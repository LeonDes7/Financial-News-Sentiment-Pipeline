import json
import os
import psycopg2
from confluent_kafka import Consumer
from textblob import TextBlob
from dotenv import load_dotenv

load_dotenv()

kafka_config = {
    'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'), 
    'group.id': 'sentiment-analysis-group',
    'auto.offset.reset': 'earliest'
}

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port="5433",
        database=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD')
    )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
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
    consumer.subscribe(['financial_news'])
    
    conn = get_db_connection()
    cur = conn.cursor()

    print("Consumer started. Listening for messages...")

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue

            data = json.loads(msg.value().decode('utf-8'))
            
            score = TextBlob(data['headline']).sentiment.polarity
            
            insert_query = """
                INSERT INTO news_sentiment (article_id, headline, sentiment_score, event_timestamp)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (article_id) DO NOTHING;
            """
            cur.execute(insert_query, (data['id'], data['headline'], score, data['timestamp']))
            conn.commit()
            print(f"Stored article {data['id']} with score {score}")

    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_consumer()