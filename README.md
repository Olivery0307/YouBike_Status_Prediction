# YouBike Station Availability Prediction

This project aims to build and deploy a machine learning model to predict the short-term availability status (e.g., `EMPTY`, `FULL`, `LOW`) of YouBike stations across Taipei.

---

### Current Status (as of July 2025)

The project has successfully completed the initial development phases. We have a trained model that is highly effective at its primary goal: providing an early warning for station imbalances.

* **Data Pipeline:** A serverless AWS pipeline is live, collecting real-time station data every 5 minutes and storing it in S3.
* **Trained Model:** An improved `LightGBM` classification model has been trained and evaluated.
* **Key Performance:** The model is particularly effective at identifying critical states 15 minutes in advance, achieving **90% recall** for `FULL` stations and **77% recall** for `EMPTY` stations.
* **Next Step:** **Phase 4: Deployment**, where we will operationalize this model to make live predictions.

---

### Project Architecture

1.  **Data Collection:** An automated, serverless pipeline on AWS.
    * **Amazon EventBridge:** Triggers the process every 5 minutes.
    * **AWS Lambda:** A Python function fetches and processes the data.
    * **Amazon S3:** Stores the raw and processed data in Parquet format.

2.  **Machine Learning Model:**
    * **Algorithm:** `LightGBM` Classifier.
    * **Features:** The model uses the current station status combined with engineered time-series features like lags (e.g., bike availability 15 mins ago) and rolling window statistics (e.g., average availability over the last 30 mins).
    * **Target:** Predicts the station's status (`EMPTY`, `FULL`, `LOW`, `HEALTHY`) 15 minutes into the future.

---

### How to Run the Analysis

To explore the data preparation and model training process:

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd youbike-prediction-project
    ```

2.  **Set up the environment:**
    ```bash
    # Create and activate a virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install required packages
    pip install -r requirements.txt
    ```

3.  **Launch Jupyter and run the notebook:**
    ```bash
    jupyter lab
    ```
    Open and run the notebook inside the `notebooks/` directory to see the full data processing and modeling workflow.

---