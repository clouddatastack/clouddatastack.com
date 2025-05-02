2.1. Streaming Infrastructure
=============================

Real-time data pipelines rely on robust streaming infrastructure.  
This page outlines the building blocks of a modern streaming system, including stream design, schema management, event producers and consumers, and integration with Kafka Connect.

**Relevant repositories:**

- `Terraform AWS EKS <https://github.com/clouddatastack/terraform-aws-eks>`_
- `Streaming Kafka Cluster <https://github.com/clouddatastack/streaming-kafka-cluster>`_
- `Streaming Kafka Schemas <https://github.com/clouddatastack/streaming-kafka-schemas>`_
- `Streaming Kafka Producer <https://github.com/clouddatastack/streaming-kafka-producer>`_
- `Streaming Kafka Consumer <https://github.com/clouddatastack/streaming-kafka-consumer>`_


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

**Relevant repository:**

- `Terraform AWS EKS <https://github.com/clouddatastack/terraform-aws-eks>`_
- `Streaming Kafka Cluster <https://github.com/clouddatastack/streaming-kafka-cluster>`_

**Best practices for topic design:**

- Use domain-based topic names: ``ecommerce.orders.created``
- Prefer one event type per topic unless there's a strong operational reason to combine.
- Version topics if breaking schema changes are expected (e.g., ``orders.v2``).
- Avoid topics that mix unrelated domains or concerns.

Partitioning Guidelines
-----------------------

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
High cardinality helps avoid "hot" partitions and enables parallel processing.

*Example (using ``session_id`` to spread load):*

.. code-block:: python

   key = record["session_id"].encode("utf-8")
   producer.send("clickstream", key=key, value=record)

**Plan partition count carefully** at topic creation.  
Partitioning affects both throughput and scalability.  
Reassigning partitions later is possible but operationally complex.

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
- **Increase partition count**: Add partitions when consumer parallelism needs to scale, but monitor distribution closely.

Trade-offs to Consider
----------------------

- Simple hashing vs custom partitioning logic.
- Early selection of partition key vs rekeying later.
- Fixed partition count vs operational complexity when scaling.
- Single-event-type topics vs aggregated topics (event grouping).

Schema Management
-----------------

Defining consistent, versioned event schemas is critical for reliable and scalable stream processing.

**Relevant repository:**

- `Streaming Kafka Schemas <https://github.com/clouddatastack/streaming-kafka-schemas>`_

**Why schemas matter:**

- Enforce data contracts between producers and consumers.
- Validate event structure at runtime.
- Enable safe schema evolution.
- Power downstream automation (e.g., code generation, analytics models).

Formats
-------

AVRO is the recommended default format for Kafka events due to its compact serialization, dynamic typing, and strong support for schema evolution.

Kafka messages typically do **not embed full schema definitions** inside the payload.  
Instead, a small **Schema ID** is included in the message, allowing producers and consumers to resolve the full schema from a centralized Schema Registry.

(Confluent Schema Registry handles Schema ID registration and lookup automatically when using official Kafka serializers.)

Other formats to consider:

- **Protobuf**:  
  Suitable for strongly typed APIs and gRPC-based microservices.  
  Offers compact encoding but requires careful code generation and stricter evolution management compared to Avro.

- **JSON Schema**:  
  Human-readable and easier for manual inspection, but results in larger payloads and weaker typing guarantees.

**Format recommendation:**  
For internal event-driven pipelines and analytics, **Avro** is the preferred choice.  
Protobuf may be preferred for cross-service APIs requiring strong language bindings.

Versioning Strategy
--------------------

Schemas must evolve safely without breaking producers or consumers.

**Types of schema changes:**

- *Non-breaking changes* (allowed on the same topic):
  - Add optional fields with defaults.
  - Add new fields with ``null`` union types.
  - Expand enum values.

- *Breaking changes* (require a new topic version):
  - Remove or rename fields.
  - Change required field types.
  - Restrict enum values.

**Best practices:**

- Favor backward-compatible changes.
- For breaking changes, create a new versioned topic (e.g., ``orders.v2``).
- Version both topic names and schema files explicitly.
- Validate schemas during pull requests using CI/CD pipelines.

Example schema structure:

.. code-block:: bash

   schemas/
     orders/
       order_created.v1.avsc
       order_created.v2.avsc

Each event references its schema indirectly through the Schema ID, ensuring minimal payload size and centralized governance.

Event Producers
---------------

Producers are systems that publish events into Kafka topics.

**Relevant repository:**

- `Streaming Kafka Producer <https://github.com/clouddatastack/streaming-kafka-producer>`_

**Common producer types:**

- Microservices emitting business events (e.g., ``UserRegistered``, ``OrderPlaced``).
- Change Data Capture (CDC) tools capturing database changes (e.g., **Debezium**).
- IoT devices sending telemetry data.
- Log shippers (e.g., FluentBit, Filebeat).

Producer Strategy for Exactly-Once Guarantees
---------------------------------------------

When a producer is only writing to Kafka (without consuming from Kafka),  
exactly-once delivery can be achieved by configuring the Kafka producer for **idempotent writes**.

**Key configurations:**

- ``enable.idempotence=true``:  
  Ensures that retries of a produce request will not result in duplicate records.

- ``acks=all``:  
  Waits for all in-sync replicas to acknowledge the write, ensuring durability and consistency.

- ``retries=Integer.MAX_VALUE`` (or a very high number):  
  Automatically retries transient failures without risking duplicates.

With these settings, Kafka will automatically deduplicate retried messages at the broker side, achieving exactly-once semantics for event production.

**Example: Configuring a Kafka producer with exactly-once guarantees (Python)**

.. code-block:: python

   # Create Kafka producer with exactly-once settings
   producer = KafkaProducer(
       bootstrap_servers="localhost:9092",
       enable_idempotence=True,    # Critical for exactly-once
       acks="all",                  # Ensure full replication
       retries=2147483647           # Retry infinitely
   )

   # Example event
   event = {
       "event_type": "UserRegistered",
       "user_id": "1234",
       "timestamp": "2025-04-28T12:34:56Z"
   }

   # Serialize and send
   producer.send(
       topic="user-registrations",
       key=event["user_id"].encode("utf-8"),
       value=json.dumps(event).encode("utf-8")
   )

   producer.flush()

Best Practices
--------------

- Always enable idempotence on all production Kafka producers.
- Ensure producer retries are configured correctly to avoid message loss during transient failures.
- Validate event payloads against schemas at the producer side before sending.
- Use stable, meaningful keys for partitioning to ensure proper event ordering if required.

Event Consumers
---------------

Consumers subscribe to Kafka topics and process incoming events.

**Relevant repository:**

- `Streaming Kafka Consumer <https://github.com/clouddatastack/streaming-kafka-consumer>`_

**Best practices:**

- Validate incoming event schemas to ensure compatibility with expected structures.
- Manage consumer offsets manually:
  - Only commit offsets after successful event processing.
  - Avoid premature commits to ensure reliability.

- Build for exactly-once delivery guarantees:

Exactly-once processing ensures that every event is processed exactly once — no duplicates, no data loss.
Two practical patterns enable exactly-once guarantees:

**1. Kafka Transactions (manual, per event batch):**

Use a transactional Kafka producer that sends output messages and commits consumer offsets atomically within a single transaction.

Example (Python with KafkaProducer):

.. code-block:: python

   from kafka import KafkaProducer, KafkaConsumer
   from kafka.structs import TopicPartition

   producer = KafkaProducer(
       bootstrap_servers="localhost:9092",
       transactional_id="producer-1",
       enable_idempotence=True
   )
   producer.init_transactions()

   consumer = KafkaConsumer(
       "input-topic",
       group_id="consumer-group-1",
       bootstrap_servers="localhost:9092",
       enable_auto_commit=False,  # manual offset commits
       isolation_level="read_committed"  # only consume committed messages
   )

   for message in consumer:
       try:
           producer.begin_transaction()

           # Process the event
           output_record = process_event(message.value)

           # Produce to output topic
           producer.send("output-topic", value=output_record)

           # Commit consumed offset inside the transaction
           producer.send_offsets_to_transaction(
               {TopicPartition(message.topic, message.partition): message.offset + 1},
               consumer_group_id="consumer-group-1"
           )

           producer.commit_transaction()

       except Exception as e:
           producer.abort_transaction()
           handle_processing_error(e)

This pattern guarantees that event processing, output production, and offset commits are atomic.

**2. Stateful Stream Processors (automatic checkpointing):**

Apache Flink manages both the event processing state and Kafka consumer offsets atomically.  
It uses periodic checkpointing to capture a consistent snapshot of the system state,  
enabling automatic recovery and exactly-once processing guarantees without manual transaction handling.

Example:

.. code-block:: java

   StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

   env.enableCheckpointing(60000); // checkpoint every 60 seconds
   env.getCheckpointConfig().setCheckpointingMode(CheckpointingMode.EXACTLY_ONCE);

   FlinkKafkaConsumer<String> source = new FlinkKafkaConsumer<>(
       "input-topic",
       new SimpleStringSchema(),
       kafkaProperties
   );

   FlinkKafkaProducer<String> sink = new FlinkKafkaProducer<>(
       "output-topic",
       new SimpleStringSchema(),
       kafkaProperties,
       FlinkKafkaProducer.Semantic.EXACTLY_ONCE
   );

   env.addSource(source)
      .map(record -> transform(record))
      .addSink(sink);

Trade-offs to consider
----------------------

- Kafka transactions add some latency but are flexible for simple pipelines.
- Stateful processors like Flink offer high-level exactly-once guarantees but require stream processing infrastructure.
- If exactly-once complexity is too high, fallback to at-least-once processing combined with idempotent operations to tolerate occasional duplicates.

Kafka Connect
-------------

Kafka Connect simplifies integrating Kafka with external systems without writing custom code.

**Typical use cases:**

- Capture changes from databases into Kafka (source connectors).
- Sink Kafka topics into object storage, data warehouses, or search engines (sink connectors).

**Advantages:**

- Declarative configuration (JSON/YAML based).
- Built-in scalability, fault tolerance, and distributed deployments.
- Extensive ecosystem of pre-built connectors.

.. raw:: html

   <script>
   var links = document.querySelectorAll('a[href^="http"]');
   links.forEach(function(link) {
       link.setAttribute('target', '_blank');
   });
   </script>