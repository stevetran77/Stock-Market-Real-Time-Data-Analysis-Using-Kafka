# AWS Glue Setup Guide

This guide walks you through setting up AWS Glue Crawler and Data Catalog for the Stock Market Real-Time Data Pipeline.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured (optional, but recommended)
- S3 bucket with stock market data: `s3://kafka-stock-market-steve/`
- AWS Region: `ap-southeast-1` (Singapore)

## Architecture Overview

```
Kafka Consumer → S3 Bucket → Glue Crawler → Glue Data Catalog → Amazon Athena
```

The Glue Crawler automatically discovers the schema of your JSON data in S3 and creates/updates table definitions in the Glue Data Catalog, making the data queryable via Athena.

---

## Step 1: Verify IAM Role

You mentioned having an IAM role named `glue-admin-role`. Ensure it has the following permissions:

### Required Policies

1. **AWSGlueServiceRole** (AWS Managed Policy)
   - Provides Glue service permissions

2. **S3 Read Access** (Custom Policy)
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:GetObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::kafka-stock-market-steve",
           "arn:aws:s3:::kafka-stock-market-steve/*"
         ]
       }
     ]
   }
   ```

3. **CloudWatch Logs** (for crawler logs)
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "logs:CreateLogGroup",
           "logs:CreateLogStream",
           "logs:PutLogEvents"
         ],
         "Resource": "arn:aws:logs:ap-southeast-1:*:*"
       }
     ]
   }
   ```

### Trust Relationship

Ensure the role has a trust relationship with Glue:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "glue.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

---

## Step 2: Create Glue Database

The Glue Database is a logical container for your table metadata.

### Using AWS Console

1. Navigate to **AWS Glue Console** → **Databases**
2. Click **Add database**
3. Enter database name: `stock_market_kafka`
4. (Optional) Add description: "Stock market real-time data from Kafka pipeline"
5. Click **Create**

### Using AWS CLI

```bash
aws glue create-database \
  --database-input '{
    "Name": "stock_market_kafka",
    "Description": "Stock market real-time data from Kafka pipeline"
  }' \
  --region ap-southeast-1
```

---

## Step 3: Create or Verify Glue Crawler

You mentioned having a crawler named `stock_market_kafka_project`. Verify or create it with the following configuration:

### Using AWS Console

1. Navigate to **AWS Glue Console** → **Crawlers**
2. Click **Create crawler**
3. **Crawler name**: `stock_market_kafka_project`
4. Click **Next**

#### Data Source Configuration

5. **Data source type**: S3
6. **S3 path**: `s3://kafka-stock-market-steve/`
7. **Subsequent crawler runs**: Crawl all sub-folders
8. Click **Next**

#### IAM Role

9. **Choose an existing IAM role**: Select `glue-admin-role`
10. Click **Next**

#### Target Database

11. **Target database**: Select `stock_market_kafka`
12. **Table name prefix** (optional): `kafka_` (this will prefix all discovered tables)
13. Click **Next**

#### Crawler Schedule

14. **Frequency**: On demand (Airflow will trigger it)
15. Click **Next**

16. Review and click **Create crawler**

### Using AWS CLI

```bash
aws glue create-crawler \
  --name stock_market_kafka_project \
  --role arn:aws:iam::<YOUR_ACCOUNT_ID>:role/glue-admin-role \
  --database-name stock_market_kafka \
  --targets '{
    "S3Targets": [
      {
        "Path": "s3://kafka-stock-market-steve/"
      }
    ]
  }' \
  --region ap-southeast-1
```

**Note**: Replace `<YOUR_ACCOUNT_ID>` with your AWS account ID.

---

## Step 4: Test Crawler Manually (Optional)

Before using Airflow, test the crawler manually:

### Using AWS Console

1. Go to **AWS Glue Console** → **Crawlers**
2. Select `stock_market_kafka_project`
3. Click **Run crawler**
4. Wait for the crawler to complete (status will change to "Ready")
5. Check **Databases** → `stock_market_kafka` → **Tables** to see discovered tables

### Using AWS CLI

```bash
# Start the crawler
aws glue start-crawler \
  --name stock_market_kafka_project \
  --region ap-southeast-1

# Check crawler status
aws glue get-crawler \
  --name stock_market_kafka_project \
  --region ap-southeast-1 \
  --query 'Crawler.State'
```

---

## Step 5: Configure Athena Workgroup (Optional)

For querying data with Athena, you'll need a workgroup and query result location.

### Using AWS Console

1. Navigate to **Amazon Athena Console**
2. If prompted, set up a query result location:
   - Click **Settings**
   - Set **Query result location**: `s3://kafka-stock-market-steve/athena-results/`
   - Click **Save**

### Create a Workgroup (Optional)

1. Go to **Workgroups** tab
2. Click **Create workgroup**
3. **Workgroup name**: `stock-market-workgroup`
4. **Query result location**: `s3://kafka-stock-market-steve/athena-results/`
5. Click **Create workgroup**

---

## Step 6: Verify Data Catalog

After the crawler runs successfully:

1. Go to **AWS Glue Console** → **Databases** → `stock_market_kafka`
2. You should see tables created by the crawler
3. Click on a table to view its schema
4. The schema should match your JSON data structure

---

## Step 7: Test Athena Query

Once the Data Catalog is populated, test querying the data:

### Using Athena Console

1. Navigate to **Amazon Athena Console**
2. Select database: `stock_market_kafka`
3. Run a test query:

```sql
-- List all tables
SHOW TABLES;

-- View table schema (replace 'your_table_name' with actual table name)
DESCRIBE your_table_name;

-- Query sample data
SELECT * FROM your_table_name LIMIT 10;

-- Example: Get stock data for a specific date
SELECT *
FROM your_table_name
WHERE date = '2024-01-01'
LIMIT 100;
```

### Using AWS CLI

```bash
# Start query execution
aws athena start-query-execution \
  --query-string "SELECT * FROM your_table_name LIMIT 10;" \
  --query-execution-context Database=stock_market_kafka \
  --result-configuration OutputLocation=s3://kafka-stock-market-steve/athena-results/ \
  --region ap-southeast-1
```

---

## Troubleshooting

### Crawler Fails to Run

**Issue**: Crawler fails with permission errors

**Solution**: 
- Verify IAM role `glue-admin-role` has S3 read permissions
- Check CloudWatch Logs for detailed error messages
- Ensure S3 bucket exists and contains data

### No Tables Created

**Issue**: Crawler runs successfully but no tables appear

**Solution**:
- Verify S3 path contains JSON files
- Check crawler configuration points to correct S3 path
- Ensure JSON files are valid and not empty
- Check crawler logs in CloudWatch

### Athena Query Fails

**Issue**: "Table not found" or "Schema mismatch" errors

**Solution**:
- Verify crawler has run successfully
- Check table exists in Glue Data Catalog
- Ensure you've selected the correct database in Athena
- Try refreshing the Athena table list

### Airflow Can't Access AWS

**Issue**: Airflow DAG fails with AWS credential errors

**Solution**:
- Verify AWS credentials are set in environment variables
- Check `docker-compose.yml` has correct AWS environment variables
- Ensure `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are exported
- Verify region is set to `ap-southeast-1`

---

## Best Practices

1. **Crawler Schedule**: Use Airflow to trigger crawler on-demand rather than scheduled runs
2. **Table Partitioning**: Consider partitioning S3 data by date for better query performance
3. **Cost Optimization**: Glue Crawler charges per DPU-hour; avoid running unnecessarily
4. **Data Format**: Consider using Parquet instead of JSON for better compression and query performance
5. **Monitoring**: Set up CloudWatch alarms for crawler failures

---

## Next Steps

1. Ensure AWS credentials are configured in your environment
2. Rebuild Airflow Docker image: `docker-compose build`
3. Start Airflow: `docker-compose up -d`
4. Trigger the `kafka_start` DAG to test the end-to-end pipeline
5. Monitor the `glue_crawler_orchestration` DAG execution
6. Query your data in Athena!

---

## Additional Resources

- [AWS Glue Documentation](https://docs.aws.amazon.com/glue/)
- [AWS Glue Crawler Documentation](https://docs.aws.amazon.com/glue/latest/dg/add-crawler.html)
- [Amazon Athena Documentation](https://docs.aws.amazon.com/athena/)
- [Airflow AWS Provider Documentation](https://airflow.apache.org/docs/apache-airflow-providers-amazon/)
