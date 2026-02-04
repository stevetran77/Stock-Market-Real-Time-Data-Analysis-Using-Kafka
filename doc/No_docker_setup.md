# Download Kafka version 3.3.1

wget https://archive.apache.org/dist/kafka/3.3.1/kafka_2.12-3.3.1.tgz

# Unzip Kafka
tar -xzf kafka_2.12-3.3.1.tgz

# Start Kafka
cd kafka_2.12-3.3.1
bin/kafka-server-start.sh config/server.properties


# Install Java

java -version # Check Java version
sudo yum install java-1.8.0-openjdk
java -version # Check Java version after installation


## Start Zoo-keeper (Zookeeper need to run first, then Kafka will run)
-------------------------------
bin/zookeeper-server-start.sh config/zookeeper.properties

Open another window to start kafka
But first ssh to to your ec2 machine as done above


## Start Kafka-server:
----------------------------------------
Duplicate the session & enter in a new console --
export KAFKA_HEAP_OPTS="-Xmx256M -Xms128M"


cd kafka_2.12-3.3.1
bin/kafka-server-start.sh config/server.properties

It is pointing to private server , change server.properties so that it can run in public IP 

To do this , you can follow any of the 2 approaches shared belwo --
Do a "sudo nano config/server.properties" - change ADVERTISED_LISTENERS to public ip of the EC2 instance


Create the topic:
-----------------------------
Duplicate the session & enter in a new console --
cd kafka_2.12-3.3.1
bin/kafka-topics.sh --create --topic demo_testing --bootstrap-server your_public_ip:9092 --replication-factor 1 --partitions 1

Start Producer:
--------------------------
bin/kafka-console-producer.sh --topic demo_testing --bootstrap-server your_public_ip:9092

Start Consumer:
-------------------------
Duplicate the session & enter in a new console --
cd kafka_2.12-3.3.1
bin/kafka-console-consumer.sh --topic demo_testing --bootstrap-server your_public_ip:9092