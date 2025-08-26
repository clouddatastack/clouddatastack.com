6.1 Schedule With Airflow
=================================

How to schedule your Workloads on Databricks with Airflow.

.. contents:: Article Outline
   :local:
   :depth: 2

Introduction
------------
*   Brief overview of using Airflow, specifically AWS Managed Workflows for Apache Airflow (MWAA), to orchestrate workloads on Databricks.
*   Benefits: robust scheduling, dependency management, visibility, and centralized workflow management.
*   Article Goal: Guide readers through setting up a production-ready Airflow project for Databricks, emphasizing:

    *   AWS MWAA for deployment.
    *   Python project setup with the ``uv`` package manager.
    *   Scheduling dbt SQL models, Databricks notebooks, and general Python/Bash DAGs.
    *   Local development using Docker.
    *   Managing test and production environments.
*   Reference to a Template Project: This article uses examples and principles from the `clouddatastack/aws-airflow-databricks <https://github.com/clouddatastack/aws-airflow-databricks>`_ template project.

Core Requirements & Design Considerations
-----------------------------------------
*   **Workload Diversity**: Effectively scheduling and managing:

    *   dbt Core SQL models.
    *   Databricks notebooks.
    *   General purpose Airflow DAGs (e.g., Python scripts, Bash commands).
*   **Environment Parity**:

    *   Local Development: Airflow running in Docker, connecting to a test Databricks workspace.
    *   Test Environment: Airflow (MWAA or local) targeting a dedicated test Databricks workspace.
    *   Production Environment: AWS MWAA targeting the production Databricks workspace.
*   **Package Management**: Utilizing ``uv`` for fast and efficient Python dependency management.
*   **Deployment**: Specifics of deploying to and configuring AWS MWAA.
*   **Configuration Management**: Handling connections, variables, and configurations across different environments.

Recommended Project Structure
-----------------------------
A well-organized project structure is crucial for maintainability and scalability.

::

  airflow-databricks-project/
  ├── dags/                     # Airflow DAGs
  │   ├── common/               # Common utilities, custom operators, hooks
  │   │   ├── __init__.py
  │   │   └── utils.py          # Placeholder for shared utilities
  │   ├── dbt_runs/             # DAGs for running dbt tasks
  │   │   ├── __init__.py
  │   │   └── dag_dbt_daily_models.py
  │   ├── notebook_jobs/        # DAGs for running Databricks notebooks
  │   │   ├── __init__.py
  │   │   └── dag_notebook_etl.py
  │   └── generic_tasks/        # General purpose DAGs
  │       ├── __init__.py
  │       └── dag_generic_data_pipeline.py
  ├── plugins/                  # Custom Airflow plugins (if any)
  │   └── __init__.py
  ├── dbt_project/              # Your dbt project
  │   ├── dbt_project.yml
  │   ├── models/
  │   └── ...
  ├── notebooks_source/         # Source Databricks notebooks
  │   └── etl_notebook.py       # Example ETL notebook
  ├── requirements/             # Python dependencies
  │   ├── base.in               # Abstract dependencies for uv compile (e.g., apache-airflow, apache-airflow-providers-databricks)
  │   ├── base.txt              # Pinned dependencies for Airflow (local & MWAA)
  │   ├── dev.in                # Development specific dependencies
  │   └── dev.txt               # Pinned dev dependencies
  ├── tests/                    # Automated tests
  │   ├── dags/                 # DAG integrity and unit tests
  │   └── operators/            # Tests for custom operators
  ├── scripts/                  # Helper scripts (e.g., deployment, local env setup)
  │   └── setup_local_env.sh    # Example script for local setup
  ├── Dockerfile                # For local Airflow development environment
  ├── docker-compose.yml        # For orchestrating local Airflow services
  ├── .env.example              # Example environment variables
  └── README.md

*   **Rationale**:

    *   `dags/`: Clear separation of DAGs by purpose (dbt, notebooks, generic).
    *   `dags/common/`: Promotes DRY principles by centralizing shared code.
    *   `requirements/`: Manages dependencies clearly for different contexts using ``uv`` for generation.
    *   `notebooks_source/`: Keeps source notebooks version-controlled; these would be deployed to Databricks (e.g., via DBFS or Databricks Repos).

Python Project Setup with ``uv``
--------------------------------
``uv`` is a fast Python package installer and resolver.

*   **Virtual Environment with ``uv``**:

    .. code-block:: bash

       # Create a virtual environment
       uv venv
       source .venv/bin/activate

*   **Managing Dependencies**:

    *   Use ``*.in`` files for abstract dependencies and ``uv pip compile`` to generate pinned ``*.txt`` files.

    .. code-block:: bash

       # Compile base requirements
       uv pip compile requirements/base.in -o requirements/base.txt

       # Install requirements
       uv pip sync requirements/base.txt

*   **Integration with Docker**: The ``Dockerfile`` will use the generated ``requirements/base.txt`` (from ``requirements/base.in``) for the Airflow image. The template project\'s ``Dockerfile`` demonstrates this:

    .. code-block:: dockerfile

       # Start from a Python base image to use uv fully
       FROM python:3.10-slim

       ENV AIRFLOW_HOME=/opt/airflow
       ENV AIRFLOW__CORE__DAGS_FOLDER=${AIRFLOW_HOME}/dags
       ENV AIRFLOW__CORE__LOAD_EXAMPLES=False
       ENV AIRFLOW__CORE__EXECUTOR=LocalExecutor

       # Install uv
       RUN pip install --no-cache-dir uv

       WORKDIR $AIRFLOW_HOME
       COPY requirements/base.txt .
       # Install Python dependencies using uv
       RUN uv pip sync base.txt --system --no-cache

       COPY dags/ ./dags/
       COPY plugins/ ./plugins/

       EXPOSE 8080
       CMD ["airflow", "standalone"]

Configuring for AWS MWAA
------------------------
*   **S3 Bucket**: MWAA requires an S3 bucket for DAGs, plugins, and the ``requirements.txt`` file.
*   **`requirements.txt` for MWAA**:

    *   Upload your ``requirements/base.txt`` (compiled by ``uv`` from ``requirements/base.in``) to the S3 bucket.
    *   Ensure it includes necessary providers, e.g., ``apache-airflow-providers-databricks``, ``apache-airflow>=2.8.0`` (or your target version).
*   **IAM Roles & Permissions**:

    *   MWAA Execution Role: Needs permissions to access S3, CloudWatch Logs, and to assume roles for accessing other services like Databricks.
    *   Databricks Access: Configure Databricks connection in Airflow using a Databricks personal access token (PAT) or Azure AD service principal, stored securely (e.g., AWS Secrets Manager and referenced in Airflow connection).
*   **Environment Variables in MWAA**: For Databricks host, tokens, cluster IDs, etc.
*   *Reference*: `AWS MWAA User Guide <https://docs.aws.amazon.com/mwaa/latest/userguide/what-is-mwaa.html>`_

Scheduling Databricks Workloads
-------------------------------

1.  **Databricks Connection in Airflow**:

    *   Create a Databricks connection in the Airflow UI or via environment variables.
    *   Key fields: ``databricks_conn_id`` (e.g., ``databricks_default``), ``host``, ``token`` (or other auth methods like Azure Service Principal).
    *   *Code Example (Environment Variable for Connection in ``docker-compose.yml`` or MWAA)*:

        .. code-block:: bash

           AIRFLOW_CONN_DATABRICKS_DEFAULT=\\\'{\\n\\
               "conn_type": "databricks",\\n\\
               "host": "https://your-databricks-instance.azuredatabricks.net",\\n\\
               "token": "dapiXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",\\n\\
               "extra": {"job_cluster_name_prefix": "airflow-local-"}\\n\\
           }\\\'

2.  **Scheduling Databricks Notebooks**:

    *   Use ``DatabricksSubmitRunOperator`` for submitting notebook tasks as new jobs.
    *   *Code Example (from ``dags/notebook_jobs/dag_notebook_etl.py``)*:

        .. code-block:: python

           from airflow.models.dag import DAG
           from airflow_providers_databricks.operators.databricks import DatabricksSubmitRunOperator
           import pendulum

           with DAG(
               dag_id=\\\'databricks_notebook_etl_example\\\',
               start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
               schedule_interval=\\\'@daily\\\',
               catchup=False,
               tags=[\\\'databricks\\\', \\\'notebook\\\'],
           ) as dag:
               submit_notebook_task = DatabricksSubmitRunOperator(
                   task_id=\\\'run_etl_notebook\\\',
                   databricks_conn_id=\\\'databricks_default\\\',
                   new_cluster={
                       \\\'spark_version\\\': \\\'13.3.x-scala2.12\\\', # Or your desired Spark version
                       \\\'node_type_id\\\': \\\'i3.xlarge\\\',    # Choose appropriate instance type
                       \\\'num_workers\\\': 2,
                   },
                   notebook_task={
                       \\\'notebook_path\\\': \\\'/Shared/airflow_notebooks/etl_notebook.py\\\', # Adjust path in Databricks
                       \\\'base_parameters\\\': {\\\'param1\\\': \\\'value_from_airflow\\\', \\\'date\\\': \\\'{{ ds }}\\\'}
                   },
               )

3.  **Scheduling dbt Workloads**:

    *   **Strategy**: The template project uses ``DatabricksSubmitRunOperator`` with a ``spark_python_task`` that points to a Python script on DBFS. This script is responsible for invoking dbt CLI commands.
    *   This requires:

        *   Your dbt project to be accessible by the Databricks job (e.g., synced via Databricks Repos, or copied to DBFS).
        *   A Python script (e.g., ``dbt_runner_script.py``) on DBFS that can execute dbt commands.
        *   The Databricks cluster (either new or existing) must have dbt installed (e.g., via init scripts or by using a custom Docker container for the cluster).
    *   *Code Example (from ``dags/dbt_runs/dag_dbt_daily_models.py``)*:

        .. code-block:: python

           from airflow.models.dag import DAG
           from airflow_providers_databricks.operators.databricks import DatabricksSubmitRunOperator
           import pendulum

           with DAG(
               dag_id=\\\'dbt_daily_models_example\\\',
               start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
               schedule_interval=\\\'@daily\\\',
               catchup=False,
               tags=[\\\'dbt\\\', \\\'databricks\\\'],
           ) as dag:
               dbt_run_models = DatabricksSubmitRunOperator(
                   task_id=\\\'dbt_run_daily_models\\\',
                   databricks_conn_id=\\\'databricks_default\\\',
                   new_cluster={
                       \\\'spark_version\\\': \\\'13.3.x-scala2.12\\\',
                       \\\'node_type_id\\\': \\\'i3.xlarge\\\',
                       \\\'num_workers\\\': 1,
                       # \\\'init_scripts\\\': [ { \\\'dbfs\\\': { \\\'destination\\\': \\\'dbfs:/FileStore/scripts/dbt_install.sh\\\' } } ] # Example init script
                   },
                   spark_python_task={
                       \\\'python_file\\\': \\\'dbfs:/path/to/your/dbt_runner_script.py\\\', # IMPORTANT: Create this script
                       \\\'parameters\\\': [
                           \\\'run\\\',
                           \\\'--models\\\', \\\'tag:daily\\\',
                           \\\'--project-dir\\\', \\\'/path/to/your/dbt_project/in/repo_or_dbfs\\\', # e.g., /dbfs/dbt_projects/my_dbt_project or /Workspace/Repos/user/my_dbt_project
                           \\\'--profiles-dir\\\', \\\'/path/to/your/profiles_dir\\\' # e.g., /dbfs/dbt_projects/my_dbt_project or /Workspace/Repos/user/my_dbt_project
                       ]
                   }
               )
    *   *Considerations for dbt runner script*: This script would typically use ``subprocess.run()`` to execute dbt commands. It needs to handle paths to the dbt project and profiles correctly within the Databricks execution environment.

4.  **Scheduling General Python/Bash DAGs**:

    *   Standard Airflow operators like ``PythonOperator``, ``BashOperator``. These run on the Airflow worker.
    *   For interactions with Databricks API from these operators: use ``databricks-sdk`` within a ``PythonOperator``.
    *   *Code Example (from ``dags/generic_tasks/dag_generic_data_pipeline.py``)*:

        .. code-block:: python

           from airflow.models.dag import DAG
           from airflow.operators.python import PythonOperator
           from airflow.operators.bash import BashOperator
           import pendulum

           def my_python_callable():
               print("Running general Python task!")
               return "Python task finished."

           def another_python_callable(**kwargs):
               ti = kwargs[\\\'ti\\\']
               pulled_value = ti.xcom_pull(task_ids="simple_python_task")
               print(f"Pulled value: {pulled_value}")

           with DAG(
               dag_id=\\\'general_python_bash_pipeline_example\\\',
               start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
               schedule=\\\'@daily\\\',
               catchup=False,
               tags=[\\\'generic\\\', \\\'python\\\', \\\'bash\\\'],
           ) as dag:
               python_task = PythonOperator(
                   task_id=\\\'simple_python_task\\\',
                   python_callable=my_python_callable
               )
               bash_task = BashOperator(
                   task_id=\\\'simple_bash_task\\\',
                   bash_command=\\\'echo "Running Bash command! Today is $(date)"\\\'
               )
               python_task_with_xcom = PythonOperator(
                   task_id=\\\'python_task_using_xcom\\\',
                   python_callable=another_python_callable
               )
               python_task >> bash_task >> python_task_with_xcom

Local Development with Docker
-----------------------------
*   **`Dockerfile` for Airflow**:

    *   The template project\'s ``Dockerfile`` starts from ``python:3.10-slim``, installs ``uv``, copies ``requirements/base.txt``, and uses ``uv pip sync base.txt --system`` to install dependencies. It then copies DAGs and plugins.
    *   *Key `Dockerfile` instructions (refer to template for full file)*:

        .. code-block:: dockerfile

           FROM python:3.10-slim
           ENV AIRFLOW_HOME=/opt/airflow
           # ... other ENV VARS ...
           RUN pip install --no-cache-dir uv
           WORKDIR $AIRFLOW_HOME
           COPY requirements/base.txt .
           RUN uv pip sync base.txt --system --no-cache
           COPY dags/ ./dags/
           COPY plugins/ ./plugins/
           # ...
           CMD ["airflow", "standalone"]

*   **`docker-compose.yml`**:

    *   The template project\'s ``docker-compose.yml`` defines services for ``postgres``, ``airflow-init`` (to initialize DB and create user), ``airflow-webserver``, and ``airflow-scheduler``.
    *   It uses the local ``Dockerfile`` (``build: .``) for Airflow services.
    *   Volumes are mounted for ``./dags``, ``./plugins``, and ``./logs``.
    *   Crucially, it sets environment variables, including ``AIRFLOW_CONN_DATABRICKS_DEFAULT`` for the local Databricks connection, and ``AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`` for the Postgres backend.
    *   *Code Snippet (`docker-compose.yml` excerpt)*:

        .. code-block:: yaml

           version: \\\'3.8\\\'
           x-airflow-common: &airflow-common
             build: . # Uses the Dockerfile in the current directory
             environment:
               &airflow-common-env
               AIRFLOW__CORE__EXECUTOR: LocalExecutor
               AIRFLOW__CORE__LOAD_EXAMPLES: \\\'false\\\'
               AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
               AIRFLOW__CORE__FERNET_KEY: \\\'FB0o_zt3333qL9jAbELJ7z3gLh2aK3N2ENc2Ld1sL_Y=\\\' # Replace for production
               AIRFLOW_CONN_DATABRICKS_DEFAULT: \\\'{ ... your local databricks connection ... }\\\'
             volumes:
               - ./dags:/opt/airflow/dags
               - ./plugins:/opt/airflow/plugins
               - ./logs:/opt/airflow/logs
             depends_on:
               postgres:
                 condition: service_healthy
               airflow-init:
                 condition: service_completed_successfully

           services:
             postgres:
               image: postgres:13
               # ... postgres config ...
             airflow-init:
               <<: *airflow-common
               container_name: airflow-init
               entrypoint: /bin/bash
               command:
                 - -c
                 - | # Initializes DB and creates admin user
                   set -e; if [ ! -f "/opt/airflow/airflow_db_initialized.flag" ]; then
                     airflow db init;
                     airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@example.com || true;
                     touch /opt/airflow/airflow_db_initialized.flag; fi;
                   airflow db upgrade;
               restart: on-failure
             airflow-webserver:
               <<: *airflow-common
               command: webserver
               ports: ["8080:8080"]
               # ... healthcheck & restart ...
             airflow-scheduler:
               <<: *airflow-common
               command: scheduler
               # ... healthcheck & restart ...
           volumes:
             airflow-db-volume: # Persists Postgres data

Managing Environments (Test vs. Prod)
-------------------------------------
*   **Airflow Variables & Connections**:

    *   Define separate connections for test and prod Databricks workspaces: e.g., ``databricks_test``, ``databricks_prod``.
    *   Use Airflow Variables for environment-specific parameters (cluster IDs, paths, instance pool IDs).
    *   *Code Example (Accessing variables in DAG)*:

        .. code-block:: python

           from airflow.models import Variable

           databricks_conn_id = Variable.get("databricks_conn_id", default_var="databricks_test")
           target_cluster_id = Variable.get("databricks_target_cluster_id_prod" if databricks_conn_id == "databricks_prod" else "databricks_target_cluster_id_test")

*   **Branching Strategy**:

    *   E.g., ``develop`` branch for test environment, ``main`` branch for production.
    *   Changes are merged from ``develop`` to ``main`` after successful testing.
*   **CI/CD**:

    *   Automate deployment of DAGs and ``requirements.txt`` to MWAA\'s S3 bucket upon merges to ``main``.
    *   Automate testing (DAG validation, unit tests) in CI pipeline.
*   **DAG Parameterization**: Design DAGs to dynamically pick up configurations based on the environment (e.g., by checking an Airflow Variable like ``environment=prod``).

Potential Tradeoffs and Considerations
--------------------------------------
*   **Monorepo vs. Polyrepo**:

    *   **Monorepo (Airflow + dbt + Notebooks in one repo)**:

        *   *Pros*: Simplified dependency management if shared, easier to coordinate changes.
        *   *Cons*: Can become large, tighter coupling, build/CI times might increase.
    *   **Polyrepo (Separate repos for Airflow, dbt, etc.)**:

        *   *Pros*: Clear ownership, independent release cycles, focused CI/CD.
        *   *Cons*: More complex to manage cross-repo dependencies and coordination.
    *   *Recommendation*: Start with a monorepo for simplicity if the team is small and projects are tightly linked. Consider polyrepo as complexity grows.
*   **Complexity of Local Setup vs. MWAA**:

    *   Strive for similarity, but exact replication can be hard (e.g., MWAA\'s specific execution environment).
    *   ``uv`` helps by producing a standard ``requirements.txt`` that ``pip`` (used by MWAA) understands.
*   **Databricks Operator Choices**:

    *   ``DatabricksSubmitRunOperator``: Submits a new one-time run. Good for dynamic tasks.
    *   ``DatabricksRunNowOperator``: Triggers an existing Databricks job. Good if jobs are pre-defined in Databricks UI/API.
    *   Consider how job definitions are managed (Airflow-defined vs. Databricks-defined).
*   **dbt Integration Strategy**:

    *   Running dbt via ``DatabricksSubmitRunOperator`` (as shown in the template\'s ``dag_dbt_daily_models.py``):

        *   *Pros*: Leverages Databricks compute, can handle large dbt projects, keeps dbt execution close to data.
        *   *Cons*: Requires managing the dbt project on Databricks (Repos/DBFS), a runner script, and ensuring dbt is installed on the cluster.
    *   Using Airflow dbt providers (e.g., ``astronomer-cosmos``, ``airflow-dbt-python``):

        *   *Pros*: Can simplify DAG authoring, potentially better Airflow UI integration for dbt tasks.
        *   *Cons*: Adds another layer of abstraction, might have different dependency or execution model.
    *   Tradeoffs involve cost, execution environment, ease of debugging, and dependency management for dbt itself. The template\'s approach gives more control over the dbt execution environment on Databricks.
*   **Dependency Management with ``uv`` and MWAA**:

    *   MWAA uses ``pip`` with a ``requirements.txt``. ``uv`` is used locally to *generate* this ``requirements.txt``.
    *   Ensure Python versions are compatible between local Docker and MWAA environment.
*   **Testing Strategy**:

    *   DAG validation tests (``airflow dags test``).
    *   Unit tests for custom operators/hooks.
    *   Integration tests (running DAGs against a test Databricks environment) can be complex and costly but provide high confidence.
*   **Cost Management**:

    *   MWAA pricing.
    *   Databricks cluster costs (interactive vs. job clusters, instance types, auto-scaling).
    *   Optimize DAGs: avoid unnecessary task runs, use efficient cluster configurations.

Other Common Concerns
---------------------
*   **Security**:

    *   Secrets Management: Use AWS Secrets Manager for sensitive data (like Databricks tokens) and integrate with Airflow Connections.
    *   IAM Permissions: Follow the principle of least privilege for MWAA execution role and Databricks service principals/users.
    *   Network Configuration: MWAA VPC setup, security groups, private networking to Databricks if needed.
*   **Monitoring and Alerting**:

    *   Airflow UI for DAG status.
    *   AWS CloudWatch for MWAA logs, metrics, and alarms.
    *   Configure Airflow alerts (e.g., on task failure) via email, Slack (e.g., ``SlackAPIPostOperator``).
*   **Scalability**:

    *   MWAA Environment Sizing: Choose appropriate instance class for MWAA.
    *   Databricks Cluster Optimization: Right-size clusters, use instance pools, auto-scaling.
    *   DAG Design: Maximize parallelism, avoid bottlenecks.
*   **Idempotency**: Design tasks to be rerunnable without causing duplicate data or incorrect states.
*   **Backfills**: Plan for how to run DAGs for historical periods. Airflow\'s ``catchup=True`` and manual triggering.
*   **DAG Versioning & Promotion**:

    *   Use Git for version control of DAGs.
    *   Promotion through environments (Dev -> Test -> Prod) typically handled by CI/CD and S3 sync strategies for MWAA.

Conclusion
----------
*   Recap of key elements: structured project (based on `clouddatastack/aws-airflow-databricks`), ``uv`` for dependencies, Docker for local dev, MWAA for deployment, robust Databricks integration.
*   Emphasis on the importance of a well-thought-out project structure and operational practices from the start.
*   Encouragement to adapt the provided template and guidelines to specific organizational needs and scale.

References
----------
*   Template Project: `clouddatastack/aws-airflow-databricks <https://github.com/clouddatastack/aws-airflow-databricks>`_
*   `AWS Managed Workflows for Apache Airflow (MWAA) Documentation <https://docs.aws.amazon.com/mwaa/latest/userguide/>`_
*   `Airflow Databricks Provider Documentation <https://airflow.apache.org/docs/apache-airflow-providers-databricks/stable/index.html>`_
*   `uv Documentation <https://github.com/astral-sh/uv>`_
*   `dbt Documentation <https://docs.getdbt.com/>`_
*   `Databricks Documentation <https://docs.databricks.com/>`_