markdown_content = """# Real-Time Financial News Sentiment Pipeline

![Dashboard Screenshot](image_0216d4.jpg)

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
2. **Streaming:** The producer pushes raw articles to a Kafka topic (`financial_news`), guaranteeing fault-tolerant delivery.
3. **Stream Processing:** A Python consumer constantly listens to the Kafka topic, calculates a sentiment score for each headline on the fly, and lands the structured results into PostgreSQL. Exactly-once delivery is enforced via primary key constraints (`article_id`).
4. **Data Modeling & Testing:** dbt transforms the raw ingestion tables into a clean Star Schema (`fact_sentiment` and `dim_articles`). It enforces pipeline observability using automated data quality tests (uniqueness, not-null, referential integrity).
5. **Analytics Dashboard:** A Streamlit web application queries the dbt schema to display real-time pipeline metrics, sentiment distribution, and a live rolling news feed.

## Project Structure
