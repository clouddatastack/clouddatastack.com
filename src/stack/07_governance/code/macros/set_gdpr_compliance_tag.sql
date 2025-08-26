-- Generic GDPR tagging macro for dbt
-- Notes:
-- - Example SQL below uses Databricks/Unity Catalog syntax for tags.
-- - If your warehouse uses a different syntax (e.g., Snowflake), adjust the ALTER statements accordingly.

{% macro set_gdpr_compliance_tag() %}
    {% if execute %}
        {# Table-level meta flag to opt-in the model for GDPR tagging #}
        {% set is_gdpr_model = model.meta.get('is_gdpr_model') %}

        {% if is_gdpr_model %}
            {# Table-level tag #}
            {% set table_tag_name = 'gdpr_deletion' %}
            {% set table_tag_value = 'enabled' %}

            {% set table_level_tag_sql %}
                ALTER TABLE {{ this }} SET TAGS ('{{ table_tag_name }}' = '{{ table_tag_value }}');
            {% endset %}
            {% do run_query(table_level_tag_sql) %}

            {# Column-level tags: set gdpr_column_type when provided #}
            {% set column_tag_name = 'gdpr_column_type' %}
            {% for column in model.columns %}
                {% set col_meta = model.columns.get(column).meta or {} %}

                {# Support either a boolean flag or explicit type string #}
                {% set explicit_type = col_meta.get('gdpr_column_type') %}
                {% set is_flagged = col_meta.get('is_gdpr_column') %}

                {% if explicit_type is string and explicit_type|length > 0 %}
                    {% set column_level_tag_sql %}
                        ALTER TABLE {{ this }}
                        ALTER COLUMN {{ column }} SET TAGS ('{{ column_tag_name }}' = '{{ explicit_type }}');
                    {% endset %}
                    {% do run_query(column_level_tag_sql) %}
                {% elif is_flagged %}
                    {% set column_level_tag_sql_default %}
                        ALTER TABLE {{ this }}
                        ALTER COLUMN {{ column }} SET TAGS ('{{ column_tag_name }}' = 'user_identifier');
                    {% endset %}
                    {% do run_query(column_level_tag_sql_default) %}
                {% else %}
                    {% set column_level_untag_sql %}
                        ALTER TABLE {{ this }}
                        ALTER COLUMN {{ column }} UNSET TAGS ('{{ column_tag_name }}');
                    {% endset %}
                    {% do run_query(column_level_untag_sql) %}
                {% endif %}
            {% endfor %}
        {% endif %}
    {% endif %}
{% endmacro %}
