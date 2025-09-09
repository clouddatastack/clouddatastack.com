1.3. Extraction from Salesforce
================================

.. """
.. Salesforce ingestion functions.
.. """

.. import logging
.. import os
.. from itertools import islice
.. from typing import Any, Callable, Generator, List, Union

.. import dlt
.. from dlt.common.normalizers.naming.snake_case import NamingConvention
.. from dlt.pipeline import TPipeline
.. from simple_salesforce import Salesforce

.. from utils.constants.monetization.salesforce import TABLES_TO_LOAD
.. from utils.pipelines.monetization.salesforce.utils import (
..     cleanup_after_load,
..     configure_filesystem_destination,
..     get_sf_client,
.. )


.. def create_resource(
..     sf_client: Salesforce,
..     dt: str,
..     table: dict[str, str],
..     hour: int = None,
.. ) -> Callable[[], Generator[list[Any], None, None]]:
..     """Creates a DLT resource for querying a Salesforce table.

..     Args:
..         sf_client: Salesforce client instance
..         dt: Date string in YYYY-MM-DD format
..         table: Name of Salesforce table to query
..         incremental_column: Column used for incremental loading

..     Returns:
..         Callable[[], Generator[List[Any], None, None]]: A function that when called returns a generator
..         yielding Salesforce records
..     """

..     @dlt.resource(
..         name=f"{table['name']}_{dt}_{hour}" if hour else f"{table['name']}_{dt}",
..         write_disposition="append",
..         file_format="parquet",
..         table_name=table["name"],
..         parallelized=True,
..     )
..     def query_sf(
..         sf_client: Salesforce, table: dict[str, str], dt: str, hour: int = None
..     ) -> Generator[list[Any], None, None]:
..         """Query Salesforce table for records modified on specified date.

..         Args:
..             table: Name of Salesforce table to query

..         Returns:
..             Generator of records from the table matching date criteria
..         """

..         query = generate_query(sf_client=sf_client, table=table, dt=dt, hour=hour)
..         logging.info(f"Executing query: {query}")

..         sf_data = sf_client.query_all_iter(
..             query=query,
..             include_deleted=True,
..         )

..         if sf_data == []:
..             return []

..         # keys_to_keep = [k for k in sf_data[0].keys() if k != "attributes"]
..         # sf_data = [dict(zip(keys_to_keep, itemgetter(*keys_to_keep)(row))) for row in sf_data]

..         while slice_sf_data := list(islice(sf_data, 10000)):
..             logging.info(f"Table {table['name']}: {len(slice_sf_data)} records")

..             for row in slice_sf_data:
..                 del row["attributes"]

..             yield slice_sf_data

..     def generate_query(sf_client: Salesforce, table: dict[str, str], dt: str, hour: int = None) -> str:
..         """Generate a SOQL query for a Salesforce table with date filtering.

..         This function creates a query that selects all fields from the specified table,
..         filtered by the incremental_column to only include records modified/created
..         within the specified date.

..         Args:
..             table: Name of the Salesforce table/object to query
..             sf_client: Authenticated Salesforce client instance
..             date: Date string in YYYY-MM-DD format to filter records
..             incremental_column: Column name used for date filtering

..         Returns:
..             str: A SOQL query string that will retrieve all fields for records
..                 modified/created on the specified date
..         """
..         object_desc = getattr(sf_client, table["name"]).describe()
..         fields = [field["name"] for field in object_desc["fields"]]
..         fields_str = ", ".join(fields)

..         # Prepare the query
..         if hour is None:
..             start_date = f"{dt}T00:00:00.000Z"  # Start of the day
..             end_date = f"{dt}T23:59:59.999Z"  # End of the day
..         else:
..             start_date = f"{dt}T{hour:02d}:00:00.000Z"  # Start of the day
..             end_date = f"{dt}T{hour:02d}:59:59.999Z"  # End of the day

..         query = (
..             f"SELECT {fields_str} FROM {table['name']} "
..             f"WHERE {table['incremental_column']} >= {start_date} "
..             f"AND {table['incremental_column']} <= {end_date} "
..         )

..         if table.get("condition") is not None:
..             query += f" AND {table['condition']}"

..         return query

..     return query_sf(sf_client, table, dt, hour)


.. @dlt.source
.. def salesforce_source(
..     dt: str, salesforce_conn: Union[str, dict[str, str]], tables: List[dict] = None, hour: int = None
.. ) -> list[Any]:
..     """Create data resources for specified Salesforce tables.

..     Args:
..         dt (str): Date in YYYY-MM-DD format to extract data for.
..         salesforce_conn: Salesforce connection details
..         tables: List of table configurations to load. If None, loads all configured tables.
..         hour: Optional hour to load data for

..     Returns:
..         List[Any]: List of data resources containing Salesforce table data.
..     """
..     sf_client = get_sf_client(salesforce_conn)
..     tables_to_process = tables if tables is not None else TABLES_TO_LOAD

..     if hour is None:
..         load_data = [
..             create_resource(
..                 sf_client=sf_client,
..                 dt=dt,
..                 table=table,
..             )
..             for table in tables_to_process
..         ]
..     else:
..         load_data = [
..             create_resource(
..                 sf_client=sf_client,
..                 dt=dt,
..                 table=table,
..                 hour=hour,
..             )
..             for table in tables_to_process
..             if table.get("hourly_load", False)
..         ] + [
..             create_resource(
..                 sf_client=sf_client,
..                 dt=dt,
..                 table=table,
..             )
..             for table in tables_to_process
..             if not table.get("hourly_load", False) and hour == 0
..         ]

..     return load_data


.. def get_pipeline(
..     dt: str,
..     bucket_url: str,
..     destination: str = "filesystem",
..     hour: int = None,
..     table: dict = None,
.. ) -> TPipeline:
..     """Get a DLT pipeline for Salesforce data loading.

..     Args:
..         dt: Date string in YYYY-MM-DD format
..         bucket_url: S3 bucket URL for storage
..         destination: Destination type for the pipeline
..         hour: Optional hour to load data for
..         table: Table configuration dictionary

..     Returns:
..         TPipeline: Configured DLT pipeline
..     """
..     if destination == "filesystem":
..         destination = configure_filesystem_destination(dt=dt, bucket_url=bucket_url, hour=hour)

..     # Include table name in pipeline name and folder if provided
..     table_suffix = f"_{table['name'].lower()}" if table else ""
..     pipeline_name = f"salesforce_pipeline_{dt}{table_suffix}"
..     pipelines_dir = f"salesforce_pipeline_{dt}{table_suffix}"

..     os.environ["RUNTIME__LOG_LEVEL"] = "DEBUG"

..     pipeline = dlt.pipeline(
..         pipeline_name=pipeline_name,
..         destination=destination,
..         dataset_name="salesforce",
..         import_schema_path="dags/monetization/salesforce/schema",
..         pipelines_dir=pipelines_dir,
..         # progress="log",
..     )

..     return pipeline


.. def load_single_table(
..     table: dict, dt: str, bucket_url: str, salesforce_conn: str, destination: str = "filesystem"
.. ) -> dict:
..     """Load data for a single Salesforce table.

..     Args:
..         table: Table configuration dictionary
..         dt: Date string in YYYY-MM-DD format
..         bucket_url: S3 bucket URL for storage
..         salesforce_conn: Salesforce connection ID

..     Returns:
..         dict: A dictionary containing the load information in a serializable format
..     """
..     pipeline = get_pipeline(dt=dt, bucket_url=f"s3://{bucket_url}", table=table, destination=destination)
..     source = salesforce_source(dt=dt, salesforce_conn=salesforce_conn, tables=[table])

..     load_info = pipeline.run(
..         data=source,
..     )

..     logging.info(f"Load info: {load_info}")
..     if len(load_info.loads_ids) > 0:
..         load_id = load_info.loads_ids[0]
..     else:
..         load_id = ""

..     n = NamingConvention()
..     print(f"normalized {table['name']}:{n.normalize_identifier(table['name'])}")

..     cleanup_after_load(bucket_url, n.normalize_identifier(table["name"]), dt, load_id)

..     # Convert load_info to a serializable dictionary
..     return {
..         "table": table["name"],
..         "pipeline_name": pipeline.pipeline_name,
..         "status": "success",
..         "load_id": str(load_info.load_id) if hasattr(load_info, "load_id") else None,
..         "load_package_id": str(load_info.load_package_id) if hasattr(load_info, "load_package_id") else None,
..     }
