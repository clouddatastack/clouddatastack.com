{% macro databricks__get_incremental_replace_where_sql(arg_dict) %}
    {#
      This is the definitive override for the `replace_where` strategy.
      It fixes the column-order problem by using the `SELECT` form of the
      `INSERT ... REPLACE WHERE` command, which allows us to explicitly
      order the columns to match the target table.
    #}
    {%- set target_relation = arg_dict['target_relation'] -%}
    {%- set temp_relation = arg_dict['temp_relation'] -%}
    {%- set predicates = arg_dict['incremental_predicates'] -%}

    {# Get the ordered list of columns from the target table #}
    {%- set dest_columns = adapter.get_columns_in_relation(target_relation) -%}
    {%- set dest_cols_csv = dest_columns | map(attribute='name') | join(', ') -%}

    INSERT INTO {{ target_relation }}
    REPLACE WHERE
        {# This robust logic handles both string and list predicates #}
        {% if predicates is sequence and predicates is not string %}
            {{ predicates | join(' AND ') }}
        {% else %}
            {{ predicates }}
        {% endif %}
    -- Use a SELECT instead of original 'TABLE {{ temp_relation.render() }}'
    SELECT {{ dest_cols_csv }} FROM {{ temp_relation.render() }}

{% endmacro %} 