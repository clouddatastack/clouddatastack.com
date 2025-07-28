4.1. dbt Incremental Models
===================================

Advanced strategies for implementing efficient incremental data models in dbt with Databricks.

.. contents:: Article Outline
   :local:
   :depth: 2

Introduction
------------
Incremental models are one of dbt's most powerful features for handling large datasets efficiently. Instead of rebuilding entire tables on every run, incremental models only process new or changed data, dramatically reducing compute costs and execution time.

This guide covers advanced strategies for implementing robust incremental models on Databricks, including:

* Core incremental strategies and their use cases
* Understanding incremental predicates and partition optimization
* Establishing event_date as a standard for all incremental models
* Managing schema changes with append_new_columns
* Implementing automated data retention policies
* Solving column ordering issues in incremental models

Key Benefits of Incremental Models
----------------------------------
* **Performance**: Process only new/changed records instead of full table rebuilds
* **Cost Efficiency**: Significantly reduced compute costs for large datasets
* **Scalability**: Handle tables with billions of records efficiently
* **Flexibility**: Support various update strategies based on business needs

Core Incremental Strategies
----------------------------

dbt supports several incremental strategies, each optimized for different use cases:

**append (Default)**

Simply adds new records to the target table without checking for duplicates.

.. code-block:: text

   {{
       config(
           materialized='incremental',
           incremental_strategy='append'
       )
   }}

   SELECT * FROM {{ ref('raw_events') }}
   {% if is_incremental() %}
       WHERE created_at > (SELECT MAX(created_at) FROM {{ this }})
   {% endif %}

**merge (Recommended)**

Performs MERGE operations, ideal for handling updates and inserts (upserts).

.. code-block:: text

   {{
       config(
           materialized='incremental',
           incremental_strategy='merge',
           unique_key='user_id'
       )
   }}

   SELECT user_id, email, updated_at
   FROM {{ ref('raw_users') }}
   {% if is_incremental() %}
       WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
   {% endif %}

**replace_where (Databricks Optimized)**

Replaces data based on a predicate condition, excellent for time-partitioned data.

.. code-block:: text

   {{
       config(
           materialized='incremental',
           incremental_strategy='replace_where',
           incremental_predicates=["event_date = " ~ event_date()]
       )
   }}

Understanding Incremental Predicates
------------------------------------
Incremental predicates define which partitions of data to replace or merge. They're crucial for performance optimization and data consistency.

**Basic Predicate Usage**

.. code-block:: text

   {{
       config(
           materialized='incremental',
           incremental_strategy='replace_where',
           incremental_predicates="event_date = '{{ var('event_date') }}'"
       )
   }}

**Dynamic Predicate with Macros**

.. code-block:: text

   {{
       config(
           materialized='incremental',
           incremental_strategy='replace_where',
           incremental_predicates=["event_date = " ~ event_date()]
       )
   }}

**Multiple Predicates**

.. code-block:: text

   {{
       config(
           materialized='incremental',
           incremental_strategy='replace_where',
           incremental_predicates=[
               "event_date = " ~ event_date(),
               "region = '" ~ var('region') ~ "'"
           ]
       )
   }}

Partition Strategy with partition_by
------------------------------------
Proper partitioning is essential for query performance and cost optimization in Databricks.

**Date-based Partitioning (Recommended)**

.. code-block:: text

   {{
       config(
           materialized='incremental',
           partition_by=['event_date'],
           incremental_strategy='replace_where',
           incremental_predicates=["event_date = " ~ event_date()]
       )
   }}

**Multi-column Partitioning**

.. code-block:: text

   {{
       config(
           materialized='incremental',
           partition_by=['event_date', 'region'],
           incremental_strategy='replace_where'
       )
   }}

Event Date as the Standard
--------------------------
Establishing ``event_date`` as a consistent column across all incremental models provides numerous benefits:

**Benefits of event_date Standardization**

* **Consistent Partitioning**: All tables partition on the same column
* **Simplified Joins**: Easy to join tables across different time periods
* **Uniform Retention**: Apply the same retention policies across all models
* **Query Optimization**: Databricks can optimize queries knowing the partition structure

**Implementation Pattern**

.. code-block:: text

   {{
       config(
           materialized='incremental',
           on_schema_change='append_new_columns',
           incremental_strategy='replace_where',
           incremental_predicates=["event_date = " ~ event_date()],
           post_hook="{{ data_retention(90) }}",
           partition_by=['event_date']
       )
   }}

   SELECT
       {{ event_date() }} AS event_date,
       user_id,
       action_type,
       created_at
   FROM {{ ref('raw_events') }}
   {% if is_incremental() %}
       WHERE DATE(created_at) = {{ event_date() }}
   {% endif %}

Schema Evolution with on_schema_change
--------------------------------------
The ``on_schema_change='append_new_columns'`` setting allows tables to evolve gracefully when new columns are added to source data.

.. code-block:: text

   {{
       config(
           materialized='incremental',
           on_schema_change='append_new_columns'
       )
   }}

**Benefits:**
* Automatically adds new columns from source data
* Prevents model failures when schema changes occur
* Maintains backward compatibility with existing data

**Considerations:**
* New columns will be NULL for existing records
* Column type changes may still cause failures
* Always test schema changes in development first

Data Retention Management
-------------------------
Large incremental models require automated data retention to manage storage costs and comply with data governance policies.

**Custom Data Retention Macro**

.. literalinclude:: code/macros/data_retention.sql
   :language: text
   :linenos:

**Usage in Incremental Models**

.. code-block:: text

   {{
       config(
           materialized='incremental',
           post_hook="{{ data_retention(90) }}"
       )
   }}

**Retention Configuration Examples**

.. code-block:: text

   -- Retain 30 days of data
   post_hook="{{ data_retention(30) }}"
   
   -- Retain 1 year with custom date column
   post_hook="{{ data_retention(365, 'transaction_date') }}"
   
   -- Retain 90 days (default)
   post_hook="{{ data_retention() }}"

Column Ordering Problem and Solution
------------------------------------
One of the most challenging issues with incremental models is maintaining consistent column ordering between the source data and target table. When Databricks creates a table, the column order matters for incremental operations. If your dbt model's SELECT statement has columns in a different order than the target table's schema, incremental runs will fail with type errors.

The issue occurs because the ``SHOW CREATE TABLE`` command reveals the actual column order in Databricks, and if your SQL SELECT has a different order, incremental operations fail. This commonly happens when running incremental models multiple times or when pre-commit hooks (like sqlfluff) reorder your SQL columns automatically.

**Solution: Custom Materialization**

The most robust solution is to create a custom materialization that handles column ordering automatically:

.. literalinclude:: code/macros/custom_spark_materializations.sql
   :language: text
   :linenos:

**Best Practice: Match YAML Schema Order**

The safest approach is to ensure your model's YAML schema matches Databricks' table creation order. This prevents the column ordering issue from occurring in the first place and makes your models more predictable and maintainable.

Complete Example Implementation
-------------------------------

**Production-ready Incremental Model**

Here's a complete example that incorporates all the best practices discussed:

.. code-block:: text

   {{
       config(
           materialized='incremental',
           on_schema_change='append_new_columns',
           incremental_strategy='replace_where',
           incremental_predicates=["event_date = " ~ event_date()],
           post_hook="{{ data_retention(90) }}",
           partition_by=['event_date']
       )
   }}

   SELECT
       {{ event_date() }} AS event_date,
       user_id,
       session_id,
       event_type,
       properties,
       created_at
   FROM {{ ref('raw_user_events') }}
   {% if is_incremental() %}
       WHERE DATE(created_at) = {{ event_date() }}
   {% endif %}

**Corresponding Schema Definition**

.. code-block:: yaml

   version: 2

   models:
     - name: user_events_incremental
       description: "User events processed incrementally with automated retention"
       columns:
         - name: event_date
           description: "Partition date for the event"
           data_type: date
           tests:
             - not_null
         - name: user_id
           description: "Unique identifier for the user"
           data_type: string
           tests:
             - not_null
         - name: session_id
           description: "Session identifier"
           data_type: string
         - name: event_type
           description: "Type of user event"
           data_type: string
         - name: properties
           description: "Event properties as JSON"
           data_type: string
         - name: created_at
           description: "Original event timestamp"
           data_type: timestamp

Best Practices and Recommendations
----------------------------------

**Performance Optimization**

* Always use ``event_date`` partitioning for time-series data
* Choose appropriate incremental strategies based on data patterns
* Use ``replace_where`` for event data, ``merge`` for dimension tables
* Implement proper indexing on unique_key columns

**Data Quality**

* Always test incremental logic with ``dbt build --full-refresh``
* Implement data quality tests on incremental models
* Monitor for duplicate records when using append strategy
* Validate that incremental predicates match partition keys

**Operational Excellence**

* Standardize on ``event_date`` across all incremental models
* Implement automated data retention policies
* Use consistent naming conventions for incremental models
* Document incremental strategies in model descriptions

**Cost Management**

* Right-size partitions to avoid small file problems
* Use appropriate retention periods to manage storage costs
* Monitor incremental model performance and adjust strategies
* Consider using ``insert_overwrite`` for full partition refreshes

Common Pitfalls and Solutions
-----------------------------

**Small Files Problem**

Incremental models can create many small files, impacting performance. Use ``optimize`` and ``vacuum`` operations regularly:

.. code-block:: text

   post_hook=[
       "OPTIMIZE {{ this }}",
       "{{ data_retention(90) }}",
       "VACUUM {{ this }} RETAIN 168 HOURS"
   ]

**Inconsistent Data Types**

Schema changes can cause type mismatches in incremental runs. Use strict schema definitions and test changes thoroughly:

.. code-block:: yaml

   columns:
     - name: event_date
       data_type: date
       tests:
         - not_null
     - name: amount
       data_type: decimal(10,2)

**Partition Pruning Issues**

Queries scan too many partitions due to improper predicate pushdown. Ensure partition columns are used in WHERE clauses:

.. code-block:: text

   {% if is_incremental() %}
       WHERE event_date = {{ event_date() }}  -- Ensures partition pruning
   {% endif %}

Conclusion
----------
Incremental models are essential for building scalable data pipelines in dbt. By following these patterns and best practices:

* Use consistent ``event_date`` partitioning across all models
* Implement automated data retention policies
* Choose appropriate incremental strategies for your use cases
* Solve column ordering issues with custom materializations
* Monitor and optimize performance regularly

These strategies will help you build robust, efficient, and maintainable incremental models that scale with your data growth while controlling costs and maintaining high performance.

References
----------
* `dbt Incremental Models Documentation <https://docs.getdbt.com/docs/build/incremental-models>`_
* `Databricks Delta Lake Documentation <https://docs.databricks.com/delta/index.html>`_
* `dbt Databricks Adapter Documentation <https://docs.getdbt.com/reference/warehouse-setups/databricks-setup>`_
