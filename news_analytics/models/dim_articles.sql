{{ config(materialized='table') }}

SELECT
    article_id,
    article_headline
FROM {{ ref('stg_news') }}