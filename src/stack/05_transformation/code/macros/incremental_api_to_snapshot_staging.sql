{% macro incremental_api_to_snapshot_staging(source_relation) %}

{% if is_incremental() %}
    -- Incremental logic: Combine today's data with unchanged records from yesterday's snapshot.

    -- 1. Select all records from the latest incremental load (today's data).
    with current_increment as (
        select *
        from {{ source_relation }}
        where event_date = {{ var('event_date') }}
    ),

    -- 2. Select records from the previous day's snapshot that haven't been updated today.
    --    This carries forward the state of unchanged records.
    previous_snapshot_unchanged as (
        select *
        from (
            {% if adapter.get_relation(this.database, this.schema, this.identifier) %}
                select * except(event_date),
                       {{ var('event_date') }} as event_date
                from {{ this }}
                where event_date = {{ date_add(var('event_date'), -1, 'day') }}
                  and record_id not in (
                    select record_id
                    from current_increment
                )
            {% else %}
                -- If the target model doesn't exist yet, return an empty set with the correct schema.
                select *
                from {{ source_relation }}
                where 1=0
            {% endif %}
        )
    )

    -- 3. Union the new/updated records with the unchanged records from the previous snapshot.
    select * from current_increment
    union all
    select * from previous_snapshot_unchanged

{% else %}
    -- Full refresh logic: Build the snapshot from the entire history.

    -- 1. Select the most recent version of each record based on the event_date.
    with latest_records as (
        select *,
               row_number() over (partition by record_id order by event_date desc) as rn
        from {{ source_relation }}
        where event_date <= {{ var('event_date') }}
    )

    -- 2. Select only the latest version (rn=1) and set the event_date to the processing date.
    select * except(event_date, rn),
           {{ var('event_date') }} as event_date
    from latest_records
    where rn = 1

{% endif %}

{% endmacro %}
