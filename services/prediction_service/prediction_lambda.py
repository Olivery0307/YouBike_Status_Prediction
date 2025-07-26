import os
import io
import joblib
import requests
import pandas as pd
import numpy as np
import awswrangler as wr
from datetime import datetime, timedelta

# --- Configuration ---
S3_BUCKET = "chung-yeh-youbike-poc-data"
MODEL_S3_PATH = f"s3://{S3_BUCKET}/models/youbike_lgbm_model.joblib"
LOCAL_MODEL_PATH = "/tmp/youbike_lgbm_model.joblib" # Lambda's temporary storage
API_URL = "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"
PREDICTIONS_PATH = f"s3://{S3_BUCKET}/predictions/"

# --- Load Model ---
# This happens once when the Lambda container starts up, making subsequent runs faster.
print("Loading model from S3...")
# Download the model from S3 to the local /tmp directory
wr.s3.download(path=MODEL_S3_PATH, local_file=LOCAL_MODEL_PATH)
# Load the model from the local file using joblib
model = joblib.load(LOCAL_MODEL_PATH)
print("Model loaded successfully.")

def feature_engineering(df):
    """Performs the same feature engineering as the training notebook."""
    print("Starting feature engineering...")
    
    # Basic time features
    df['hour'] = df['collection_timestamp'].dt.hour
    df['day_of_week'] = df['collection_timestamp'].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

    # Advanced features (Lags and Rolling Windows)
    df.sort_values(['sno', 'collection_timestamp'], inplace=True)
    features_to_engineer = ['available_rent_bikes', 'available_return_bikes']
    lag_steps = [1, 2, 3, 6]
    rolling_window_size = 6

    for col in features_to_engineer:
        for step in lag_steps:
            df[f'{col}_lag_{step}'] = df.groupby('sno')[col].shift(step)
        
        rolling_window = df.groupby('sno')[col].rolling(window=rolling_window_size)
        df[f'{col}_rolling_mean'] = rolling_window.mean().values
        df[f'{col}_rolling_std'] = rolling_window.std().values
        df[f'{col}_rolling_min'] = rolling_window.min().values
        df[f'{col}_rolling_max'] = rolling_window.max().values

    df.dropna(inplace=True)
    print("Feature engineering complete.")
    return df

def lambda_handler(event, context):
    """
    Main Lambda handler for making predictions.
    """
    print("--- Prediction run started ---")
    
    # 1. Fetch live data from YouBike API
    print("Fetching live data...")
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        live_data = response.json()
        df_live = pd.DataFrame(live_data)
        df_live['collection_timestamp'] = datetime.now()
    except requests.RequestException as e:
        print(f"Error fetching live data: {e}")
        return {'statusCode': 500, 'body': 'Failed to fetch live data.'}

    # 2. Fetch recent historical data from S3 for feature calculation
    print("Fetching recent historical data...")
    # To calculate a 30-min window, we need at least 30 mins of prior data.
    # We'll query the last hour to be safe.
    start_time = datetime.now() - timedelta(hours=1)
    
    # Use awswrangler's partitioning filter to read only the necessary data
    df_historical = wr.s3.read_parquet(
        path=f"s3://{S3_BUCKET}/realtime/",
        dataset=True,
        partition_filter=lambda x: datetime(int(x["year"]), int(x["month"]), int(x["day"])).date() >= start_time.date()
    )
    
    # Combine live and historical data, ensuring correct types
    df_historical['collection_timestamp'] = pd.to_datetime(df_historical['collection_timestamp'])
    df_combined = pd.concat([df_historical, df_live]).drop_duplicates(subset=['sno', 'collection_timestamp'], keep='last')

    # Create total feature
    df_combined['total'] = df_combined['available_rent_bikes'] + df_combined['available_return_bikes']

    # 3. Perform Feature Engineering
    df_featured = feature_engineering(df_combined)
    
    # We only want to predict on the most recent timestamp
    latest_timestamp = df_featured['collection_timestamp'].max()
    df_to_predict = df_featured[df_featured['collection_timestamp'] == latest_timestamp]

    if df_to_predict.empty:
        print("No data available to predict after feature engineering. Exiting.")
        return {'statusCode': 200, 'body': 'No data to predict.'}

    # 4. Make Predictions
    features = [
        'total', 'available_rent_bikes', 'latitude', 'longitude', 'available_return_bikes',
        'hour', 'day_of_week', 'is_weekend',
        'available_rent_bikes_lag_1', 'available_rent_bikes_lag_2', 'available_rent_bikes_lag_3', 'available_rent_bikes_lag_6',
        'available_rent_bikes_rolling_mean', 'available_rent_bikes_rolling_std', 'available_rent_bikes_rolling_min', 'available_rent_bikes_rolling_max',
        'available_return_bikes_lag_1', 'available_return_bikes_lag_2', 'available_return_bikes_lag_3', 'available_return_bikes_lag_6',
        'available_return_bikes_rolling_mean', 'available_return_bikes_rolling_std', 'available_return_bikes_rolling_min', 'available_return_bikes_rolling_max'
    ]
    X_live = df_to_predict[features]
    
    print(f"Making predictions for {len(X_live)} stations...")
    predictions_codes = model.predict(X_live)
    
    # Map codes back to labels (This must match your trained model's mapping)
    label_map = {0: 'EMPTY', 1: 'FULL', 2: 'HEALTHY', 3: 'LOW'} 
    predictions_labels = [label_map.get(code, 'UNKNOWN') for code in predictions_codes]
    
    df_to_predict['predicted_status'] = predictions_labels
    
    # 5. Store Predictions
    output_df = df_to_predict[['sno', 'sna', 'predicted_status', 'collection_timestamp']]
    timestamp_str = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    output_path = f"{PREDICTIONS_PATH}year={start_time.year}/month={start_time.month}/day={start_time.day}/predictions_{timestamp_str}.csv"
    
    print(f"Saving {len(output_df)} predictions to {output_path}...")
    wr.s3.to_csv(df=output_df, path=output_path, index=False)
    
    # Save a JSON version to a fixed path for the dashboard
    latest_json_path = f"s3://{S3_BUCKET}/predictions/latest_predictions.json"
    print(f"Saving latest predictions for dashboard to {latest_json_path}...")
    # Include coordinates needed for the map
    output_df_json = df_to_predict[['sno', 'sna', 'latitude', 'longitude', 'predicted_status', 'collection_timestamp']]
    wr.s3.to_json(df=output_df_json, path=latest_json_path, orient="records")


    print("--- Prediction run finished successfully ---")
    return {'statusCode': 200, 'body': 'Predictions generated successfully.'}
