7.3. GDPR Compliance with dbt
=============================

Overview
--------

This guide shows a portable approach to marking dbt models and columns as GDPR-relevant and applying tags at the warehouse level automatically. The pattern uses dbt ``meta`` on models/columns plus a simple post-hook macro that runs ``ALTER TABLE/ALTER COLUMN`` statements. Adjust SQL syntax to match your warehouse (Databricks Unity Catalog, Snowflake, BigQuery, etc.).

What you implement
------------------

- A model-level opt-in flag to mark a table as GDPR-relevant.
- Optional column-level tags for sensitive fields (for example, user identifiers).
- A post-hook macro that sets/unsets warehouse tags based on ``meta``.

Setup
-----

1. Add macros to your project (example files in this repository):

    .. literalinclude:: code/macros/set_gdpr_compliance_tag.sql
        :language: jinja
        :caption: Macro: set_gdpr_compliance_tag

2. In your dbt model YAML, annotate tables/columns via ``meta``:

	.. literalinclude:: code/examples/schema_gdpr_and_retention.yml
		:language: yaml
		:lines: 1-25
		:caption: Example model YAML with GDPR meta

3. Configure a post-hook on the models where you want the macro to run. You can set this at the folder level (``models:`` in ``dbt_project.yml``) or per-model using ``config(post_hook=...)``.

Usage
-----

- Model-level: set ``meta: { is_gdpr_model: true }``. The macro will set a table tag ``gdpr_deletion=enabled``.
- Column-level: either set ``meta: { is_gdpr_column: true }`` to mark a field as sensitive with default type ``user_identifier``, or provide an explicit type via ``meta: { gdpr_column_type: <type> }``.
- The macro also unsets ``gdpr_column_type`` on columns that aren't flagged, keeping tags consistent when schemas evolve.

Warehouse syntax notes
----------------------

- Databricks/Unity Catalog: uses ``ALTER TABLE <table> SET TAGS (...)`` and ``ALTER COLUMN ... SET TAGS (...)``.
- Snowflake: use ``ALTER TABLE <table> SET TAG <name> = '<value>'``; adjust the macro accordingly.
- BigQuery: consider labels or policy tags via separate APIs; the post-hook may call an external procedure instead of SQL.

Example: end-to-end
-------------------

1. Add meta in YAML for your model and columns.
2. Ensure the macro is available and included in the models' post-hooks.
3. Run your model; dbt will execute the post-hook and apply tags to the relation and columns.

Reference implementation
------------------------

.. literalinclude:: code/macros/set_gdpr_compliance_tag.sql
	:language: jinja
	:caption: set_gdpr_compliance_tag macro (full)

.. literalinclude:: code/examples/schema_gdpr_and_retention.yml
	:language: yaml
	:lines: 1-25
	:caption: YAML meta example for GDPR

Operational tips
----------------

- Run this macro via post-hooks to keep tags aligned with each run, especially after schema changes.
- Use explicit types like ``user_identifier``, ``pii_email``, or ``business_identifier`` to categorize sensitivity.
- Keep the tagging macro idempotent and safe for reruns; the provided implementation sets or unsets tags based on current ``meta``.

