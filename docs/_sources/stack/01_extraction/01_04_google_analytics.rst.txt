1.4. Extraction from Google Analytics
=====================================

.. import os
.. from datetime import timedelta

.. import pendulum
.. from airflow.decorators import dag, task, task_group
.. from airflow.models import Variable
.. from airflow.operators.empty import EmptyOperator
.. from airflow.operators.python import get_current_context
.. from airflow.providers.amazon.aws.operators.s3 import S3DeleteObjectsOperator
.. from airflow.providers.google.cloud.operators.gcs import GCSListObjectsOperator
.. from airflow.providers.google.cloud.sensors.bigquery import BigQueryTableExistenceSensor
.. from airflow.providers.google.cloud.transfers.bigquery_to_gcs import BigQueryToGCSOperator
.. from cosmos import DbtTaskGroup, RenderConfig

.. from include.operator.google.google_cloud_storage import GCSToS3CheckSummedOperator
.. from utils.constants.connections import AWS_DEFAULT_CONN, GCP_GA4_ECG_CONN
.. from utils.constants.dbt import (
..     COSMOS_RENDER_CONFIG,
..     DEFAULT_AIRFLOW_TO_DBT_VARS,
..     get_cosmos_base_config,
..     get_profile_config,
.. )
.. from utils.constants.domains import VIBRANCY_ENV
.. from utils.constants.platform import BERLIN_TZ, AstromerWorkerQueues
.. from utils.constants.vibrancy import BUCKET_VIBRANCY_PREFIX, ECG_PROJECT_ID, GCP_BUCKET_ECG

.. DATASET_ID = "analytics_151375460"


.. def create_extract_task_group(process_day: pendulum.DateTime, group_suffix: str):
..     @task_group(group_id=f"extract_{group_suffix}")
..     def extract_task_group():
..         @task
..         def get_source(process_day: pendulum.DateTime):
..             process_day_str = process_day.strftime("%Y%m%d")
..             table_name = f"events_{process_day_str}"
..             return f"{ECG_PROJECT_ID}.{DATASET_ID}.{table_name}"

..         @task
..         def get_destination(process_day: pendulum.DateTime):
..             event_date = process_day.strftime("%Y-%m-%d")
..             return f"gs://{GCP_BUCKET_ECG}/raw/ga4/{VIBRANCY_ENV.env}/event_date={event_date}/raw-data-*.zstd.parquet"

..         @task
..         def get_prefix(process_day: pendulum.DateTime):
..             event_date = process_day.strftime("%Y-%m-%d")
..             return f"raw/ga4/{VIBRANCY_ENV.env}/event_date={event_date}"

..         @task
..         def get_s3_prefix(process_day: pendulum.DateTime):
..             event_date = process_day.strftime("%Y-%m-%d")
..             return f"raw/ga4/event_date={event_date}"

..         extract_task = BigQueryToGCSOperator(
..             task_id="extract_bq_table",
..             source_project_dataset_table="{{ task_instance.xcom_pull(task_ids='extract.extract_"
..             + group_suffix
..             + ".get_source') }}",
..             destination_cloud_storage_uris=[
..                 "{{ task_instance.xcom_pull(task_ids='extract.extract_" + group_suffix + ".get_destination') }}"
..             ],
..             export_format="PARQUET",
..             compression="ZSTD",
..             gcp_conn_id=GCP_GA4_ECG_CONN,
..             force_rerun=True,
..         )

..         list_files = GCSListObjectsOperator(
..             task_id="list_created_files",
..             bucket=GCP_BUCKET_ECG,
..             prefix="{{ task_instance.xcom_pull(task_ids='extract.extract_" + group_suffix + ".get_prefix') }}",
..             gcp_conn_id=GCP_GA4_ECG_CONN,
..         )

..         @task
..         def create_tasks(files):
..             ls = []
..             for f in files:
..                 path = os.path.dirname(f)
..                 s3_path = path.replace(f"/{VIBRANCY_ENV.env}", "")
..                 ls.append(
..                     {
..                         "prefix": f,
..                         "dest_s3_key": f"s3://{BUCKET_VIBRANCY_PREFIX}-{VIBRANCY_ENV.env}/{s3_path}",
..                     }
..                 )

..             return ls

..         tasks = create_tasks(list_files.output)

..         clear_s3_partition = S3DeleteObjectsOperator(
..             task_id="clear_s3_partition",
..             bucket=f"{BUCKET_VIBRANCY_PREFIX}-{VIBRANCY_ENV.env}",
..             prefix="{{ task_instance.xcom_pull(task_ids='extract.extract_" + group_suffix + ".get_s3_prefix') }}",
..             aws_conn_id=AWS_DEFAULT_CONN,
..         )

..         sync = GCSToS3CheckSummedOperator.partial(
..             gcs_bucket=GCP_BUCKET_ECG,
..             # prefix=None, set via kwargs
..             task_id="gcs_to_s3",
..             gcp_conn_id=GCP_GA4_ECG_CONN,
..             dest_aws_conn_id=AWS_DEFAULT_CONN,
..             # dest_s3_key=None, set via kwargs
..             replace=True,
..             retries=3,
..             queue=AstromerWorkerQueues.GOOGLE_TO_S3.value,
..             check_local_integrity=False,
..         ).expand_kwargs(tasks)

..         (
..             [get_source(process_day), get_destination(process_day), get_prefix(process_day), get_s3_prefix(process_day)]
..             >> extract_task
..             >> list_files
..             >> tasks
..             >> clear_s3_partition
..             >> sync
..         )

..     return extract_task_group()


.. @dag(
..     dag_id="process_raw_ga4",
..     start_date=pendulum.datetime(2025, 1, 1, tz=BERLIN_TZ),
..     schedule="10 12 * * *",
..     catchup=False,
..     tags=["vibrancy"],
..     default_args={**VIBRANCY_ENV.default_args, "retries": 2},
..     params={"process_start": None, "process_end": None},
.. )
.. def dag():
..     @task_group(group_id="setup")
..     def setup():
..         @task
..         def get_run_cfg():
..             context = get_current_context()
..             process_day = pendulum.instance(context["data_interval_start"])
..             process_day_str = process_day.strftime("%Y%m%d")
..             return f"events_{process_day_str}"

..         check_dataset = BigQueryTableExistenceSensor(
..             task_id="check_dataset_exists",
..             project_id=ECG_PROJECT_ID,
..             dataset_id=DATASET_ID,
..             table_id="{{ task_instance.xcom_pull(task_ids='setup.get_run_cfg') }}",
..             gcp_conn_id=GCP_GA4_ECG_CONN,
..             poke_interval=600,  # Poke every 10 minutes
..             silent_fail=True,  # If the table is not ready, don't fail for 404
..             mode="reschedule",
..         )

..         finalize_setup = EmptyOperator(task_id="finalize_setup")

..         cfg = get_run_cfg()
..         cfg >> check_dataset >> finalize_setup

..     @task
..     def get_data_interval_start():
..         context = get_current_context()
..         return pendulum.instance(context["data_interval_start"])

..     @task
..     def get_data_interval_start_minus_1():
..         context = get_current_context()
..         return pendulum.instance(context["data_interval_start"]) - timedelta(days=1)

..     # @task
..     # def get_data_interval_start_minus_2():
..     #    context = get_current_context()
..     #    return pendulum.instance(context["data_interval_start"]) - timedelta(days=2)

..     @task_group(group_id="extract")
..     def extract():
..         current_day = get_data_interval_start()
..         previous_day = get_data_interval_start_minus_1()
..         # two_days_ago = get_data_interval_start_minus_2()
..         extract_task_group1 = create_extract_task_group(current_day, "extract_data_interval_start")
..         extract_task_group2 = create_extract_task_group(previous_day, "extract_data_interval_start_minus_1")
..         # extract_task_group3 = create_extract_task_group(two_days_ago, "extract_data_interval_start_minus_2")
..         return [extract_task_group1, extract_task_group2]

..     @task_group(group_id="transform")
..     def transform():
..         ga4_vars = DEFAULT_AIRFLOW_TO_DBT_VARS.copy()
..         ga4_vars["ga4_decrypt_key"] = Variable.get("vibrancy/ga4_decrypt", default_var="DUMMY_KEY")
..         dbt_run_stage = DbtTaskGroup(  # noqa
..             group_id="ga4_staging",
..             profile_config=get_profile_config(VIBRANCY_ENV, True),
..             render_config=RenderConfig(
..                 **COSMOS_RENDER_CONFIG,
..                 select=[
..                     "path:models/vibrancy/stage/ga4/raw_events",
..                     "path:models/vibrancy/stage/ga4/raw_split",
..                     "path:models/vibrancy/core/ga4/hit_step1",
..                     "path:models/vibrancy/stage/ga4/session_step1",
..                     "path:models/vibrancy/core/ga4/session_step1",
..                     "path:models/vibrancy/core/ga4/hit_w",
..                     "path:models/vibrancy/core/ga4/ins_hit",
..                     "path:models/vibrancy/core/ga4/session_w",
..                     "path:models/vibrancy/core/ga4/ins_session",
..                 ],
..             ),
..             **get_cosmos_base_config(ga4_vars),
..         )
..         return

..     start = EmptyOperator(task_id="start")
..     setup = setup()
..     extract = extract()
..     transform = transform()
..     end = EmptyOperator(task_id="end")

..     start >> setup >> extract >> transform >> end


.. dag()
