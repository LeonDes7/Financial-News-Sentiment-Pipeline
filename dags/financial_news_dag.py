from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator  # type: ignore

default_args = {
    'owner': 'data_engineer',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3, 
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'financial_news_ingestion',
    default_args=default_args,
    description='Hourly Finnhub news ingestion to Kafka',
    schedule_interval='@hourly', 
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['finance', 'streaming'],
) as dag:


    run_producer = BashOperator(
        task_id='run_producer_script',
        bash_command='pip install confluent-kafka requests python-dotenv && python /opt/airflow/producer.py',
    )

    run_producer