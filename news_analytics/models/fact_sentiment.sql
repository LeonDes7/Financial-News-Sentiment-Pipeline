{{ config(materialized='table') }}

SELECT
    article_id,
    sentiment_score,
    published_timestamp,
    
    
    CASE
        WHEN sentiment_score > 0.05 THEN 'Positive'
        WHEN sentiment_score < -0.05 THEN 'Negative'
        ELSE 'Neutral'
    END AS sentiment_category

FROM {{ ref('stg_news') }}