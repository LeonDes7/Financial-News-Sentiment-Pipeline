import os
import json
import time 
import psycopg2
from confluent_kafka import Consumer
from textblob import TextBlob
from dotenv import load_dotenv

load_dotenv()

# Consumer Group Configuration Parameters
kafka_config = {
    'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'), 
    'group.id': 'sentiment-analysis-group', # Coordinates offset distribution across multiple scale-out consumers
    'auto.offset.reset': 'earliest'          # Fault Tolerance: Automatically replays unread messages upon initialization
}

def get_db_connection():
    """Establishes a dedicated physical TCP session link connection to the target PostgreSQL Operational Data Store."""
    return psycopg2.connect(
        host="localhost",
        port="5433",
        database=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD')
    )

def init_db():
    """DB Bootstrapping: Generates structural storage tables if missing to guarantee initial write execution paths."""
    conn = get_db_connection()
    cur = conn.cursor()
    # Schema Definition: Defines strict constraints including explicit data types and an explicit primary identity key
    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_sentiment (
            article_id BIGINT PRIMARY KEY,
            headline TEXT,
            sentiment_score FLOAT,
            event_timestamp BIGINT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def run_consumer():
    init_db()
    consumer = Consumer(kafka_config)
    consumer.subscribe(['financial_news']) # Map stream context explicitly to our target pub/sub topic channel
    
    conn = get_db_connection()
    cur = conn.cursor()

    print("Consumer started. Listening for messages...")

    try:
        while True:
            # Continuous Streaming Polling Loop: Query the message cluster channel for new entries with a 1.0 second timeout window
            msg = consumer.poll(1.0)
            
            if msg is None:
                continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue

            # Latency Profiling: Initialize tracking anchor before execution transformations
            start_time = time.time()

            # Deserialization Stage: Decode raw binary byte sequence blocks back into structured JSON Python representations
            data = json.loads(msg.value().decode('utf-8'))
            
            # Streaming In-Flight Enrichment: Apply text processing logic to deduce a sentiment score component
            score = TextBlob(data['headline']).sentiment.polarity
            
            # Data Integrity Architecture Rule (Exactly-Once Semantics):
            # Implements an Idempotent UPSERT strategy using 'ON CONFLICT (article_id) DO NOTHING'.
            # Eliminates duplicate database record creations from network retries or message re-deliveries.
            insert_query = """
                INSERT INTO news_sentiment (article_id, headline, sentiment_score, event_timestamp)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (article_id) DO NOTHING;
            """
            cur.execute(insert_query, (data['id'], data['headline'], score, data['timestamp']))
            conn.commit() # Atomic transaction flush to persistent storage disk partitions

            end_time = time.time()
            
            # Observability & Metrics Logging: Profile ingestion performance speeds up to 4 decimal places
            print(f"Stored article {data['id']} | Score: {score:.2f} | Latency: {end_time - start_time:.4f} seconds")

    except KeyboardInterrupt:
        pass
    finally:
        # Resource Teardown Protocol: Close connections gracefully to clean up lingering file handlers and process contexts
        consumer.close()
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_consumer()