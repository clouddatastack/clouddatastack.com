Databricks Audit
=================================

Here’s a practical guide to auditing and analyzing datasets, workloads, and costs within Databricks environment. This checklist helps understand data usage, performance, and cost management.

Inventory: What Data Assets Exist?
-------------------------------------

**Show the top N largest tables in Databricks by size**

.. code-block:: python

    from pyspark.sql import SparkSession
    from typing import Optional

    spark = SparkSession.builder.getOrCreate()

    # === PARAMETERS ===
    MAX_TABLES = 100  # Number of top tables to return
    SKIP_SCHEMAS = {"information_schema"}

    # === FUNCTIONS ===
    def format_size(size_in_bytes: Optional[int]) -> str:
        if size_in_bytes is None:
            return "N/A"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} PB"

    # === MAIN ===
    results = []

    catalogs = [row.catalog for row in spark.sql("SHOW CATALOGS").collect()]

    for catalog in catalogs:
        try:
            spark.sql(f"USE CATALOG {catalog}")
            schemas_raw = spark.sql("SHOW SCHEMAS").collect()
            schema_names = [getattr(row, 'namespace', getattr(row, 'databaseName', None)) for row in schemas_raw]
        except Exception as e:
            print(f"⚠️ Skipping catalog {catalog}")
            continue

        for schema in schema_names:
            if not schema or schema.lower() in SKIP_SCHEMAS:
                continue

            try:
                tables = spark.sql(f"SHOW TABLES IN {catalog}.{schema}").collect()
            except Exception as e:
                print(f"⚠️ Skipping schema {catalog}.{schema}")
                continue

            for table in tables:
                if hasattr(table, 'entityType') and table.entityType.lower() == 'view':
                    continue  # Skip views

                full_name = f"{catalog}.{schema}.{table.tableName}"
                print(f"🔍 Checking table: {full_name}")

                try:
                    detail = spark.sql(f"DESCRIBE DETAIL {full_name}").collect()[0].asDict()
                    size = detail.get("sizeInBytes", 0)
                    results.append({
                        "catalog": catalog,
                        "schema": schema,
                        "table": table.tableName,
                        "format": detail.get("format", "unknown"),
                        "lastModified": detail.get("lastModified"),
                        "sizeInBytes": size,
                        "sizeReadable": format_size(size),
                        "numFiles": detail.get("numFiles", 0),
                    })
                except Exception as e:
                    print(f"❌ Skipped {full_name}")

    # === DISPLAY RESULT ===
    if results:
        df = spark.createDataFrame(results)
        top_n_df = df.orderBy("sizeInBytes", ascending=False).limit(MAX_TABLES)
        display(top_n_df)
    else:
        print("❌ No table metadata collected.")