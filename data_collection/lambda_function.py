import os
import io
import logging
from datetime import datetime
import requests
import pandas as pd
import boto3

S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
API_URL = "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"
s3_client = boto3.client('s3')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    This is the main function that AWS Lambda will execute.
    It's triggered by Amazon EventBridge every 5 minutes.
    """
    logger.info("Lambda execution started.")
    
    if not S3_BUCKET_NAME:
        logger.error("FATAL: S3_BUCKET_NAME environment variable is not set.")
        return {'statusCode': 500, 'body': 'Server configuration error.'}

    # 1. Fetch data from YouBike API
    try:
        response = requests.get(API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)

        # Add collection timestamp for tracking
        df['collection_timestamp'] = datetime.now()
        logger.info(f"Successfully fetched data for {len(df)} stations.")

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {'statusCode': 502, 'body': f'Failed to fetch data from API: {e}'}

    # 2. Save data to S3 in a partitioned Parquet format
    try:
        # Use the collection time to create a partitioned "folder" structure
        ts = df['collection_timestamp'].iloc[0]
        s3_key = f"realtime/year={ts.year}/month={ts.month:02d}/day={ts.day:02d}/data_{ts.strftime('%Y%m%d_%H%M%S')}.parquet"
        
        # Write the DataFrame to an in-memory buffer
        parquet_buffer = io.BytesIO()
        df.to_parquet(parquet_buffer, engine='pyarrow')
        
        # Upload the buffer's content to S3
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=parquet_buffer.getvalue()
        )
        logger.info(f"Data successfully saved to s3://{S3_BUCKET_NAME}/{s3_key}")
        
    except Exception as e:
        logger.error(f"Failed to save data to S3: {e}")
        return {'statusCode': 500, 'body': f'Failed to save data to S3: {e}'}

    return {
        'statusCode': 200,
        'body': f'Successfully collected and stored {len(df)} records.'
    }
