import streamlit as st
import pandas as pd
import psycopg2
import os
import time 
from dotenv import load_dotenv

load_dotenv()

# Layout Configuration Optimization
st.set_page_config(page_title="Financial News Sentiment", layout="wide")
st.title("Real-Time Financial News Sentiment")
st.markdown("Live dashboard powered by **Kafka, Apache Airflow, dbt, and PostgreSQL**.")

@st.cache_resource
def init_connection():
    """
    Connection Pooling Simulation: Utilizes Streamlit's caching mechanism to maintain
    and reuse a persistent database TCP connection instead of instantiating connections on every rerun.
    """
    return psycopg2.connect(
        host="localhost",
        port="5433",
        database=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD')
    )

conn = init_connection()

def load_data():
    """Analytical Extraction Query: Pulls, formats, and transforms row metrics directly inside the warehouse engine."""
    query = """
    SELECT 
        headline as article_headline,
        sentiment_score,
        CASE 
            WHEN sentiment_score > 0 THEN 'Positive'
            WHEN sentiment_score < 0 THEN 'Negative'
            ELSE 'Neutral'
        END as sentiment_category,
        to_timestamp(event_timestamp) as published_at -- In-flight transformation of unix epochs to readable timestamp fields
    FROM news_sentiment
    ORDER BY event_timestamp DESC
    LIMIT 1000; -- Performance Protection: Caps read window payload size to conserve web interface resources
    """
    # Parse query result directly into a standard pandas DataFrame data asset
    return pd.read_sql(query, conn)

df = load_data()

# Conditional Ingestion Check: Provides defensive alerting context if the database layer is currently dry
if df.empty:
    st.warning("No data found. Make sure your pipeline and Kafka consumer are running!")
else:
    st.subheader("Live Pipeline Metrics")
    col1, col2, col3 = st.columns(3)
    
    # Real-Time Visual Aggregation Metrics Calculations
    col1.metric("Total Articles Analyzed", len(df))
    col2.metric("Average Sentiment Score", round(df['sentiment_score'].mean(), 3))
    
    pos_count = len(df[df['sentiment_category'] == 'Positive'])
    col3.metric("Positive Articles", pos_count)

    st.divider()

    chart_col, data_col = st.columns([1, 2])

    with chart_col:
        st.subheader("Sentiment Distribution")
        category_counts = df['sentiment_category'].value_counts()
        st.bar_chart(category_counts, color="#1f77b4")

    with data_col:
        st.subheader("Latest Processed News")
        # Renders presentation data block with structural interface parameters (removes explicit index arrays)
        st.dataframe(
            df[['published_at', 'sentiment_category', 'sentiment_score', 'article_headline']], 
            use_container_width=True,
            hide_index=True
        )

# Web Sockets Emulation Protocol: Forces the execution frame to halt for 3 seconds 
# before re-executing the code workspace, achieving automated, looping data refreshes.
time.sleep(3)
st.rerun()