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
    'kafka_stop',
    default_args=default_args,
    description='Stop the Stock Market Producer and Consumer containers',
    schedule_interval=None,
    catchup=False,
    tags=['kafka', 'control'],
) as dag:

    # Stop producer and consumer containers
    stop_workload = BashOperator(
        task_id='stop_kafka_workload',
        bash_command='''
        # Find and stop producer container
        PRODUCER=$(docker ps --filter "name=producer" --filter "ancestor=stock-market-producer:latest" --format "{{ '{{' }}.Names{{ '}}' }}" | head -1)
        if [ -n "$PRODUCER" ]; then
            docker stop $PRODUCER
            echo "Stopped producer: $PRODUCER"
        else
            echo "Producer container not running"
        fi
        
        # Find and stop consumer container
        CONSUMER=$(docker ps --filter "name=consumer" --filter "ancestor=stock-market-consumer:latest" --format "{{ '{{' }}.Names{{ '}}' }}" | head -1)
        if [ -n "$CONSUMER" ]; then
            docker stop $CONSUMER
            echo "Stopped consumer: $CONSUMER"
        else
            echo "Consumer container not running"
        fi
        ''',
    )
