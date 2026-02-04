# Troubleshooting Guide

This guide documents common errors encountered during the setup and execution of the Stock Market Real-Time Data Pipeline and how to resolve them.

---

## 🏗️ 1. Docker & Networking Errors

### Error: `failed to set up container networking: network <ID> not found`
**Symptoms**: Producer or Consumer containers fail to start with a daemon error message.
**Cause**: The containers were created with a network ID that became invalid after the Docker network was recreated (e.g., after `docker-compose down` or `docker-compose up -d --force-recreate`).
**Solution**:
Recreate only the workload containers to link them to the current network:
```bash
docker rm -f stock-market-real-time-data-analysis-using-kafka-producer-1 stock-market-real-time-data-analysis-using-kafka-consumer-1
docker-compose --profile workload up --no-start producer consumer
```

### Error: `Failed to connect to Kafka: NoBrokersAvailable`
**Symptoms**: Producer/Consumer logs show continuous retry attempts.
**Cause**:
1. Kafka/Zookeeper haven't finished starting yet.
2. Containers are on different Docker networks.
**Solution**:
- Wait 1-2 minutes for Kafka to be fully healthy.
- Ensure all services are in the same `docker-compose.yml` and using the default network.

---

## ☁️ 2. AWS Credentials Errors

### Error: `botocore.exceptions.NoCredentialsError: Unable to locate credentials`
**Symptoms**: Airflow DAGs (Glue Crawler) or Consumer fail when trying to access AWS services.
**Cause**: AWS credentials are not being correctly passed into the Docker containers. This often happens on Windows due to environment variable scoping.
**Solution**:
**Option A (Recommended)**: Manually create an AWS Connection in Airflow:
1. Open Airflow UI (`localhost:8080`) → **Admin** → **Connections**.
2. Create/Edit `aws_default`.
3. Set Type to `Amazon Web Services` and fill in your Key/Secret.
4. In **Extra**, add: `{"region_name": "ap-southeast-1"}`.

**Option B**: Recreate containers with explicit environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
docker-compose down
docker-compose up -d
```

---

## 🌬️ 3. Airflow DAG & Operator Errors

### Error: `airflow.exceptions.AirflowException: missing keyword argument 'config'`
**Symptoms**: DAG `glue_crawler_orchestration` shows a "Broken DAG" error.
**Cause**: Newer versions of `apache-airflow-providers-amazon` (8.13.0+) require a `config` dictionary instead of individual arguments for `GlueCrawlerOperator`.
**Solution**: Pass the crawler configuration inside the `config` parameter:
```python
start_crawler = GlueCrawlerOperator(
    task_id='start_glue_crawler',
    config={
        'Name': 'your_crawler_name',
        'Role': 'your_role_arn',
        'DatabaseName': 'your_db',
        'Targets': {'S3Targets': [{'Path': 's3://path/'}]}
    }
)
```

### Error: `Invalid arguments were passed to GlueCrawlerSensor: region_name`
**Symptoms**: DAG fails during the wait/sensor task.
**Cause**: Some versions of `GlueCrawlerSensor` do not accept `region_name` as a direct argument.
**Solution**: Remove `region_name` from the Sensor. It will automatically use the region defined in the `aws_default` connection.

---

## 📊 4. Data Pipeline Issues

### Issue: Kafka started but no files in S3
**Symptoms**: Containers are "Up" but S3 bucket is empty.
**Checklist**:
1. **Check Producer Logs**: `docker logs producer` - Is it successfully sending messages?
2. **Check Consumer Logs**: `docker logs consumer` - Is it receiving messages and writing to S3?
3. **Check Connection**: Ensure the `S3_BUCKET_NAME` in `docker-compose.yml` matches your actual bucket name.
4. **Permissions**: Ensure your IAM User has `s3:PutObject` permission for that bucket.

---

## 🛠️ Efficient Management Commands

**Force recreate everything**:
```bash
docker-compose --profile workload up -d --force-recreate
```

**View logs for all services**:
```bash
docker-compose logs -f
```

**Restart only the orchestration engine**:
```bash
docker-compose restart airflow-webserver airflow-scheduler
```
