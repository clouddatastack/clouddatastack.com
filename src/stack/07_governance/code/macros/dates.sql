-- Small helpers to make examples portable across warehouses

{% macro event_date() %}
    {{ var('event_date', 'CURRENT_DATE()') }}
{% endmacro %}

{% macro current_date() %}
    CURRENT_DATE()
{% endmacro %}
