4.1. Queries Federation with Apache Trino
=========================================

Introduction
-------------
Apache Trino is a distributed SQL query engine designed to query large datasets across multiple data sources. This section explores how to set up and use Trino for query federation, enabling seamless data access and analytics.

Key Features
-------------
- **Federated Queries**: Combine data from multiple sources, such as relational databases, object storage, and NoSQL systems.
- **High Performance**: Optimized for low-latency and high-throughput queries.
- **Scalability**: Supports scaling to thousands of nodes for large-scale analytics.

Setup and Configuration
------------------------

1. **AWS Setup**:

   **Provision an EC2 Instance**:
   
   - Launch an EC2 instance with a Linux AMI (e.g., Amazon Linux 2).
   - Ensure the instance has sufficient resources (e.g., 4 vCPUs, 16 GB RAM) for Trino.
   - Install Java and Trino on the instance:

     ```bash
     sudo yum update -y
     sudo yum install java-11-amazon-corretto -y
     wget https://repo1.maven.org/maven2/io/trino/trino-server/403/trino-server-403.tar.gz
     tar -xvzf trino-server-403.tar.gz
     cd trino-server-403
     mkdir etc
     ```

   **Configure Trino**:
   - Create a `config.properties` file in the `etc` directory to define Trino's coordinator and discovery settings:

     ```properties
     coordinator=true
     node-scheduler.include-coordinator=true
     http-server.http.port=8080
     query.max-memory=5GB
     query.max-memory-per-node=1GB
     discovery-server.enabled=true
     discovery.uri=http://localhost:8080
     ```

   - Create a `node.properties` file to specify node-specific configurations:

     ```properties
     node.environment=production
     node.id=unique-node-id
     node.data-dir=/var/trino/data
     ```

   - Start Trino using the launcher script:

     ```bash
     bin/launcher start
     ```

   **Configure AWS S3 Connector**:
   - Add an S3 catalog in the `etc/catalog` directory (e.g., `s3.properties`) to enable querying data stored in S3:

     ```properties
     connector.name=hive
     hive.metastore=glue
     hive.s3.aws-access-key=YOUR_ACCESS_KEY
     hive.s3.aws-secret-key=YOUR_SECRET_KEY
     hive.s3.bucket=your-bucket-name
     ```

   - Use AWS Glue as the metastore for managing table schemas.

2. **Kubernetes Setup**:

   **Deploy Trino on Kubernetes**:
   - Create a Kubernetes deployment YAML file to define the Trino pods:

     .. code-block:: yaml

        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: trino
        spec:
            replicas: 3
            selector:
                matchLabels:
                    app: trino
            template:
                metadata:
                    labels:
                        app: trino
                spec:
                    containers:
                    - name: trino
                      image: trinodb/trino:latest
                      ports:
                      - containerPort: 8080
                      volumeMounts:
                      - name: config-volume
                        mountPath: /etc/trino
                    volumes:
                    - name: config-volume
                      configMap:
                          name: trino-config

   - Create a ConfigMap for Trino configuration to manage settings centrally:

     .. code-block:: yaml

        apiVersion: v1
        kind: ConfigMap
        metadata:
          name: trino-config
        data:
          config.properties: |
            coordinator=true
            node-scheduler.include-coordinator=true
            http-server.http.port=8080
            query.max-memory=5GB
            query.max-memory-per-node=1GB
            discovery-server.enabled=true
            discovery.uri=http://localhost:8080
          node.properties: |
            node.environment=production
            node.id=unique-node-id
            node.data-dir=/var/trino/data

   - Apply the configurations using `kubectl`:

     .. code-block:: bash

        kubectl apply -f trino-deployment.yaml
        kubectl apply -f trino-config.yaml

   **Expose Trino Service**:
   - Create a service YAML file to expose Trino to external clients:

     .. code-block:: yaml

        apiVersion: v1
        kind: Service
        metadata:
          name: trino-service
        spec:
            selector:
                app: trino
            ports:
            - protocol: TCP
              port: 8080
              targetPort: 8080
            type: LoadBalancer

   - Apply the service configuration:

     .. code-block:: bash

        kubectl apply -f trino-service.yaml

Best Practices
---------------

- **Resource Allocation**:
  - Allocate sufficient memory and CPU resources for Trino nodes to handle query workloads efficiently.
  - Use Kubernetes auto-scaling to dynamically adjust resources based on demand.

- **Security**:
  - Use IAM roles for AWS S3 access to avoid hardcoding credentials in configuration files.
  - Enable HTTPS for secure communication between Trino nodes and clients.
  - Restrict access to Trino's HTTP port using security groups or network policies.

- **Monitoring and Logging**:
  - Integrate Trino with Prometheus and Grafana for real-time monitoring of query performance and resource usage.
  - Enable detailed logging to troubleshoot query issues and optimize performance.

- **Data Partitioning**:
  - Partition large datasets by frequently queried columns (e.g., date, region) to improve query performance.
  - Use appropriate partitioning strategies based on query patterns and data distribution.

- **Query Optimization**:
  - Use filters and projections early in queries to reduce the amount of data processed.
  - Avoid cross-joins and use indexed columns for join conditions.

Use Cases
---------

1. **Data Lake Analytics**:

   - **Configuration**:
  - Set up an S3 catalog as described in the AWS setup to query data stored in S3.

- **Code Example**:

  ```sql
  SELECT region, COUNT(*)
  FROM s3.sales_data
  WHERE year = 2025
  GROUP BY region;
  ```

  This query counts the number of sales records for each region in the year 2025.

2. **Cross-Database Joins**:

   - **Configuration**:
  - Set up catalogs for MySQL and PostgreSQL to enable cross-database queries:

    .. code-block:: properties

       # MySQL catalog (mysql.properties)
       connector.name=mysql
       connection-url=jdbc:mysql://mysql-host:3306
       connection-user=root
       connection-password=secret

       # PostgreSQL catalog (postgresql.properties)
       connector.name=postgresql
       connection-url=jdbc:postgresql://postgres-host:5432
       connection-user=admin
       connection-password=secret

- **Code Example**:

  ```sql
  SELECT a.user_id, b.order_id
  FROM mysql.users a
  JOIN postgresql.orders b
  ON a.user_id = b.user_id;
  ```

  This query joins user data from MySQL with order data from PostgreSQL based on the `user_id` column.

3. **Ad-Hoc Analysis**:

   - **Configuration**:
  - Use Trino CLI or connect a BI tool like Tableau to Trino for interactive analysis.

- **Code Example**:

  ```sql
  SELECT product_id, AVG(sales)
  FROM s3.sales_data
  WHERE category = 'electronics'
  GROUP BY product_id;
  ```

  This query calculates the average sales for each product in the "electronics" category.


