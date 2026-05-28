from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator  # type: ignore

# Operational Guardrails: Configure high-availability task policies for episodic scheduling
default_args = {
    'owner': 'data_engineer',
    'depends_on_past': False,  # Ensures upstream execution bottlenecks from previous hours do not stall the current run
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,              # Fault Tolerance: Automatically retries the task to overcome transient network drops or API rate-limiting
    'retry_delay': timedelta(minutes=5), # Backoff Window: Waits 5 minutes between retries to allow remote systems to recover
}

# Core DAG Definition
with DAG(
    'financial_news_ingestion',
    default_args=default_args,
    description='Hourly Finnhub news ingestion to Kafka message broker queues',
    schedule_interval='@hourly',  # Ingestion Grain: Triggers at the top of every hour to capture changing market events
    start_date=datetime(2023, 1, 1),
    catchup=False,  # Performance Guardrail: Prevents backfilling historic intervals, avoiding cluster flooding on DAG initialization
    tags=['finance', 'streaming'],
) as dag:

    # Task 1: Trigger Episodic Event Generation via Ingestion Script
    # NOTE FOR INTERVIEWS: In production, 'pip install' must be baked into the Dockerfile or base environment image.
    # Running pip setup tasks inside an active worker node introduces high latency and an external runtime dependency on PyPI.
    run_producer = BashOperator(
        task_id='run_producer_script',
        bash_command='pip install confluent-kafka requests python-dotenv && python /opt/airflow/producer.py',
    )

    # Declarative Dependency Graph (Singular Node Pipeline Context)
    run_producer