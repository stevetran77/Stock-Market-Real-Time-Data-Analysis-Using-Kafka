"""
AWS Glue Crawler Orchestration DAG

This DAG orchestrates the AWS Glue Crawler to catalog stock market data in S3
and make it available for querying in Amazon Athena.

Configuration:
- Crawler Name: stock_market_kafka_project
- Database Name: stock_market_kafka
- S3 Path: s3://kafka-stock-market-steve/
- Region: ap-southeast-1
- IAM Role: glue-admin-role

This DAG is triggered automatically after the Kafka consumer finishes writing data.
"""

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue_crawler import GlueCrawlerOperator
from airflow.providers.amazon.aws.sensors.glue_crawler import GlueCrawlerSensor
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging

# Configuration
GLUE_CRAWLER_NAME = "stock_market_kafka_project"
GLUE_DATABASE_NAME = "stock_market_kafka"
AWS_REGION = "ap-southeast-1"
GLUE_IAM_ROLE = "glue-admin-role" # Note: If this fails, use the full ARN
S3_PATH = "s3://kafka-stock-market-steve/"

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def log_crawler_start(**context):
    """Log the start of the Glue Crawler"""
    logging.info(f"Starting AWS Glue Crawler: {GLUE_CRAWLER_NAME}")
    logging.info(f"Target Database: {GLUE_DATABASE_NAME}")
    logging.info(f"Region: {AWS_REGION}")

def log_crawler_completion(**context):
    """Log the completion of the Glue Crawler"""
    logging.info(f"AWS Glue Crawler {GLUE_CRAWLER_NAME} completed successfully!")
    logging.info(f"Data is now cataloged and ready for Athena queries")
    logging.info(f"Database: {GLUE_DATABASE_NAME}")

with DAG(
    'glue_crawler_orchestration',
    default_args=default_args,
    description='Orchestrate AWS Glue Crawler to catalog stock market data for Athena',
    schedule_interval=None,  # Triggered by kafka_start DAG
    catchup=False,
    tags=['glue', 'crawler', 'athena', 'aws'],
) as dag:

    # Task 1: Log crawler start
    log_start = PythonOperator(
        task_id='log_crawler_start',
        python_callable=log_crawler_start,
        provide_context=True,
    )

    # Task 2: Start the Glue Crawler
    # In newer versions of apache-airflow-providers-amazon, a 'config' dictionary is required
    start_crawler = GlueCrawlerOperator(
        task_id='start_glue_crawler',
        config={
            'Name': GLUE_CRAWLER_NAME,
            'Role': GLUE_IAM_ROLE,
            'DatabaseName': GLUE_DATABASE_NAME,
            'Targets': {
                'S3Targets': [
                    {
                        'Path': S3_PATH,
                    },
                ],
            },
        },
        aws_conn_id='aws_default',
        region_name=AWS_REGION,
        wait_for_completion=False,
    )

    # Task 3: Wait for crawler to complete
    wait_for_crawler = GlueCrawlerSensor(
        task_id='wait_for_crawler_completion',
        crawler_name=GLUE_CRAWLER_NAME,
        aws_conn_id='aws_default',
        poke_interval=30,  # Check every 30 seconds
        timeout=3600,  # Timeout after 1 hour
        mode='poke',
    )

    # Task 4: Log crawler completion
    log_completion = PythonOperator(
        task_id='log_crawler_completion',
        python_callable=log_crawler_completion,
        provide_context=True,
    )

    # Define task dependencies
    log_start >> start_crawler >> wait_for_crawler >> log_completion
