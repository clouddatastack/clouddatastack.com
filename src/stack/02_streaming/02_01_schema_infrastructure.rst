2.1. Streaming Infrastructure
=============================

Real-time data pipelines rely on robust streaming infrastructure. This page outlines the building blocks of a modern streaming system, including schema design, stream architecture, emitters and sinks, and integration using Kafka Connect.

Overview
--------

- Stream Design
- Schema Management
- Event Producers
- Event Consumers
- Kafka Connect

Stream Design
-------------

A **stream** is typically represented as a Kafka topic.  
Structuring your streams well ensures clarity, reusability, and performance across services.

**Best practices for topic design:**

- Use domain-based topic names: ``ecommerce.orders.created``
- Prefer one event type per topic unless there's a strong operational reason to combine
- Version topics if breaking schema changes are expected (e.g., ``orders.v2``)
- Avoid topics that mix unrelated domains or concerns

Partitioning guidelines
------------------------

Kafka guarantees ordering *within* a partition only — events for the same entity must be routed consistently to the same partition.

**Partition by business identifiers** (e.g., ``order_id``, ``user_id``) to guarantee ordering.

*Example (using ``user_id`` as key):*

.. code-block:: python

   key = record["user_id"].encode("utf-8")
   producer.send("user-events", key=key, value=record)

*Example (compound key with ``user_id`` + ``session_id``):*

.. code-block:: python

   compound_key = f"{record['user_id']}:{record['session_id']}".encode("utf-8")
   producer.send("session-events", key=compound_key, value=record)

**Use high-cardinality keys** to distribute load evenly across partitions.  
High cardinality (many unique keys) helps avoid "hot" partitions and enables parallel consumer processing.

*Example (using ``session_id`` to spread load):*

.. code-block:: python

   key = record["session_id"].encode("utf-8")
   producer.send("clickstream", key=key, value=record)

**Plan partition count carefully** during topic creation.  
More partitions allow higher parallelism but increase management overhead.  
Partition count can be increased later if needed, but reassigning partitions across brokers has operational impacts.

**Improve partition distribution after ingestion if needed:**

- **Rekey in stream processors**: Consume events, assign a better partitioning key, and produce to a new topic.

  *Example (rekeying using Faust, by ``user_id``):*

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

- **Custom partitioners**: Implement producer-side logic to control partition assignment beyond default hashing.
- **Increase partition count**: Add more partitions when consumer throughput must scale, but manage impact carefully.

Trade-offs to consider
----------------------

- Simple hashing vs custom partitioning logic
- Early selection of partition key vs post-processing rekeying
- Fixed partition count vs dynamic scaling complexity
- Single-topic-per-entity vs aggregated event streams

Schema Management
-------------

Defining consistent, versioned event schemas is key to reliable and scalable stream processing.

**Why schemas matter:**

- Enforce data contracts between producers and consumers
- Validate structure before sending/processing events
- Enable safe schema evolution
- Power downstream automation (e.g., code generation, analytics models)

Formats
-------

AVRO is the recommended default format for Kafka events due to its compact binary serialization, dynamic typing, and strong support for schema evolution.

Kafka messages typically do **not embed full schema information** inside the event payload.  
Instead, a small **Schema ID** is included in the message header, allowing producers and consumers to retrieve the full schema from a centralized Schema Registry.  
This avoids payload bloat and ensures efficient serialization.

(With Confluent Schema Registry, this behavior is enabled by default: the producer serializes the message with a wire format that starts with a magic byte and a schema ID.)

Other formats to consider:

- **Protobuf**:  
  Suitable for strongly typed APIs and gRPC-based microservices.  
  Protobuf offers compact encoding and strict contracts, but requires more upfront tooling (e.g., code generation and careful field numbering).  
  Evolution rules are stricter than Avro.

- **JSON Schema**:  
  Easier to inspect manually and friendly for less technical users.  
  However, JSON payloads are larger, and schema validation is generally weaker compared to Avro and Protobuf.

**Format recommendation:**  
For internal data pipelines and analytics use cases, **Avro** is the preferred choice.  
Protobuf can be considered for service-to-service communication where strict typing across languages is critical.

Versioning Strategy
--------------------

Schemas must evolve safely without breaking producers or consumers.

**Types of changes:**

- *Non-breaking changes* (allow evolution on same topic):
  - Add optional fields with defaults
  - Add new fields with ``null`` union types
  - Expand enum values

- *Breaking changes* (require a new topic version):
  - Remove or rename fields
  - Change required field types
  - Restrict enum values

**Best practices:**

- Always aim for backward-compatible changes where possible
- For breaking changes, create a new versioned topic (e.g., ``orders.v2``)
- Version both topic names and schema files explicitly to make upgrades clear
- Enforce schema evolution rules automatically in CI/CD pipelines

Example schema structure:

.. code-block:: bash

   schemas/
     orders/
       order_created.v1.avsc
       order_created.v2.avsc

Each event payload will reference its schema indirectly via the Schema ID, not by embedding the full schema content.  
The Schema Registry resolves the Schema ID dynamically at runtime.

This design ensures efficient message size and centralized schema governance.

Event Producers
--------------

Event producers are systems that produce events into Kafka topics.

**Common emitter types:**

- Microservices publishing business events (e.g., ``UserRegistered``, ``OrderPlaced``)
- Change Data Capture (CDC) tools capturing database changes (e.g., **Debezium**)
- IoT devices emitting telemetry data
- Application logs converted to events (e.g., FluentBit, Filebeat)

**Producer architecture options:**

- Direct producers (e.g., Kafka client libraries in Java, Python, Node.js)
- Embedded producers (e.g., producer libraries embedded inside services)
- Externalized producers (e.g., CDC pipelines)

**Best practices:**

- Validate data against schema before sending
- Use consistent metadata fields (e.g., ``event_type``, ``timestamp``, ``source``)
- Configure producer retries, idempotence, and delivery guarantees

**Trade-offs to consider:**

- At-least-once vs exactly-once guarantees
- Synchronous vs asynchronous event sending
- Compression (e.g., snappy, gzip) to reduce network usage

Event Consumers
-----------

Event consumers are systems that consume Kafka events for processing or storage.

**Common sink types:**

- Object storage (e.g., S3, GCS)
- Data warehouses (e.g., Snowflake, BigQuery)
- Stream processors (e.g., Apache Flink, Faust, Spark Streaming)
- Analytics engines (e.g., Druid, ClickHouse)

**Consumer architecture options:**

- Simple consumers (read and write)
- Stateful consumers (aggregate, window, join events)
- Real-time analytics consumers (e.g., real-time dashboards)

**Best practices:**

- Handle consumer offsets carefully (commit after processing)
- Validate schema versions to avoid incompatibilities
- Ensure fault tolerance and at-least-once delivery

**Trade-offs to consider:**

- Manual vs auto offset commits
- Rebalancing cost during consumer group scaling
- Resource-heavy stateful processing vs lightweight stateless

Kafka Connect
-------------

Kafka Connect is a framework to move large amounts of data into and out of Kafka reliably.

**Use cases:**

- Capture changes from databases into Kafka
- Sink Kafka topics into external systems

**Advantages:**

- Declarative configuration (no custom code)
- Built-in fault tolerance and scaling
- Large ecosystem of source and sink connectors

**Popular connectors:**

- **Sources**: PostgreSQL, MySQL, MongoDB, Elasticsearch
- **Sinks**: S3, Snowflake, BigQuery, Elasticsearch

**Best practices:**

- Run connectors in distributed mode for production
- Monitor lag and task failures
- Isolate high-traffic connectors to dedicated worker groups if needed

**Trade-offs to consider:**

- Self-managed vs Confluent Cloud connectors
- Single vs multiple Connect clusters
- Centralized connector config vs GitOps management
