# Real-Time Financial News Sentiment Pipeline

<img width="2554" height="1205" alt="185803" src="https://github.com/user-attachments/assets/5fb58250-7950-489f-be0c-08598c26efc4" />

## Overview
An end-to-end streaming data engineering pipeline designed to ingest, process, and visualize the sentiment of live financial news. The system reads real-time market articles, mathematically calculates their sentiment (positive/negative/neutral), and models the data into a production-ready Star Schema for immediate visualization. 

This project demonstrates the ability to handle live API traffic, guarantee fault-tolerant message streaming, enforce data quality, and orchestrate automated workflows.

## Architecture & Tech Stack
* **Data Source:** [Finnhub API](https://finnhub.io/)
* **Orchestration:** Apache Airflow
* **Message Broker:** Apache Kafka
* **Stream Processing:** Python (TextBlob)
* **Data Warehouse:** PostgreSQL
* **Data Transformation:** dbt (Data Build Tool)
* **Visualization:** Streamlit
* **Containerization:** Docker & Docker Compose

## Pipeline Workflow
1. **Data Ingestion:** An Airflow DAG runs on an hourly schedule, triggering a Python producer that fetches live market news.
2. **Streaming:** The producer pushes raw articles to a Kafka topic (`financial_news`). This step automatically initializes the topic in the broker.
3. **Stream Processing:** A Python consumer listens to the Kafka topic, calculates a sentiment score for each headline on the fly, and lands the structured results into PostgreSQL. Exactly-once delivery is enforced via primary key constraints.
4. **Data Modeling & Testing:** dbt transforms the raw ingestion tables into a clean Star Schema (`fact_sentiment` and `dim_articles`). It enforces pipeline observability using automated data quality tests.
5. **Analytics Dashboard:** A Streamlit web application queries the dbt schema to display real-time pipeline metrics, sentiment distribution, and a live rolling news feed.

## Project Structure
```text
financial-sentiment-pipeline/
├── dags/                           # Airflow DAGs for scheduling
│   └── financial_news_dag.py
├── news_analytics/                 # dbt project folder
│   ├── models/
│   │   ├── staging/stg_news.sql
│   │   ├── core/dim_articles.sql
│   │   └── core/fact_sentiment.sql
│   └── schema.yml                  # dbt data quality tests
├── producer.py                     # Finnhub API to Kafka script
├── consumer.py                     # Kafka to PostgreSQL sentiment script
├── dashboard.py                    # Streamlit visualization app
├── check_throughput.py             # Database row count & throughput monitoring
├── docker-compose.yml              # Container infrastructure
└── requirements.txt                # Python dependencies

```
## How to Run Locally
1. Clone the repository and install dependencies
```
git clone [https://github.com/LeonDes7/Financial-News-Sentiment-Pipeline.git](https://github.com/LeonDes7/Financial-News-Sentiment-Pipeline.git)
cd Financial-News-Sentiment-Pipeline
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

## 2. Configure Environment Variables
Create a hidden .env file in the root directory to store your API keys and database credentials:
```
FINNHUB_API_KEY=your_api_key_here
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=news_db
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9094
```

## 3. Start Infrastructure
Ensure Docker Desktop is running, then start the background containers:
```
docker-compose up -d
```
Wait about 15-20 seconds for the Airflow webserver and Kafka broker to fully initialize.
## 4. Trigger Data Ingestion (Create Kafka Topic)
Before starting the consumer, we must send at least one message to Kafka to create the financial_news topic.

* Navigate to the Airflow UI at http://localhost:8080 (Login: airflow / airflow).
* Unpause the financial_news_ingestion DAG.
* Click the "Play" button to manually trigger a run.

5. Start the Stream Processor (Populate Database)
Once Airflow has fetched the first batch of news, open a terminal, activate your virtual environment, and start the Kafka consumer.
```
python consumer.py
```
Leave this terminal window open. Wait until you see "Stored article..." printed in the console, confirming that raw data has landed in PostgreSQL.

## 6. Initialize Data Warehouse (dbt)
Now that raw data exists, we can build the analytical tables. Open a new terminal window:
```
cd news_analytics
dbt run
cd ..
```

## 7. Launch the Dashboard
Finally, in that same terminal, start the Streamlit web application:
```
streamlit run dashboard.py
```
Navigate to http://localhost:8501 to view the live dashboard.

## Troubleshooting & Clean Up
* Database Connection Issues: If the dashboard shows a relation "fact_sentiment" does not exist error, it means the database was recently restarted and is empty. Ensure data is flowing via Airflow and the Consumer (Steps 4 and 5), then run dbt run inside the news_analytics folder to rebuild the schema.

* Kafka Connection Errors: If you see errors like Connect to ipv6#[::1]:9094 failed in your consumer terminal, ensure your .env file uses the explicit IPv4 address: KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9094 instead of localhost.

* Stopping the Pipeline: Press Ctrl + C in your terminal windows to stop the Python scripts. Run docker-compose down to cleanly spin down the background infrastructure.
