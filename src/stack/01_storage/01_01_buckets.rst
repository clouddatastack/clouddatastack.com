1.1. Buckets
====================================

Organizing your cloud storage buckets is one of the first critical steps toward building a scalable, secure, and cost-effective data platform. This guide outlines best practices around bucket structure, configuration, and lifecycle policies.

Structure
---------

Separate Production and Development Accounts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To reduce the risk of accidental data exposure or corruption, production and development environments should reside in separate cloud accounts or projects. This separation ensures:

- Strict access control
- Clear billing separation
- Easier auditing and compliance

**Example:**

- ``data-prod`` (production workloads and analytics)
- ``data-dev`` (experiments, testing, staging)

Buckets per Logical Domain
^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a separate bucket for each logical data domain in your organization. This improves data governance, cost attribution, and access control.

**Example domains:**

- ``user-profile-data``
- ``sales-data``
- ``clickstream-events``

Processing Stage Prefixes
^^^^^^^^^^^^^^^^^^^^^^^^^

Organize data inside each bucket by processing stage using structured path prefixes:

::

    domain-name/raw/
    domain-name/processed/
    domain-name/curated/

- ``raw/`` — original ingested files, unaltered
- ``processed/`` — cleaned, structured, possibly joined
- ``curated/`` — ready for consumption by analysts or ML models

This layout enables easy cleanup, partitioning, and clear lineage.

Project-Type Prefixes
^^^^^^^^^^^^^^^^^^^^^

For more granular control, introduce prefixes based on project or data format:

::

    clickstream-json/
    event-log-csv/
    user-profile-parquet/

This allows you to apply specific processing rules or lifecycle policies to different data formats or sources.

Configuration
-------------

Enable Versioning
^^^^^^^^^^^^^^^^^

Versioning tracks all versions of an object, allowing for recovery from accidental deletes or overwrites.

**Pros:**

- Accidental overwrite protection
- Required for rollback in raw zones

**Considerations:**

- Can increase storage costs significantly if not paired with lifecycle cleanup

**Terraform example:**

.. code-block:: hcl

    versioning {
      enabled = true
    }

Block Public Access
^^^^^^^^^^^^^^^^^^^

Always block public access unless there's a deliberate use case (e.g., public datasets).

- Prevents accidental exposure
- Compliant with GDPR and enterprise policies

Enable Server-Side Encryption
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use encryption to protect data at rest. Options include:

- **SSE-S3** (default, managed by AWS)
- **SSE-KMS** (uses customer-managed keys for finer access control)

.. code-block:: hcl

    rule {
        apply_server_side_encryption_by_default {
            sse_algorithm = "AES256"
        }
    }

Lifecycle Rules and Archiving
-----------------------------

Expire Raw Data
^^^^^^^^^^^^^^^

Raw data is often large and infrequently accessed. It may also contain **sensitive or personally identifiable information (PII)** that has not yet been masked, anonymized, or validated. 

It is recommended to configure lifecycle policies that expire raw data after a defined period, such as 30 or 90 days.

**Terraform example:**

.. code-block:: hcl

    rule {
      id     = "expire-raw"
      prefix = "nyc-taxi/raw/"
      enabled = true

      expiration {
        days = 90
      }
    }

Archive Processed Data
^^^^^^^^^^^^^^^^^^^^^^

Processed data is accessed occasionally but still valuable. Configure a transition rule to move it to cold storage (e.g., S3 Glacier) after a retention period.

**Terraform example:**

.. code-block:: hcl

    rule {
      id     = "archive-processed"
      prefix = "nyc-taxi/processed/"
      enabled = true

      transition {
        days          = 180
        storage_class = "GLACIER"
      }
    }

Example: Provisioning a Bucket for NYC Taxi Dataset
---------------------------------------------------

To reuse the Terraform module from GitHub:

.. code-block:: hcl

    module "nyc_taxi_data_bucket" {
      source  = "git::https://github.com/clouddatastack/terraform-aws-s3-data-bucket.git?ref=v1.0.0"

      bucket_name       = "mycompany-nyc-taxi-data"
      force_destroy     = true      # Allow deletion in the example even if bucket contains files
      enable_versioning = true

      lifecycle_rules = [
        {
          id              = "expire-raw"
          prefix          = "nyc-taxi/raw/"
          expiration_days = 90
        },
        {
          id                       = "archive-processed"
          prefix                   = "nyc-taxi/processed/"
          transition_days          = 180
          transition_storage_class = "GLACIER"
        }
      ]

      tags = {
        project = "nyc-taxi"
        env     = "prod"
      }
    }

You can find the full module code and latest versions at:
`GitHub - terraform-aws-s3-data-bucket <https://github.com/clouddatastack/terraform-aws-s3-data-bucket>`_

Use the `ref=v1.0.0` query to lock the module version.
