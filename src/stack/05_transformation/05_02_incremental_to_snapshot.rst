5.2. Incremental to Snapshot
============================

Many data integrations, especially with third-party APIs (e.g., Stripe, Salesforce), provide data incrementally. Instead of getting a full dump of a source table every day, you receive only the records that were created or updated on that day. While this is efficient for data extraction, it's less convenient for analytics, where analysts often need a complete "snapshot" of the table as it looked on a specific day.

The Core Logic
---------------

The goal is to build a dbt model that, for any given day, represents the complete state of the source data. We achieve this with a macro that combines the latest incremental data with the previous day's snapshot.

- **For an incremental run (daily operation):** The model takes all new and updated records from today's load and combines them with all the *unchanged* records from yesterday's snapshot.
- **For a full refresh (initial setup or recovery):** The model scans the entire history of incremental loads, finds the absolute latest version of each record, and builds a snapshot from scratch.

The Macro
----------

Here is a generalized dbt macro that implements this logic. It's designed to be placed in your ``macros`` directory.

.. literalinclude:: code/macros/incremental_api_to_snapshot_staging.sql
   :language: jinja

**How to Use It**

You would call this macro from your staging model, which should be materialized as an incremental table itself, partitioned by ``event_date``.

.. code-block:: sql+jinja

   .. code-block:: jinja
 
   -- models/staging/stage_api_snapshots.sql
   {{
     config(
       materialized='incremental',
       unique_key='record_id',
       partition_by={
         "field": "event_date",
         "data_type": "date"
       }
     )
   }}
 
   {{ incremental_api_to_snapshot_staging(source('api_source', 'daily_loads')) }}


Potential Challenges and Solutions
-----------------------------------

This pattern is powerful, but real-world data introduces complexities. Here’s how to handle them.

1. Data Quality and Deduplication
----------------------------------

**Problem:** The integrity of your snapshot depends entirely on the quality of your incremental loads. If the source API sends duplicate ``record_id`` values within a single day's load, it can break your model.

**Solution:**

- **Initial Load:** The ``row_number()`` window function in the macro's ``else`` block effectively deduplicates the historical data, ensuring that only the most recent version of each record is used for the initial snapshot.
- **Incremental Loads:** The primary defense is testing. You must add data tests to your source-configured dbt model to ensure the uniqueness of the primary key (e.g., ``record_id``) for each daily partition (``event_date``).

.. code-block:: yaml

   # models/sources/sources.yml
   version: 2
   sources:
     - name: api_source
       schema: raw_data
       tables:
         - name: daily_loads
           columns:
             - name: record_id
               tests:
                 - dbt_utils.unique_combination_of_columns:
                     combination_of_columns:
                       - event_date
                       - record_id

2. Schema Changes
------------------

**Problem:** APIs evolve. A field might be added, removed, or have its data type changed. A standard dbt incremental model can fail or, worse, silently ignore new columns if not configured correctly. 

**Solution:**

- **Adding Columns:** The use of ``select *`` and ``select * except(...)`` makes this macro resilient to newly added columns. They will be automatically included in both the incremental and full-refresh paths. Potential backfilling might be needed for historical dates, depending on your use case.
- **Removing/Renaming/Changing Data Types:** These are breaking changes. The simplest solution is to run a full refresh: ``dbt run --full-refresh -s stage_api_snapshots``. This rebuilds the entire snapshot using the new schema from the source. For a more automated but complex solution, you could explore dbt's ``on_schema_change`` configuration in your staging model, though it requires careful implementation to work with this custom snapshot logic.