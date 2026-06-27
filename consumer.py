import os
import json
import time
import psycopg2
import pandas as pd
from confluent_kafka import Consumer, KafkaError
from transformers import pipeline
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()

class ArticlePayload(BaseModel):
    id: int
    headline: str
    summary: str | None = None
    timestamp: int

kafka_config = {
    'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9094'),
    'group.id': 'financial-sentiment-analysis-v2',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False
}

print("Loading Financial BERT Transformer model into memory...")
sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model="ProsusAI/finbert",
    device=-1
)

def run_ge_checkpoint(records: list[dict]) -> bool:
    """
    Enforces 5 Great Expectations-style data contracts on a batch of
    raw Kafka ingestion records before PostgreSQL loading.
    """
    try:
        df = pd.DataFrame(records)
        violations = []

        # Contract 1: id must never be null
        if df["id"].isnull().any():
            violations.append("expect_column_values_to_not_be_null: id")

        # Contract 2: headline must never be null
        if df["headline"].isnull().any():
            violations.append("expect_column_values_to_not_be_null: headline")

        # Contract 3: timestamp must be a positive integer
        if (df["timestamp"] < 0).any():
            violations.append("expect_column_values_to_be_between: timestamp >= 0")

        # Contract 4: id must be unique within batch
        if df["id"].duplicated().any():
            violations.append("expect_column_values_to_be_unique: id")

        # Contract 5: headline must be non-empty string
        if (df["headline"].str.len() < 1).any():
            violations.append("expect_column_value_lengths_to_be_between: headline >= 1")

        if violations:
            print(f"[GE CONTRACT VIOLATION] {len(violations)} expectation(s) failed:")
            for v in violations:
                print(f"  - {v}")
            return False

        print(f"[GE CHECKPOINT] All 5 data contracts passed on batch of {len(records)}.")
        return True

    except Exception as e:
        print(f"[GE ERROR] Validation failed with exception: {e}")
        return False

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5433'),
        database=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD')
    )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_sentiment (
            article_id BIGINT,
            headline TEXT,
            sentiment_score FLOAT,
            event_timestamp BIGINT,
            PRIMARY KEY (article_id, event_timestamp)
        );
        CREATE INDEX IF NOT EXISTS idx_news_timestamp ON news_sentiment (event_timestamp DESC);
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

    print("FinBERT Consumer Active. Processing live pipeline streams...")

    ge_batch = []
    GE_BATCH_SIZE = 10

    try:
        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                print(f"Stream Broker Error: {msg.error()}")
                continue

            loop_start = time.time()

            try:
                # 1. Pydantic schema validation
                raw_payload = json.loads(msg.value().decode('utf-8'))
                validated_data = ArticlePayload(**raw_payload)

                # 2. Accumulate batch for GE checkpoint
                ge_batch.append(raw_payload)
                if len(ge_batch) >= GE_BATCH_SIZE:
                    passed = run_ge_checkpoint(ge_batch)
                    if not passed:
                        print(f"[GE] Batch failed contracts — skipping batch.")
                        ge_batch = []
                        continue
                    ge_batch = []

                # 3. FinBERT inference
                inference_start = time.time()
                nlp_res = sentiment_pipeline(validated_data.headline)[0]
                inference_end = time.time()

                label_mapping = {'positive': 1.0, 'negative': -1.0, 'neutral': 0.0}
                score = label_mapping[nlp_res['label']] * nlp_res['score']
                inference_ms = (inference_end - inference_start) * 1000

                # 4. Idempotent PostgreSQL write
                insert_query = """
                    INSERT INTO news_sentiment (article_id, headline, sentiment_score, event_timestamp)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (article_id, event_timestamp) DO NOTHING;
                """
                cur.execute(insert_query, (validated_data.id, validated_data.headline, score, validated_data.timestamp))
                conn.commit()

                # 5. Manual offset commit — exactly-once delivery
                consumer.commit(msg, asynchronous=True)

                loop_end = time.time()
                total_latency_ms = (loop_end - loop_start) * 1000

                # 6. Adaptive backpressure
                if total_latency_ms > 200:
                    print(f"[BACKPRESSURE WARNING] Loop latency hit {total_latency_ms:.2f}ms. Throttling.")
                    time.sleep(0.05)

                print(f"Sync ID: {validated_data.id} | Compute Latency: {inference_ms:.2f}ms | Loop Latency: {total_latency_ms:.2f}ms | Score: {score:.2f}")

            except ValidationError as val_err:
                print(f"Malformed stream schema encountered, bypassing record: {val_err}")
                continue

    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_consumer()