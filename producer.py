import json
import os
import requests
from confluent_kafka import Producer
from dotenv import load_dotenv

load_dotenv()

# Cluster Connectivity Configuration
config = {
    'bootstrap.servers': 'kafka:9092',  # Internal Docker bridge network broker address
    'client.id': 'news-producer'
}

# Instantiate the Kafka producer instance using the confluent-kafka C-based client bindings
producer = Producer(config)

def delivery_report(err, msg):
    """
    Asynchronous delivery callback mechanism triggered by Kafka broker acknowledgments (ACKs).
    Used to track structural message delivery or message drop issues without blocking the main event loop.
    """
    if err is not None:
        print(f"Message delivery failed: {err}")

def fetch_news():
    """Fetches raw transactional event data from the upstream external API."""
    api_key = os.getenv('FINNHUB_API_KEY')
    url = f'https://finnhub.io/api/v1/news?category=general&token={api_key}'
    
    try:
        response = requests.get(url)
        response.raise_for_status() # Network Guardrail: Throws an exception for 4xx/5xx HTTP errors
        return response.json()
    except Exception as e:
        print(f"Error fetching data from Finnhub: {e}")
        return []

def main():
    """
    Orchestration Task Target: Designed for stateless, episodic execution triggered hourly by Apache Airflow.
    """
    print("Starting single-batch ingestion...")
    articles = fetch_news()
    
    if not articles:
        print("No articles fetched. Exiting.")
        return

    success_count = 0
    for article in articles:
        # Schema Enforcement Phase: Construct a normalized payload dictionary from raw json fields
        payload = {
            'id': article.get('id'),
            'headline': article.get('headline'),
            'summary': article.get('summary'),
            'timestamp': article.get('datetime')
        }
        
        try:
            # Asynchronous Event Production: Append event records to the internal local thread accumulator buffer.
            # Specifies the 'id' as the routing message key to guarantee partition grouping logic.
            producer.produce(
                'financial_news',
                key=str(payload['id']),
                value=json.dumps(payload),
                callback=delivery_report
            )
            success_count += 1
        except Exception as e:
            print(f"Failed to queue message for article {payload.get('id')}: {e}")
    
    print(f"Flushing {success_count} articles to Kafka...")
    # Synchronous Blocking Flush: Empties internal producer message queues and forces network transmission 
    # to the cluster broker before letting the episodic execution context exit safely.
    producer.flush()
    print("Ingestion batch complete. Exiting script.")

if __name__ == "__main__":
    main()