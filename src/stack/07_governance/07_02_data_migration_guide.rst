7.2. Data Migration Guide
=========================

Introduction
------------

Migrating data and ETL processes from traditional, often unstructured SQL environments to a structured framework like dbt (data build tool) is a common challenge that, when addressed correctly, can significantly improve data reliability, maintainability, and governance. This guide outlines key considerations, best practices, and common pitfalls encountered during such a migration, with a focus on leveraging dbt's capabilities effectively.

This guide draws upon experiences from various data migration projects, including the principles outlined in internal project requirement documents for migrating datasets and workloads to new data warehouse environments.

Key Considerations and Steps
----------------------------

Migrating to dbt involves more than just translating SQL queries. It's an opportunity to refactor, optimize, and apply software engineering best practices to your data transformation workflows.

1.  **Assessment and Planning**:
    -   **Inventory Existing Assets**: Catalog all existing SQL scripts, tables, views, and scheduled jobs.
    -   **Identify Dependencies**: Map out dependencies between various data assets. Tools that analyze query logs or lineage metadata can be helpful.
    -   **Define Scope and Prioritize**: Determine which datasets and workflows to migrate first. A phased approach, starting with less complex or high-impact models, is often advisable.
    -   **Understand the Target Environment**: Familiarize yourself with the target data warehouse (e.g., Snowflake, BigQuery, Redshift, Databricks) and its specific SQL dialect and features that dbt will interact with.

2.  **Design and Refactoring**:
    -   **Modular Design**: Break down monolithic SQL scripts into smaller, reusable dbt models. Each model should represent a distinct transformation step or logical data entity.
    -   **Staging, Intermediate, and Marts**: Adopt a layered approach (e.g., staging, intermediate/core, data marts/reporting) to organize your dbt models. This improves clarity and reusability.
    -   **Source Definition**: Define sources in dbt to manage dependencies on raw data.
    -   **Incremental Models**: For large datasets, design incremental models to process only new or updated data, significantly reducing processing time and cost.

3.  **Development and Implementation**:
    -   **dbt Project Setup**: Initialize your dbt project, configure `dbt_project.yml`, and set up profiles in `profiles.yml` for different environments (dev, test, prod).
    -   **Model Creation**: Write dbt models using SQL. Leverage Jinja templating for dynamic SQL generation, macros for reusable code snippets, and refs/sources for dependency management.
    -   **Testing**: Implement dbt tests (schema tests, data tests, custom tests) to ensure data quality and integrity.
    -   **Documentation**: Use dbt's documentation features to generate comprehensive documentation for your models, columns, and sources.

4.  **Deployment and Orchestration**:
    -   **Version Control**: Use Git for version control of your dbt project.
    -   **CI/CD**: Implement CI/CD pipelines (e.g., using GitHub Actions, GitLab CI, Jenkins) to automate testing and deployment of dbt models.
    -   **Orchestration**: Schedule dbt runs using an orchestrator like Apache Airflow, Dagster, or dbt Cloud.

Naming Conventions
------------------

Consistent naming conventions are crucial for a maintainable dbt project.

-   **Models**: Use descriptive names that indicate the entity and transformation stage (e.g., `stg_customers`, `int_orders_aggregated`, `fct_monthly_sales`).
-   **Columns**: Be consistent with casing (e.g., `snake_case`) and use clear, unambiguous names.
-   **Sources and Seeds**: Prefix with `src_` and `seed_` respectively, or follow project-specific guidelines.
-   **File Names**: Model file names should match the model names (e.g., `stg_customers.sql`).

Refer to your organization's specific guidelines for detailed conventions.

Using sqlfluff for SQL Linting
------------------------------

``sqlfluff`` is a powerful SQL linter and auto-formatter that helps maintain code quality and consistency.

1.  **Installation**:

    .. code-block:: bash

       pip install sqlfluff sqlfluff-templater-dbt

2.  **Configuration**:
    Create a ``.sqlfluff`` configuration file in your dbt project root to define rules and dialects.
    Example ``.sqlfluff``::

    .. code-block:: ini

       [sqlfluff]
       templater = dbt
       dialect = snowflake  # Or your specific dialect (bigquery, redshift, etc.)
       rules = AM04, CP01, L003, L010, L019, L029, L030, L031, L034, L036, L042, L050, L051, L052, L053, L057, L059, L062, L063, L066, L067, L068, L070

       [sqlfluff:templater:dbt]
       project_dir = ./

       [sqlfluff:rules:L003] # Indentation
       tab_space_size = 4

       [sqlfluff:rules:L010] # Keywords
       capitalisation_policy = upper

       [sqlfluff:rules:L030] # Function names
       capitalisation_policy = upper

3.  **Usage**:
    -   Lint: ``sqlfluff lint models/``
    -   Fix: ``sqlfluff fix models/``

Integrating ``sqlfluff`` into your CI/CD pipeline ensures that all code contributions adhere to the defined standards.

Data Reconciliation
-------------------

Ensuring data consistency between the old and new systems is paramount.

1.  **Strategy**:
    -   **Row Counts**: Compare row counts for key tables.
    -   **Aggregate Checks**: Compare sums, averages, min/max values for important numeric columns.
    -   **Dimension Comparisons**: For dimensional data, check for discrepancies in distinct values.
    -   **Full Data Dumps (for smaller tables)**: Compare entire datasets if feasible.

2.  **Reconciliation Script**:
    A Python script can automate the comparison of tables between two different data sources (e.g., the legacy system and the new dbt-managed warehouse). The script typically involves:
    -   Connecting to both source and target databases.
    -   Fetching data (or aggregates) from corresponding tables.
    -   Comparing the results and highlighting discrepancies.

    An example Python script for table reconciliation might look like this (conceptual):

    .. code-block:: python
       :caption: Example: reconcile_tables.py
       :name: reconcile_tables_py

       import pandas as pd
       # Assume functions get_connection_source() and get_connection_target() exist
       # Assume functions fetch_data(connection, query) exist

       def reconcile_tables(source_table_name, target_table_name, key_columns, value_columns):
           """
           Reconciles data between a source and target table.
           """
           print(f"Reconciling {source_table_name} with {target_table_name}...")

           conn_source = get_connection_source() # Implement this
           conn_target = get_connection_target() # Implement this

           query_source = f"SELECT {', '.join(key_columns + value_columns)} FROM {source_table_name}"
           query_target = f"SELECT {', '.join(key_columns + value_columns)} FROM {target_table_name}"

           df_source = fetch_data(conn_source, query_source) # Implement this
           df_target = fetch_data(conn_target, query_target) # Implement this

           # Basic checks
           if len(df_source) != len(df_target):
               print(f"Row count mismatch: Source has {len(df_source)}, Target has {len(df_target)}")
           else:
               print("Row counts match.")

           # Example: Sum check for numeric columns
           for col in value_columns:
               if pd.api.types.is_numeric_dtype(df_source[col]) and pd.api.types.is_numeric_dtype(df_target[col]):
                   sum_source = df_source[col].sum()
                   sum_target = df_target[col].sum()
                   if sum_source != sum_target:
                       print(f"Sum mismatch for column {col}: Source sum {sum_source}, Target sum {sum_target}")
                   else:
                       print(f"Sum for column {col} matches.")
           # Add more sophisticated checks as needed (e.g., using pandas.merge for detailed diff)

           conn_source.close()
           conn_target.close()

       # Example usage:
       # reconcile_tables("legacy_schema.orders", "dbt_prod.fct_orders", ["order_id"], ["order_amount", "item_count"])

    A more complete version of such a script can be found at:
    `code/dbt_migration/reconcile_tables.py <code/dbt_migration/reconcile_tables.py>`_

    This script should be adapted to your specific database connectors and comparison logic.

Stakeholder Approval
--------------------

Data migration projects impact various stakeholders (data analysts, business users, data scientists).
-   **Communication**: Keep stakeholders informed throughout the migration process.
-   **Validation**: Involve stakeholders in validating the migrated data and reports. Their domain expertise is invaluable for catching subtle errors.
-   **Sign-off**: Establish a formal sign-off process for migrated datasets and workflows to ensure alignment and accountability.

Common dbt Pitfalls and Solutions
---------------------------------

### Handling Dates

-   **Pitfall**: Using `CURRENT_DATE` or `NOW()` directly in SQL models makes them non-rerunnable for past dates, hindering backfills and historical reprocessing.
-   **Solution**:
    -   **dbt Variables**: Pass processing dates as dbt variables.

      .. code-block:: text

         -- model.sql
         SELECT *
         FROM {{ source('my_source', 'events') }}
         WHERE event_date = '{{ var("processing_date") }}'

      Run with: ``dbt run --vars '{"processing_date": "2023-01-15"}'``

    -   **Date Dimension Table**: Join with a date dimension table and filter on its attributes.
    -   **Macros for Date Logic**: Encapsulate date logic in dbt macros for consistency.

### Data Backfilling Strategies

- **Strategies**:
  - **Full Refresh**: For smaller tables, a `dbt run --full-refresh` might be sufficient.
  - **Incremental Models with Backfill Logic**: Design incremental models to handle backfills. This might involve:

    - Temporarily changing the incremental strategy or `is_incremental()` logic.
    - Running the model for specific date ranges.
    - Using custom materializations or pre/post hooks for complex backfill scenarios.

  - **Batching**: For very large backfills, process data in batches (e.g., month by month) to manage resource consumption.

    .. code-block:: text

       # Example: Backfilling month by month
       for year_month in 2022-01 2022-02 ...; do
         dbt run --select my_incremental_model --vars "{\"processing_month\": \"${year_month}\"}"
       done

Testing dbt Scripts
-------------------

-   **Dedicated Test Environment**: Always test dbt models in a dedicated test or pre-production environment that mirrors production as closely as possible. This environment should have its own data sources or sanitized copies of production data.
-   **dbt Tests**:
    -   **Schema Tests**: ``unique``, ``not_null``, ``accepted_values``, ``relationships``.
    -   **Data Tests**: Custom SQL queries that assert specific conditions (e.g., "total revenue should be positive").
    -   **Singular Tests (dbt-utils)**: Useful for more complex assertions.
-   **Dry Runs**: Use ``dbt compile`` and ``dbt run --dry-run`` (if supported by adapter) to catch compilation errors and review generated SQL before execution.
-   **CI Integration**: Run tests automatically in your CI pipeline on every commit or pull request.

Managing Lookup Tables
----------------------

Lookup tables (or static tables) often contain reference data that changes infrequently.

-   **dbt Seeds**:
    -   **Pros**:
        
        - Easy to manage small, static datasets directly within your dbt project.
        - Version controlled with your code.
        
    -   **Cons**:
        
        - Not ideal for large datasets or data that needs to be updated by non-technical users.
        - Can lead to slower ``dbt seed`` runs if many or large CSVs.
        
    -   **Usage**:

        Place CSV files in the ``seeds`` directory (or ``data`` prior to dbt v0.17.0).
        Run ``dbt seed`` to load the data.
        Reference them in models using ``{{ ref('my_seed_table') }}``.

-   **Static External Tables**:
    -   **Pros**:
        
        - Suitable for larger lookup tables or when data is managed externally (e.g., by a business team).
        - Data can be updated without a dbt run.
        
    -   **Cons**:
        
        - Requires managing the external storage (e.g., CSVs on S3, Google Cloud Storage) and ensuring schema consistency.
        
    -   **Usage**:

        1.  Store the lookup data as CSVs or Parquet files in object storage (e.g., S3).
        2.  Define these as external tables in your data warehouse.
        3.  In dbt, define these external tables as sources in a ``sources.yml`` file.
        4.  Reference them using ``{{ source('my_external_source', 'lookup_table_name') }}``.

    -   **Example**: For static tables, use CSV files on S3 (e.g., `s3://<your-bucket>/<domain>/<env>/core/static/<table_name>.csv`) and create external tables pointing to these files. The DDL for these external tables can be managed via Airflow DAGs or dbt pre-hooks.

Data Partitioning Strategies with dbt
-------------------------------------

Partitioning is crucial for query performance and cost optimization in large data warehouses. While dbt doesn't directly manage physical partitioning (this is a data warehouse feature), it can and should be used to build models that leverage partitioning effectively.

-   **Model Design**: Design your dbt models, especially incremental ones, to align with the partitioning keys of your target tables (e.g., date, region).
-   **Incremental Strategies**: Ensure your incremental model logic correctly filters for and processes data relevant to specific partitions.
-   **Warehouse Configuration**: Configure partitioning and clustering (if applicable) directly in your data warehouse (e.g., ``PARTITION BY date_column`` in Snowflake or BigQuery).

    .. code-block:: text

       -- Example dbt model config for BigQuery partitioning
       {{
         config(
           materialized='incremental',
           partition_by={
             "field": "event_date",
             "data_type": "date",
             "granularity": "day"
           },
           cluster_by = ["user_id"]
         )
       }}

       SELECT
         event_timestamp,
         DATE(event_timestamp) as event_date, -- Ensure partition column exists
         user_id,
         ...
       FROM {{ source('raw_events', 'events_table') }}

       {% if is_incremental() %}
         WHERE DATE(event_timestamp) >= (SELECT MAX(event_date) FROM {{ this }})
       {% endif %}

-   **Best Practices**:
    -   Choose partition keys based on common query filter patterns.
    -   Avoid partitioning on high-cardinality columns unless it aligns with specific access patterns.

Managing dbt Model Changes (Schema Evolution)
---------------------------------------------

Schema evolution (adding, removing, or modifying columns) is inevitable.

-   **dbt ``on_schema_change``: For incremental models, dbt provides the ``on_schema_change`` configuration to handle schema discrepancies between the target table and the new model definition.
    -   ``ignore``: Default. Ignores schema changes. New columns won't be added.
    -   ``fail``: Fails the run if schemas don't match.
    -   ``append_new_columns``: Adds new columns to the target table. Does not remove columns.
    -   ``sync_all_columns``: Adds new columns and removes columns present in the target table but not in the model. **Use with caution as it can be destructive.**

    .. code-block:: yaml

       # dbt_project.yml or model config block
       models:
         +on_schema_change: "append_new_columns"

-   **Full Refresh**: Sometimes, a ``dbt run --full-refresh`` is the simplest way to apply schema changes, especially for non-incremental models or when ``sync_all_columns`` behavior is desired safely.
-   **Blue/Green Deployments**: For critical models, consider a blue/green deployment strategy:
    1.  Build the new version of the model to a temporary table/schema.
    2.  Test and validate the new version.
    3.  Atomically swap the new version with the old one.
    dbt's aliasing and custom materializations can facilitate this.

-   **Communication**: Communicate schema changes to downstream consumers. dbt's documentation and tools like ``dbt-artifacts-parser`` can help track lineage and impact.
-   **Avoid Dropping Columns Lightly**: If a column needs to be removed, ensure no downstream models or BI tools depend on it. Consider deprecating it first (e.g., renaming to ``_old_column_name`` or documenting its removal) before physically dropping it.

Capturing Migration Metadata in dbt (schema.yml)
------------------------------------------------

While migrating, it is useful to record the provenance of each dbt model and any structural changes made along the way. You can add a ``meta`` block in your model's YAML (``schema.yml``) to capture:

- Original system/database/schema/model names
- Flags indicating migration status
- Lists of columns that were added, modified, or deleted
- Per-column previous names/types for traceability

This metadata improves documentation, lineage, audits, and automated checks during/after migration.

Example (generic)
~~~~~~~~~~~~~~~~~

.. code-block:: yaml

     version: 2

     models:
         - name: <target_model_name>
             description: "<Short description of the migrated model>"
             meta:
                 is_migrated: true
                 migrated_from_system: <source_system>
                 migrated_from_database: <source_database>
                 migrated_from_schema: <source_schema>
                 migrated_from_model: <source_table_or_view>
                 added_columns:
                     - <new_col_1>
                     - <new_col_2>
                 modified_columns:
                     - <changed_col_1>
                     - <changed_col_2>
                 deleted_columns:
                     - <removed_col_1>
                     - <removed_col_2>
             columns:
                 - name: <col_a>
                     data_type: <type>
                     meta:
                         previous_column_name: <old_name_if_any>
                         previous_column_type: <old_type_if_any>
                     tests:
                         - not_null
                 - name: <col_b>
                     data_type: <type>
                     meta:
                         previous_column_name: <old_name_if_any>

Operational tips
~~~~~~~~~~~~~~~~

- Keep this metadata up to date as you iterate during migration.
- Use it to generate migration reports and to drive conditional logic in checks (e.g., validating that deleted columns are not referenced downstream).
- Expose it in dbt docs so consumers can see what changed and where the data originated.

Conclusion
----------

Migrating to dbt is a strategic move towards a more robust and agile data platform. By following these guidelines, embracing best practices in naming, linting, testing, and carefully managing common pitfalls, organizations can unlock the full potential of dbt for their data transformation needs. Remember that documentation, stakeholder communication, and an iterative approach are key to a successful migration.

