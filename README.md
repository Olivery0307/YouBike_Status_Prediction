# YouBike Station Availability Prediction

This project builds and deploys an end-to-end machine learning system to predict the short-term availability status (e.g., `EMPTY`, `FULL`, `LOW`) of YouBike stations across Taipei.

---

### Current Status (as of July 2025)

The project is fully operational with both data collection and prediction pipelines deployed on AWS.

* **Data Pipeline:** A serverless AWS Lambda function collects real-time station data every 5 minutes and stores it in S3.
* **Prediction Pipeline:** A Dockerized AWS Lambda function loads a trained model and generates live predictions every 15 minutes.
* **Model Performance:** The trained `LightGBM` model is highly effective at identifying critical states 15 minutes in advance, achieving **90% recall** for `FULL` stations and **77% recall** for `EMPTY` stations.
* **Next Step:** **Phase 5: Visualization & Insights**, where we will build a dashboard to monitor the live predictions.

---

### Project Architecture

#### 1. Data Collection Pipeline
* **Amazon EventBridge:** Triggers the process every 5 minutes.
* **AWS Lambda:** A Python function (`lambda_function.py`) fetches and processes the data.
* **Amazon S3:** Stores the raw and processed data in Parquet format.

#### 2. Prediction Pipeline (Inference)
* **Docker & Amazon ECR:** The prediction application, including all dependencies, is packaged as a Docker container image and stored in the Elastic Container Registry (ECR).
* **Amazon EventBridge:** Triggers the pipeline every 15 minutes.
* **AWS Lambda:** A function configured to run from the Docker container image executes the prediction logic.
* **Amazon S3:** The trained model artifact (`.joblib` file) is stored here, and the final predictions are saved as `.csv` and `.json` files.

---

### How to Use This Repository

#### Running the Analysis Notebooks
To explore the data preparation and model training process:

1.  **Set up the environment:**
    ```bash
    # Create and activate a virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install required packages
    pip install -r notebooks/requirements.txt
    ```

2.  **Launch Jupyter and run the notebooks:**
    ```bash
    jupyter lab
    ```
    Open and run the notebooks inside the `notebooks/` directory.

#### Building and Running the Prediction Service
The prediction service is a self-contained Docker application.

1.  **Navigate to the service directory:**
    ```bash
    cd services/prediction_service/
    ```

2.  **Build the Docker image:**
    ```bash
    docker build -t youbike-prediction-service .
    ```
    (Refer to the project documentation for instructions on pushing to ECR and deploying to AWS Lambda.)

---