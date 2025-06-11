from datetime import datetime, timedelta
import uuid
from airflow import DAG
from airflow.providers.google.cloud.operators.dataproc import DataprocCreateBatchOperator
from airflow.providers.google.cloud.sensors.gcs import GCSObjectsWithPrefixExistenceSensor
from airflow.providers.google.cloud.transfers.gcs_to_gcs import GCSToGCSOperator
from airflow.utils.trigger_rule import TriggerRule

# DAG default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2025, 2, 7),
}

# Define the DAG
with DAG(
    dag_id="credit_card_transactions_dataproc_dag",
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
) as dag:

    # Define GCS Bucket & File Pattern
    gcs_bucket = "credit-card-data-analysis"
    file_pattern = "transactions/transactions_"
    source_prefix = "transactions/"
    archive_prefix = "archive/"

    # Task 1: GCS Sensor (Detects Latest JSON File)
    file_sensor = GCSObjectsWithPrefixExistenceSensor(
        task_id="check_json_file_arrival",
        bucket=gcs_bucket,
        prefix=file_pattern,
        timeout=600,
        poke_interval=30,
        mode="poke",
    )

    # Generate a unique batch ID using UUID
    batch_id = f"credit-card-batch-{str(uuid.uuid4())[:8]}"  # Shortened UUID

    # Task 2: Submit PySpark job to Dataproc Serverless
    batch_details = {
        "pyspark_batch": {
            "main_python_file_uri": f"gs://credit-card-data-analysis/spark_job/spark_job.py"
        },
        "runtime_config": {
            "version": "2.2",
        },
        "environment_config": {
            "execution_config": {
                "service_account": "70622048644-compute@developer.gserviceaccount.com",
                "network_uri": "projects/psyched-service-442305-q1/global/networks/default",
                "subnetwork_uri": "projects/psyched-service-442305-q1/regions/us-central1/subnetworks/default",
            }
        },
    }

    pyspark_task = DataprocCreateBatchOperator(
        task_id="run_credit_card_processing_job",
        batch=batch_details,
        batch_id=batch_id,
        project_id="psyched-service-442305-q1",
        region="us-central1",
        gcp_conn_id="google_cloud_default",
    )

    move_files_to_archive = GCSToGCSOperator(
        task_id="move_files_to_archive",
        source_bucket=gcs_bucket,
        source_object=source_prefix,
        destination_bucket=gcs_bucket,
        destination_object=archive_prefix,
        move_object=True,
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )


    file_sensor >> pyspark_task >> move_files_to_archive