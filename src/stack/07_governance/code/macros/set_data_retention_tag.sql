-- Generic data retention tagging macro for dbt
-- Applies a table tag `retention` with value determined by model meta or default policy.
-- Adjust ALTER syntax to your target warehouse if needed.

{% macro set_data_retention_tag() %}
    {% if execute %}
        {# Read optional model-level override, e.g. meta: { retention: "90d" | "2y" | "permanent" } #}
        {% set retention_meta = model.meta.get('retention') %}

        {# Simple defaults by schema name; adapt to your environment/policies #}
        {% set schema_lower = this.schema | lower %}
        {% if schema_lower == 'stage' %}
            {% set default_retention = '2y' %}
        {% elif schema_lower == 'core' %}
            {% set default_retention = '3y' %}
        {% elif schema_lower == 'report' %}
            {% set default_retention = '5y' %}
        {% else %}
            {% set default_retention = 'permanent' %}
        {% endif %}

        {% if retention_meta is string and retention_meta|length > 0 %}
            {% set tag_value = retention_meta %}
        {% else %}
            {% set tag_value = default_retention %}
        {% endif %}

        {% set tag_sql %}
            ALTER TABLE {{ this }} SET TAGS ('retention' = '{{ tag_value }}');
        {% endset %}
        {% do run_query(tag_sql) %}
    {% endif %}
{% endmacro %}
