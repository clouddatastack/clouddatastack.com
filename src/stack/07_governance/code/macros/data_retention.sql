-- Housekeeping macro to delete rows older than N days
-- Usage: post_hook = "{{ data_retention(90, 'event_date') }}"

{% macro data_retention(days_to_keep=365, date_col='event_date') %}
    DELETE FROM {{ this }}
    WHERE {{ date_col }} < DATE_ADD({{ event_date() }}, -{{ days_to_keep }})
      AND {{ event_date() }} <= {{ current_date() }}
{% endmacro %}
