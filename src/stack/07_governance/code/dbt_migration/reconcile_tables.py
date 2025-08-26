from pyspark.sql import functions as F

def reconcile_tables(
    spark, # Pass the SparkSession
    old_table_path,
    new_table_path,
    pk_columns, # List of strings, e.g., ["clsfd_categ_ref_id"]
    compare_columns # List of strings for columns to compare
):
    """
    Reconciles data between two tables in Databricks, handling case-insensitive column names.

    :param spark: SparkSession object.
    :param old_table_path: Full path of the old table.
    :param new_table_path: Full path of the new table.
    :param pk_columns: A list of primary key column names (strings) used for joining.
    :param compare_columns: A list of column names (strings) to compare for data mismatches.
    :return: A tuple containing:
             - df_discrepancies: DataFrame with detailed discrepancies.
             - summary_metrics: Dictionary with summary counts.
    """

    print(f"Reconciling OLD table: {old_table_path}")
    print(f"With NEW table: {new_table_path}")
    print(f"Using PK columns: {pk_columns}")
    print(f"Comparing data columns: {compare_columns}\n")

    df_old = spark.table(old_table_path)
    df_new = spark.table(new_table_path)

    # Map all columns to lower-case for case-insensitive matching
    old_cols_lc = {col.lower(): col for col in df_old.columns}
    new_cols_lc = {col.lower(): col for col in df_new.columns}
    # Normalize pk_columns and compare_columns to ensure only base names are used, lowercased
    pk_columns_lc = [c.split('.')[-1].lower() for c in pk_columns]
    compare_columns_lc = [c.split('.')[-1].lower() for c in compare_columns]

    # Add prefixes to all columns (including PK columns) to distinguish after join
    old_cols_renamed = {old_cols_lc[col]: f"old_{col}" for col in old_cols_lc}
    new_cols_renamed = {new_cols_lc[col]: f"new_{col}" for col in new_cols_lc}

    df_old_aliased = df_old
    for old_name, new_name_val in old_cols_renamed.items():
        df_old_aliased = df_old_aliased.withColumnRenamed(old_name, new_name_val)

    df_new_aliased = df_new
    for old_name, new_name_val in new_cols_renamed.items():
        df_new_aliased = df_new_aliased.withColumnRenamed(old_name, new_name_val)

    # Build join condition (case-insensitive, using PK columns)
    join_condition = [
        F.col(f"old_{col}") == F.col(f"new_{col}")
        for col in pk_columns_lc
        if f"old_{col}" in df_old_aliased.columns and f"new_{col}" in df_new_aliased.columns
    ]

    df_joined = df_old_aliased.join(df_new_aliased, join_condition, "full_outer")

    select_exprs = []
    # Add PK columns to select expressions, coalescing from both sides
    for pk_col in pk_columns_lc:
        old_pk = f"old_{pk_col}"
        new_pk = f"new_{pk_col}"
        select_exprs.append(F.coalesce(F.col(old_pk), F.col(new_pk)).alias(pk_col))

    # Determine existence status
    old_pk_all_not_null_cond = F.lit(True)
    new_pk_all_not_null_cond = F.lit(True)
    for pk_col in pk_columns_lc:
        old_pk = f"old_{pk_col}"
        new_pk = f"new_{pk_col}"
        old_pk_all_not_null_cond = old_pk_all_not_null_cond & F.col(old_pk).isNotNull()
        new_pk_all_not_null_cond = new_pk_all_not_null_cond & F.col(new_pk).isNotNull()

    existence_status_col = F.when(old_pk_all_not_null_cond & new_pk_all_not_null_cond, "MATCH_IN_BOTH") \
                             .when(old_pk_all_not_null_cond & (~new_pk_all_not_null_cond), "ONLY_IN_OLD") \
                             .when((~old_pk_all_not_null_cond) & new_pk_all_not_null_cond, "ONLY_IN_NEW") \
                             .alias("existence_status")
    select_exprs.append(existence_status_col)

    overall_mismatch_flag_conditions = []
    # Get the columns available in df_joined to check against
    df_joined_cols = df_joined.columns

    for col_to_compare in compare_columns_lc:
        old_col_aliased_name = f"old_{col_to_compare}"
        new_col_aliased_name = f"new_{col_to_compare}"
        match_status_col_name = f"{col_to_compare}_match_status"

        # Define expressions for old and new values, defaulting to NULL if column not in df_joined
        expr_for_old_val = F.lit(None)
        if old_col_aliased_name in df_joined_cols:
            expr_for_old_val = F.col(old_col_aliased_name)
        
        expr_for_new_val = F.lit(None)
        if new_col_aliased_name in df_joined_cols:
            expr_for_new_val = F.col(new_col_aliased_name)

        # Add old and new values to select expressions, ensuring they are named correctly
        # These will be the columns in df_comparison_details
        select_exprs.append(expr_for_old_val.alias(old_col_aliased_name))
        select_exprs.append(expr_for_new_val.alias(new_col_aliased_name))

        # Add match status column (handles NULLs correctly using eqNullSafe)
        # This uses the potentially NULLified expressions for comparison
        match_expr = expr_for_old_val.eqNullSafe(expr_for_new_val)
        select_exprs.append(match_expr.alias(match_status_col_name))
        overall_mismatch_flag_conditions.append(~match_expr)

    df_comparison_details = df_joined.select(*select_exprs)

    # Create a single boolean column that is true if there is ANY data mismatch for rows in both tables
    any_data_mismatch_col = F.lit(False)
    if overall_mismatch_flag_conditions:
        current_flag = overall_mismatch_flag_conditions[0]
        for i in range(1, len(overall_mismatch_flag_conditions)):
            current_flag = current_flag | overall_mismatch_flag_conditions[i]
        any_data_mismatch_col = F.when(F.col("existence_status") == "MATCH_IN_BOTH", current_flag).otherwise(F.lit(False))

    df_comparison_details = df_comparison_details.withColumn("any_data_mismatch", any_data_mismatch_col)

    # Filter for discrepancies: rows not in both, or rows in both with any data mismatch
    df_discrepancies = df_comparison_details.filter(
        (F.col("existence_status") != "MATCH_IN_BOTH") | F.col("any_data_mismatch")
    )

    # --- Summary Metrics ---
    total_old_rows = df_old.count()
    total_new_rows = df_new.count()

    summary_counts_df = df_comparison_details.groupBy("existence_status").count()
    summary_counts_collected = {row['existence_status']: row['count'] for row in summary_counts_df.collect()}

    rows_in_both = summary_counts_collected.get('MATCH_IN_BOTH', 0)
    rows_only_in_old = summary_counts_collected.get('ONLY_IN_OLD', 0)
    rows_only_in_new = summary_counts_collected.get('ONLY_IN_NEW', 0)

    rows_with_data_mismatches = df_comparison_details.filter(
        (F.col("existence_status") == "MATCH_IN_BOTH") & F.col("any_data_mismatch")
    ).count()

    summary_metrics = {
        "total_rows_old_table": total_old_rows,
        "total_rows_new_table": total_new_rows,
        "rows_in_both_by_pk": rows_in_both,
        "rows_only_in_old_table": rows_only_in_old,
        "rows_only_in_new_table": rows_only_in_new,
        "rows_in_both_with_data_mismatches": rows_with_data_mismatches
    }

    print("--- Reconciliation Summary Metrics ---")
    for key, value in summary_metrics.items():
        print(f"{key}: {value}")
    
    print(f"\nFound {df_discrepancies.count()} total records with discrepancies (existence or data mismatch).")
    print("--- Discrepancy Details (showing up to 20 rows) ---")
    df_discrepancies.show(truncate=False)

    return df_discrepancies, summary_metrics
