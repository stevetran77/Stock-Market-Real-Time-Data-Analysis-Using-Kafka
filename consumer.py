import pandas as pd
from kafka import KafkaConsumer
from time import sleep
from json import loads
import json
from s3fs import S3FileSystem
import os
import time
import boto3
from botocore.exceptions import ClientError

# Configuration
# KAFKA_BOOTSTRAP_SERVERS: List of Kafka broker addresses.
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
# TOPIC_NAME: The Kafka topic to subscribe to.
TOPIC_NAME = os.getenv('KAFKA_TOPIC_NAME', 'demo_testing')
# S3_BUCKET_NAME: Target S3 bucket for storing processed data.
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'kafka-stock-market-steve')
# SECRET_NAME: Name of the secret in AWS Secrets Manager containing S3 credentials.
SECRET_NAME = os.getenv('AWS_SECRET_NAME', 's3_access_secret')
# REGION_NAME: AWS Region where the Secrets Manager and S3 bucket are located.
REGION_NAME = os.getenv('AWS_REGION', 'ap-southeast-1')

def get_secret():
    """
    Retrieves the AWS credentials secret from AWS Secrets Manager.
    
    This function initializes a boto3 client for Secrets Manager and attempts to 
    fetch the secret value specified by SECRET_NAME. It is robust against ClientErrors.
    
    Returns:
        dict: A dictionary containing the parsed JSON secret (e.g., {'AWS_ACCESS_KEY_ID': '...', ...}).
              Returns None if the secret cannot be retrieved or is not found.
    """
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=REGION_NAME
    )

    try:
        # API call to AWS Secrets Manager to get the secret value.
        get_secret_value_response = client.get_secret_value(SecretId=SECRET_NAME)
    except ClientError as e:
        # Log any AWS client errors (e.g., permission denied, secret not found)
        print(f"Error retrieving secret {SECRET_NAME}: {e}")
        return None

    # Decrypts secret using the associated KMS CMK.
    # Depending on whether the secret is a string or binary, one of these fields will be populated.
    if 'SecretString' in get_secret_value_response:
        return json.loads(get_secret_value_response['SecretString'])
    return None

def create_consumer():
    """
    Initializes and returns a KafkaConsumer instance, ensuring connection reliability.
    
    Similar to the producer, this function loops indefinitely until it can successfully
    connect to the Kafka broker. This robustness is critical in orchestrated environments.
    
    Returns:
        KafkaConsumer: A configured consumer subscribed to the target topic.
    """
    while True:
        try:
            # Initialize the Consumer.
            # auto_offset_reset='latest' means we start reading from the new messages 
            # arriving after we connect, ignoring old history.
            # value_deserializer handles converting the received bytes back into a JSON object.
            consumer = KafkaConsumer(
                TOPIC_NAME,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda x: loads(x.decode('utf-8')),
                auto_offset_reset='latest' 
            )
            print(f"Successfully connected to Kafka topic '{TOPIC_NAME}'")
            return consumer
        except Exception as e:
            # Wait and retry if the broker is unavailable.
            print(f"Failed to connect to Kafka: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def main():
    """
    Main entry point for the Consumer application.
    
    Workflow:
    1. Authenticates with AWS (via Secrets Manager or Environment context).
    2. Initializes S3FileSystem for writing files.
    3. Connects to Kafka and starts a loop to consume messages.
    4. Writes each consumed message to a unique file in the S3 bucket.
    """
    print(f"Starting Consumer. Connecting to {KAFKA_BOOTSTRAP_SERVERS}...")
    
    # Initialize the s3_fs variable. it will be assigned a valid S3FileSystem object below.
    s3_fs = None
    
    # Check if a Secret Name is configured. If so, prioritize fetching credentials from Secrets Manager.
    if SECRET_NAME:
        print(f"Attempting to retrieve credentials from Secrets Manager: {SECRET_NAME}")
        secrets = get_secret()
        if secrets:
            print("Successfully retrieved credentials from Secrets Manager.")
            # Explicitly initialize S3FileSystem with the retrieved keys.
            s3_fs = S3FileSystem(
                key=secrets.get('AWS_ACCESS_KEY_ID'),
                secret=secrets.get('AWS_SECRET_ACCESS_KEY')
            )
        else:
            print("Failed to retrieve secrets or secrets empty. Falling back to default chain or env vars.")
    
    # If Secrets Manager retrieval failed or wasn't configured, fall back to default AWS auth chain.
    # This supports cases like running on an EC2 instance with an IAM Role attached.
    if s3_fs is None:
        print("Using default S3FileSystem init (Env vars set in docker-compose or IAM role).")
        s3_fs = S3FileSystem()

    # Establish Kafka connection
    consumer = create_consumer()

    # Main consumption loop.
    # enumerate provides a counter 'count' which we use to generate unique filenames.
    for count, i in enumerate(consumer):
        try:
            # Define the destination path in S3.
            file_path = f"s3://{S3_BUCKET_NAME}/stock_market_{count}.json"
            
            # Open a write stream to S3 and dump the JSON content.
            with s3_fs.open(file_path, 'w') as file:
                json.dump(i.value, file)
            print(f"Wrote record {count} to {file_path}")
        except Exception as e:
            # Log S3 write errors but keep the consumer running.
            print(f"Error writing to S3: {e}")

if __name__ == "__main__":
    main()
