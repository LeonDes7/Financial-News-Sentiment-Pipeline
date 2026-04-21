import json
import os
import requests
from confluent_kafka import Producer
from dotenv import load_dotenv

load_dotenv()

config = {
    'bootstrap.servers': 'kafka:9092', 
    'client.id': 'news-producer'
}

producer = Producer(config)

def delivery_report(err, msg):
    """Callback triggered by Kafka to check if message delivery succeeded or failed."""
    if err is not None:
        print(f"Message delivery failed: {err}")

def fetch_news():
    """Fetches the latest general news from Finnhub."""
    api_key = os.getenv('FINNHUB_API_KEY')
    url = f'https://finnhub.io/api/v1/news?category=general&token={api_key}'
    
    try:
        response = requests.get(url)
        response.raise_for_status() 
        return response.json()
    except Exception as e:
        print(f"Error fetching data from Finnhub: {e}")
        return []

def main():
    """Main execution function designed to run once per Airflow task trigger."""
    print("Starting single-batch ingestion...")
    articles = fetch_news()
    
    if not articles:
        print("No articles fetched. Exiting.")
        return

    success_count = 0
    for article in articles:
        # Enforce schema
        payload = {
            'id': article.get('id'),
            'headline': article.get('headline'),
            'summary': article.get('summary'),
            'timestamp': article.get('datetime')
        }
        
        try:
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
    producer.flush()
    print("Ingestion batch complete. Exiting script.")

if __name__ == "__main__":
    main()