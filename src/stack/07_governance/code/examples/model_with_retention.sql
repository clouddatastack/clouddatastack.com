{{
    config(
        materialized='incremental',
        on_schema_change='append_new_columns',
        incremental_strategy='replace_where',
        incremental_predicates = "event_date = " ~ event_date(),
        post_hook = "{{ data_retention(90, 'event_date') }}"
    )
}}

select
  user_id,
  session_id,
  event_date,
  event_type
from {{ ref('user_events_monthly_source') }}
{% if is_incremental() %}
where event_date = {{ event_date() }}
{% endif %}
