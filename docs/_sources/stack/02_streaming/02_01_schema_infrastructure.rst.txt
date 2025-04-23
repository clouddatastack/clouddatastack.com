2.1. Streaming Infrastructure
=============================

Real-time data pipelines rely on robust streaming infrastructure. This page outlines the building blocks of a modern streaming system, including schema design, stream architecture, emitters and sinks, and integration using Kafka Connect.

Stream Design
-------------

A **stream** is typically represented as a Kafka topic. Structuring your streams well ensures clarity, reusability, and performance.

**Best practices:**

- Use domain-based topic names: ``ecommerce.orders.created``
- Prefer one event type per topic unless there’s a strong reason to combine
- Version topics if breaking schema changes are expected (e.g., ``orders.v2``)

**Partitioning guidelines:**

- Partition by IDs (``order_id``, ``user_id``) for ordering guarantees  
  Kafka only guarantees order *within* a partition — so all events for the same ID must go to the same partition to preserve sequence.

  *Example (using user_id as key in Python):*

  .. code-block:: python

     key = record["user_id"].encode("utf-8")
     producer.send("user-events", key=key, value=record)

  *Example (compound key with user_id + session_id):*

  .. code-block:: python

     compound_key = f"{record['user_id']}:{record['session_id']}".encode("utf-8")
     producer.send("session-events", key=compound_key, value=record)

- Use high-cardinality keys to distribute load  
  High cardinality — many unique values — helps spread records across partitions evenly, preventing hot spots and enabling parallel processing.

  *Example (use session_id to spread load):*

  .. code-block:: python

     key = record["session_id"].encode("utf-8")
     producer.send("clickstream", key=key, value=record)

- Ensure partitions are balanced for parallelism, **after** the data has already landed in Kafka  
  When producer-side keys are suboptimal, you can still improve distribution by:

  • **Rekeying in stream processors**: consume events, assign a high-cardinality key (e.g., ``user_id``), and write to a new topic with better partitioning.

  *Example (Faust rekeying by user_id):*

  .. code-block:: python

     import faust

     app = faust.App("rekeying-app", broker="kafka://localhost:9092")

     class Event(faust.Record):
         user_id: str
         event_type: str

     source = app.topic("events_by_country", value_type=Event)
     target = app.topic("events_by_user", key_type=str, value_type=Event)

     @app.agent(source)
     async def process(events):
         async for event in events:
             await target.send(key=event.user_id, value=event)

  • **Custom partitioner**: Implement logic in your producer to assign partitions manually when default hashing is insufficient.

  • **Increase partition count**: More partitions allow greater consumer parallelism, especially useful when keys can’t be optimized at the source.

Event Schemas
-------------

Defining consistent, versioned event schemas is key to reliable and scalable stream processing.

**Why schemas matter:**

- Enforce data contracts between producers and consumers
- Validate structure before sending/processing events
- Enable safe schema evolution
- Power downstream automation (e.g., code generation, analytics models)

Formats
-------

AVRO is the most commonly used for Kafka events due to its balance of compactness and compatibility features.

Versioning Strategy
-------------------

**Types of changes:**

- *Non-breaking changes* (schema evolution allowed on same topic):
  - Add optional fields with defaults
  - Add new fields with `null` union types
  - Change logical types (e.g., add `timestamp-millis`)

- *Breaking changes* (requires new topic version):
  - Remove or rename fields
  - Change required field types
  - Modify enum values incompatibly

**Best practices:**

- Use schema evolution for safe, additive changes
- For breaking changes, publish to a new topic (e.g., `orders.v2`)
- Version schema files and record names to make changes explicit:

.. code-block:: bash

   schemas/
     orders/
       order_created.v1.avsc
       order_created.v2.avsc

.. code-block:: json

   {
     "type": "record",
     "name": "OrderCreatedV2",
     "namespace": "ecommerce.orders.v2",
     // remaining fields omitted
   }

This versioning convention allows producers and consumers to gradually migrate, while preserving backward compatibility where possible.

.. Coming Soon: Schema Registry + Codegen Repo
.. -------------------------------------------

.. We'll provide a public example repository with:

.. - AVRO-based schemas organized by domain
.. - A workflow for PR review and schema approval
.. - CI pipeline to:
..   - Register schemas to Kafka Schema Registry
..   - Generate strongly typed classes for JavaScript/TypeScript, Java, and iOS
..   - Publish generated libraries or zip artifacts

.. **Link to repo:** *(coming soon)*

.. Emitters (Producers)
.. --------------------

.. Event emitters are systems or applications that write messages into Kafka topics.

.. **Examples:**

.. - Microservices emitting `UserRegistered`, `OrderPlaced`, etc.
.. - Databases with change data capture tools like **Debezium**
.. - IoT devices or log aggregators

.. **Tips:**

.. - Validate schema before emitting
.. - Include metadata fields like `event_type`, `timestamp`, and `source`
.. - Use consistent naming and types

.. Sinks (Consumers)
.. -----------------

.. Event sinks consume data from Kafka and send it to storage or downstream processors.

.. **Common sinks:**

.. - Data lakes (S3, GCS)
.. - Data warehouses (Snowflake, BigQuery)
.. - Real-time processors (Apache Flink, Spark Streaming)

.. **Ensure:**

.. - Schema compatibility is respected
.. - Fault tolerance and at-least-once delivery where needed

.. Kafka Connect
.. -------------

.. **Kafka Connect** is a framework for connecting Kafka with external systems using pluggable source and sink connectors.

.. **Advantages:**

.. - No custom code required
.. - Supports config-based deployment
.. - Built-in scalability and fault-tolerance

.. **Popular connectors:**

.. - **Sources**: PostgreSQL, MySQL, MongoDB
.. - **Sinks**: S3, Elasticsearch, BigQuery

.. **Example config (S3 Sink):**

.. .. code-block:: json

..    {
..      "name": "s3-sink",
..      "config": {
..        "connector.class": "io.confluent.connect.s3.S3SinkConnector",
..        "topics": "orders",
..        "s3.bucket.name": "my-data-bucket",
..        "format.class": "io.confluent.connect.s3.format.avro.AvroFormat",
..        "schema.compatibility": "BACKWARD"
..      }
..    }

.. Deployment Recommendations
.. --------------------------

.. **Local development:**

.. Use Docker Compose with:

.. - Kafka broker
.. - Schema Registry
.. - Kafka Connect

.. **Production setup:**

.. - Helm charts (Bitnami or Confluent)
.. - Confluent Cloud (fully managed)
.. - AWS MSK + self-managed Connect and Registry

.. **Security & monitoring:**

.. - TLS encryption, SASL authentication, and ACLs
.. - Monitor with Prometheus, Grafana, OpenTelemetry

.. Best Practices
.. --------------

.. - Central schema repository + CI checks for compatibility
.. - Use partition keys with high cardinality
.. - Favor AVRO for compact payloads and schema evolution
.. - Reuse logical types and standard metadata fields
.. - Stream retention: define based on replay needs and SLA

.. Conclusion
.. ----------

.. Streaming infrastructure provides the foundation for building scalable, real-time data systems.

.. **Next steps:**

.. - Set up a local Kafka + Schema Registry stack
.. - Create a schema repo with evolution checks
.. - Start streaming events with confidence

