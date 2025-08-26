7.4. Data Retention
===================

Overview
--------

This article outlines a practical way to track and enforce data retention in a dbt project. It uses model ``meta`` to declare intended retention (for example, ``90d``, ``2y``, ``permanent``), a post-hook macro to stamp warehouse-level tags, and an optional housekeeping macro to delete old rows by date.

What you implement
------------------

- A macro to set a table tag ``retention=<value>`` based on model ``meta`` or schema defaults.
- A simple housekeeping macro ``data_retention(days_to_keep, date_col)`` that deletes rows older than N days.
- YAML examples showing how to declare retention in model ``meta``.

Setup
-----

1. Add the macros to your project:

    .. literalinclude:: code/macros/set_data_retention_tag.sql
        :language: jinja
        :caption: Macro: set_data_retention_tag

    .. literalinclude:: code/macros/data_retention.sql
        :language: jinja
        :caption: Macro: data_retention

    .. literalinclude:: code/macros/dates.sql
        :language: jinja
        :caption: Helper macros for dates

2. Declare retention in your model YAML where needed:

	.. literalinclude:: code/examples/schema_gdpr_and_retention.yml
		:language: yaml
		:caption: Example YAML with model-level retention

3. Add post-hooks so the tag macro runs for the relevant models. You can set this at the ``dbt_project.yml`` folder level or per model via ``config(post_hook=...)``.

Example: incremental model with retention
The snippet below shows an incremental model using ``replace_where`` and a ``post_hook`` to delete rows older than 90 days:

.. literalinclude:: code/examples/model_with_retention.sql
	:language: jinja
	:caption: Incremental model using data_retention

Behavior and policy notes
-------------------------

- The tag macro does not enforce deletion by itself; it documents intent at the table level for governance and discovery.
- The housekeeping macro issues a ``DELETE`` based on a date column and the current date helpers. Adjust for your warehouse functions if needed.
- Choose safe execution patterns: for large tables, prefer partition filters and limit delete frequency to off-peak hours.
- Defaults by schema are just examples; adapt them to your organization's policies.

