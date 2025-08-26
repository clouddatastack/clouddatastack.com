3.2. Files
==================================

Efficient file organization in object storage is key to scalable and cost-effective data processing. This page provides guidelines and trade-offs for structuring files in a modern data lake.

Format
------

Choosing the right file format depends on the use case and processing engine compatibility.

**When to use each format:**

- **Parquet**: Columnar, highly efficient for most analytical queries. Recommended for general-purpose analytics.
- **Avro**: Supports schema evolution, good for streaming pipelines and serialization.
- **JSON / CSV**: Human-readable and useful for raw ingest, debugging, or exchanging data across systems.

**Compression options:**

By default, file formats like **Parquet** and **Avro** are written with **Snappy compression**, which offers a good balance between speed and compression ratio. You can override this behavior when writing data using the ``compression`` option.

The choice of compression affects both **storage cost** and **query performance**, especially in distributed processing engines like Spark, Trino, or Presto.

**Available options:**

- **Snappy**: Fast and splittable. Default for Parquet and Avro. Recommended for most workloads.
- **ZSTD**: Higher compression ratio than Snappy (smaller files), slightly slower to write. Useful when optimizing for storage cost.
- **GZIP**: Widely supported, but **not splittable**. Should be avoided for large-scale distributed processing (e.g., with Spark), especially when used with CSV or JSON.

**What does "splittable" mean?**

A **splittable** compression format allows a large file to be broken into smaller chunks and read by multiple workers in parallel. This is critical for performance in distributed processing.

- **Splittable**: Parquet + Snappy/ZSTD, Avro + Snappy → good for Spark, Trino
- **Not splittable**: CSV + GZIP → single-threaded read, can cause bottlenecks

Use **splittable formats** to ensure scalability and high throughput in data lakes.

**How to change compression algorithm**

You can explicitly configure compression during write operations. Below are common examples.

*PySpark (Parquet with ZSTD)*

.. code-block:: python

    df.write \
      .option("compression", "zstd") \
      .parquet("s3://bucket/path/")

*PySpark (Avro with Snappy)*

.. code-block:: python

    df.write \
      .format("avro") \
      .option("compression", "snappy") \
      .save("s3://bucket/path/")

*Delta Lake (ZSTD compression via Spark config)*

.. code-block:: python

    spark.conf.set("spark.sql.parquet.compression.codec", "zstd")
    
    df.write.format("delta").save("s3://bucket/delta/")

*dbt (Parquet with ZSTD in Delta Lake)*

In `dbt_project.yml` or a model config:

.. code-block:: yaml

    models:
      my_project:
        +file_format: delta
        +parquet_compression: zstd

GZIP can also be used for CSV/JSON, but use with caution in distributed systems:

.. code-block:: python

    df.write \
      .option("compression", "gzip") \
      .csv("s3://bucket/archive/")

Size
----

Small files can negatively impact performance, while very large files can slow down writes and shuffle operations.

**Target guidelines:**

- Aim for file sizes between **100 MB and 512 MB**
- Avoid creating too many small files (also known as the “small files problem”)

**Can you control file size directly?**  
Not precisely. Spark doesn't allow you to specify output file size directly, but you can influence it using the techniques below.

**Approaches to influence output file size:**

1. **Manually reduce the number of output files using `coalesce()`**

   .. code-block:: python

      # Reduce number of output files to ~10
      df.coalesce(10).write.format("parquet").save("s3://bucket/path/")

   This is best used when you're writing a smaller DataFrame or combining files at the end of processing.

2. **Repartition based on estimated total dataset size**

   .. code-block:: python

      target_file_size_mb = 128
      row_count = df.count()
      avg_row_size_bytes = 200  # adjust based on your schema

      estimated_total_size_mb = (row_count * avg_row_size_bytes) / (1024 * 1024)
      num_partitions = int(estimated_total_size_mb / target_file_size_mb)

      df.repartition(num_partitions).write.parquet("s3://bucket/path/")

3. **Use Delta Lake’s `OPTIMIZE` for post-write compaction**

   .. code-block:: sql

      OPTIMIZE delta.`s3://bucket/table/` ZORDER BY (event_date)

4. **Enable adaptive partitioning in Spark 3+**

   .. code-block:: python

      spark.conf.set("spark.sql.adaptive.enabled", "true")

Partitioning
------------

Partitioning is used to organize and prune data efficiently during reads. It improves performance and reduces cost by scanning only relevant data.

**Common partition keys:**

- `year`, `month`, `day`
- `region`, `country`
- `event_type`, `device_type`

**Trade-offs:**

- Too many partitions with small data volumes → too many files, higher metadata overhead.
- Too few partitions → large files, slower incremental writes.

**Best practice:**

- Use high-cardinality fields with caution.
- Keep partitions balanced by data volume and query access patterns.

.. code-block:: python

    df.write.partitionBy("year", "month", "day").parquet("s3://bucket/events/")

Columns
-------

Column-level organization matters when using columnar formats like Parquet or ORC.

**Recommendations:**

- Prune unused columns before writing.
- Use proper data types (e.g., `int` instead of `string` for IDs).
- Use consistent column order for schema evolution compatibility.
- Sort data within partitions to improve compression and query performance.

Sorting ensures that rows stored together on disk have similar values, leading to better compression (especially in Parquet) and more efficient predicate filtering in query engines like Trino, Presto, or Spark SQL.

**Example: Sorting within partitions in Spark**

.. code-block:: python

    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()

    # Load and cast types
    df = spark.read.option("header", True).csv("s3://bucket/nyc-taxi-raw/")
    df = df.withColumn("pickup_datetime", df["pickup_datetime"].cast("timestamp"))

    # Sort rows within each partition and write efficiently
    (
        df
        .sortWithinPartitions("vendor_id", "pickup_datetime")
        .repartition("year", "month")
        .write
        .partitionBy("year", "month")
        .parquet("s3://bucket/nyc-taxi-data/curated/")
    )

In this example:

- The dataset is partitioned by `year` and `month`.
- Rows within each partition are sorted by `vendor_id` and `pickup_datetime`.
- This improves compression ratios and enables faster filtering on those fields during query execution.

Sorting should be applied on fields that are often filtered in queries or have strong cardinality.

Compaction
----------

Compaction is the process of merging many small files into larger ones to improve query performance and reduce metadata overhead.

This is especially relevant for streaming pipelines or frequent micro-batch jobs that write many small files.

**Tools and techniques:**

- Delta Lake: `OPTIMIZE` command for table compaction.
- Iceberg: `rewrite_data_files` procedure.
- Spark: Batch job that reads and rewrites data with `coalesce()` or `repartition()`.

.. code-block:: sql

    -- Delta Lake table compaction
    OPTIMIZE nyc_taxi_data.zones WHERE year = 2024;

Vacuuming
---------

**Vacuuming** is the process of permanently deleting old data files that are no longer referenced by the current version of the Delta Lake table.

When you update, overwrite, or delete data in a Delta table, the old files are marked as deleted but still physically exist on disk. Vacuuming helps clean them up to reduce storage usage.

.. code-block:: sql

    -- Delta Lake cleanup: delete unreferenced files older than 7 days
    VACUUM nyc_taxi_data.zones RETAIN 168 HOURS;

**Important:** Vacuuming will remove files that support **time travel** and **rollback** for older versions of your table. Once those files are deleted, queries such as:

.. code-block:: sql

    SELECT * FROM nyc_taxi_data.zones VERSION AS OF 3

will no longer work if the associated data files have been removed.

**Best Practices:**

- For production tables, retain at least 7 days: ``RETAIN 168 HOURS``
- For development or cost-sensitive environments, you may choose ``RETAIN 24 HOURS``
- Do not set ``RETAIN 0 HOURS`` unless you're absolutely sure you no longer need historical versions

Regular compaction and vacuuming are crucial in maintaining long-term performance and cost efficiency.