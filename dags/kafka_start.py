from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 0,
}

with DAG(
    'kafka_start',
    default_args=default_args,
    description='Start the Stock Market Producer and Consumer containers',
    schedule_interval=None,
    catchup=False,
    tags=['kafka', 'control'],
) as dag:

    # Start producer and consumer containers that were created by the host
    # Using {% raw %} to prevent Jinja from parsing docker format strings
    start_workload = BashOperator(
        task_id='start_kafka_workload',
        bash_command='''
        # Find and start producer container
        PRODUCER=$(docker ps -a --filter "name=producer" --filter "ancestor=stock-market-producer:latest" --format "{{ '{{' }}.Names{{ '}}' }}" | head -1)
        if [ -n "$PRODUCER" ]; then
            docker start $PRODUCER
            echo "Started producer: $PRODUCER"
        else
            echo "ERROR: Producer container not found. Please run 'docker-compose --profile workload up -d' on the host first."
            exit 1
        fi
        
        # Find and start consumer container
        CONSUMER=$(docker ps -a --filter "name=consumer" --filter "ancestor=stock-market-consumer:latest" --format "{{ '{{' }}.Names{{ '}}' }}" | head -1)
        if [ -n "$CONSUMER" ]; then
            docker start $CONSUMER
            echo "Started consumer: $CONSUMER"
        else
            echo "ERROR: Consumer container not found. Please run 'docker-compose --profile workload up -d' on the host first."
            exit 1
        fi
        ''',
    )
