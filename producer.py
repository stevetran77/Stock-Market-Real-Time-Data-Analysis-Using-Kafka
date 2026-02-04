import pandas as pd
from kafka import KafkaProducer
from time import sleep
from json import dumps
import json
import os
import time

# Configuration
# KAFKA_BOOTSTRAP_SERVERS: List of Kafka broker addresses (host:port). Defaults to localhost for local testing.
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
# TOPIC_NAME: The Kafka topic to send data to.
TOPIC_NAME = os.getenv('KAFKA_TOPIC_NAME', 'demo_testing')
# DATA_FILE: Path to the source CSV file containing stock market data.
DATA_FILE = 'data/indexProcessed.csv'

def create_producer():
    """
    Initializes and returns a KafkaProducer instance, ensuring connection reliability.
    
    This function implements a forever-retry loop to handle the case where the Kafka
    broker might not be ready immediately (e.g., during Docker container startup).
    It attempts to create the producer and only returns when successful.
    
    Returns:
        KafkaProducer: A fully connected producer ready to send messages.
    """
    while True:
        try:
            # Initialize the Kafka producer using the configured bootstrap servers.
            # value_serializer is set to specific JSON serialization to ensure dictionaries 
            # are converted to bytes correctly before sending.
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda x: dumps(x).encode('utf-8')
            )
            print("Successfully connected to Kafka.")
            return producer
        except Exception as e:
            # If connection fails (e.g., Broker not found), log the error and wait 5 seconds before retrying.
            print(f"Failed to connect to Kafka: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def main():
    """
    Main entry point for the Producer application.
    
    Orchestrates the data flow:
    1. Loads historical stock data from the local CSV file.
    2. Initializes the Kafka Producer connection.
    3. Enters an infinite loop to simulate real-time data streaming by picking random records.
    """
    print(f"Starting Producer. Connecting to {KAFKA_BOOTSTRAP_SERVERS}...")
    
    # Establish the connection to Kafka
    producer = create_producer()

    try:
        # Load the entire dataset into a pandas DataFrame.
        # This acts as our data source for simulation.
        df = pd.read_csv(DATA_FILE)
        print(f"Loaded {len(df)} rows from {DATA_FILE}")
    except FileNotFoundError:
        print(f"Error: The data file '{DATA_FILE}' was not found. Please ensure it exists.")
        return

    while True:
        try:
            # Select a random row from the DataFrame to simulate a random stock update.
            # to_dict(orient='records')[0] converts the single row DataFrame into a standard Python dictionary.
            dict_stock = df.sample().to_dict(orient='records')[0]
            
            # Asynchronously send the data dictionary to the defined Kafka topic.
            producer.send(TOPIC_NAME, value=dict_stock)
            
            # Log the sent message for monitoring purposes.
            print(f"Sent: {dict_stock}")
            
            # Sleep for 1 second to control the ingestion rate (1 msg/sec).
            sleep(1)
        except Exception as e:
            # Catch transient errors during sending to prevent the script from crashing.
            print(f"Error sending message: {e}")
            sleep(1)

if __name__ == "__main__":
    main()
