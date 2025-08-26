2.1. Extraction from Databases
==============================

This article explains how to extract data from various databases into a centralized data lake using Debizium and Apache Kafka. We will cover the architecture, setup, and best practices for implementing a robust data extraction pipeline.

.. contents:: Article Outline
	:local:
	:depth: 2

Overview
--------

Many organizations rely on databases for their operational data, but extracting that data for analytics can be challenging. Debizium is an open-source tool that simplifies change data capture (CDC) from databases, allowing you to stream changes in real-time to a data lake or other downstream systems. This article focuses on using Debizium with Apache Kafka to extract data from multiple databases and load it into a centralized data lake.

Architecture
------------

The architecture for extracting data from databases with Debizium typically involves the following components:

1. **Debizium Connectors**: These connectors are responsible for capturing changes from the source databases (e.g., MySQL, PostgreSQL) and publishing them to Kafka topics.
2. **Apache Kafka**: Kafka serves as the central messaging system, allowing you to decouple the data extraction process from the data loading process.
3. **Kafka Connect**: This component is used to move data between Kafka and other systems, such as your data lake (e.g., AWS S3, Google Cloud Storage).
4. **Data Lake**: The final destination for the extracted data, where it can be stored, processed, and analyzed.

Setup (Debezium + PostgreSQL on AWS)
------------------------------------

This section shows a practical setup for CDC from PostgreSQL (Amazon RDS or self-managed on EC2) into Kafka via Debezium, and then to S3 via a sink.

Prerequisites
^^^^^^^^^^^^^

- A running Kafka cluster and Kafka Connect (can be on EC2, EKS, or a managed service). Ensure network access from Connect to Postgres and S3.
- PostgreSQL with logical replication enabled (RDS parameter group or postgresql.conf):

  .. code-block:: text

	  wal_level = logical
	  max_replication_slots = 10     # adjust as needed
	  max_wal_senders = 10           # adjust as needed

- A replication user in Postgres with required privileges and REPLICATION role.
- Security groups/NACLs allowing Connect to reach Postgres (port 5432) and S3 egress.

RDS specifics
^^^^^^^^^^^^^

- Modify the DB parameter group to set ``wal_level=logical`` and associate with your RDS instance; apply and reboot if required.
- Ensure ``rds.logical_replication`` is enabled for certain engines/versions if applicable (check AWS docs).
- Grant appropriate permissions to your Debezium user and create a replication slot name that Debezium will use.

Debezium Postgres connector (generic config)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: code/debezium/postgres/connector_postgres_generic.json
	:language: json
	:linenos:

Posting the connector to Kafka Connect
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: code/debezium/postgres/create_connector.sh
	:language: bash
	:linenos:

S3 sink connector (generic config)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: code/debezium/sinks/s3_sink_generic.json
	:language: json
	:linenos:

Monitoring and operations
^^^^^^^^^^^^^^^^^^^^^^^^^

- Use Kafka Connect REST API to check connector/task status, offsets, and errors.
- Observe Postgres replication slots (``pg_replication_slots``) and lag; alert if WAL grows.
- Scale ``tasks.max`` and tune flush/rotate parameters in sink based on throughput and latency requirements.

Limitations and pitfalls
^^^^^^^^^^^^^^^^^^^^^^^^

- Initial snapshot: Large tables can take time; consider off-hours or ``snapshot.mode=never`` if you pre-seed data.
- Replication lag: Heavy write load or network issues increase lag; monitor WAL size to avoid storage pressure.
- DDL changes: Debezium emits schema change events; ensure downstream can adapt or route to a schema registry.
- Permissions: RDS Postgres requires proper roles for logical replication; ensure slot names are unique per connector.
- Topic naming: Use a topic prefix and include lists to control scope; avoid accidentally capturing entire databases.
- S3 sink dependencies: Confluent S3 sink requires appropriate licensing/dependencies; alternatively, consider Kafka Connect S3 sink alternatives (open-source) or write a custom consumer.

Best Practices
--------------

- **Schema Management**: Keep track of schema changes in your source databases and update your Kafka topics accordingly. Debizium can help with this by capturing schema changes as part of the change events.
- **Data Quality**: Implement data validation and cleansing processes in your data lake to ensure the extracted data is accurate and consistent.
- **Performance Tuning**: Monitor the performance of your Debizium connectors and Kafka cluster, and make adjustments as needed to optimize throughput and reduce latency.

Conclusion
----------

Debizium provides a powerful solution for extracting data from databases and streaming it to a data lake. By leveraging Kafka and a well-designed architecture, you can build a robust data extraction pipeline that meets your organization's analytics needs.
