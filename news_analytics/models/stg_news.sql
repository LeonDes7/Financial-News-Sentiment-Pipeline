{{ config(materialized='view') }}

WITH raw_news AS (
    SELECT * FROM {{ source('raw_data', 'news_sentiment') }}
)

SELECT
    CAST(article_id AS VARCHAR) AS article_id,
    
    TRIM(headline) AS article_headline,
    
    CAST(sentiment_score AS FLOAT) AS sentiment_score,
    
    event_timestamp AS published_timestamp

FROM raw_news