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

Buckets per Logical Domain and Processing Stage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a separate bucket for each logical data domain in your organization, and consider using **dedicated buckets for each processing stage**: raw, processed, and curated. This improves access control, lifecycle management, and clarity in data ownership.

**Example structure:**

- ``domain_name-raw``: incoming raw JSON payloads
- ``domain_name-processed``: cleaned and structured Parquet
- ``domain_name-curated``: aggregated tables for analytics

This structure also allows you to apply bucket-level settings — like versioning, encryption, and cleanup rules — specific to the processing stage.

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

S3 bucket versioning tracks all versions of an object, allowing recovery from accidental deletes or overwrites.

**Best practice:**

- **Enable versioning** for buckets that store **raw, unprocessed files**, which may be overwritten or accidentally deleted.
- **Disable versioning** for **processed** or **curated** zones that use formats like **Delta Lake**, which handles versioning internally.

Delta Lake maintains its own version history via transaction logs and does not benefit from S3-level versioning — enabling both can lead to higher storage costs and management complexity.

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

**Terraform example:**

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

To reduce storage cost and meet compliance requirements (such as GDPR's data minimization principle), configure lifecycle rules that automatically expire raw data after a defined retention period (e.g., 30 to 90 days).

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
      force_destroy     = true      # Allow deletion for this example even if bucket contains files
      enable_versioning = true      # Enable for raw zone only

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