# Make sure these libraries are installed
# pip install pytest
# pip install pyspark

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit, to_timestamp, round
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, BooleanType, TimestampType, IntegerType

@pytest.fixture(scope="module")
def spark():
    """Initialize a Spark Session for Testing."""
    spark = SparkSession.builder \
        .appName("PySparkUnitTest") \
        .master("local[*]") \
        .getOrCreate()
    return spark

def test_transactions_processing(spark):
    """Test transaction processing logic"""

    # 1. Define Sample Transactions Data
    transactions_schema = StructType([
        StructField("transaction_id", StringType(), False),
        StructField("cardholder_id", StringType(), False),
        StructField("merchant_id", StringType(), False),
        StructField("merchant_name", StringType(), False),
        StructField("merchant_category", StringType(), False),
        StructField("transaction_amount", DoubleType(), False),
        StructField("transaction_currency", StringType(), False),
        StructField("transaction_timestamp", StringType(), False),
        StructField("transaction_status", StringType(), False),
        StructField("fraud_flag", BooleanType(), False),
        StructField("device_type", StringType(), False),
        StructField("merchant_location", StringType(), False)
    ])

    transactions_data = [
        ("T001", "CH001", "M001", "Walmart", "Groceries", 120.50, "USD", "2025-02-04T10:00:00Z", "SUCCESS", False, "Mobile", "New York, USA"),
        ("T002", "CH002", "M002", "Expedia", "Travel", 9500.75, "USD", "2025-02-04T12:30:00Z", "PENDING", True, "Web", "Toronto, Canada"),
        ("T003", "CH003", "M003", "Amazon", "Shopping", 75.20, "USD", "2025-02-04T15:45:00Z", "FAILED", False, "Web", "San Francisco, USA"),
    ]

    transactions_df = spark.createDataFrame(transactions_data, schema=transactions_schema)

    # 2. Define Sample Cardholders Data
    cardholders_schema = StructType([
        StructField("cardholder_id", StringType(), False),
        StructField("customer_name", StringType(), False),
        StructField("reward_points", IntegerType(), False),
        StructField("risk_score", DoubleType(), False),
    ])

    cardholders_data = [
        ("CH001", "John Doe", 4500, 0.15),
        ("CH002", "Jane Smith", 1200, 0.35),
        ("CH003", "Ali Khan", 8000, 0.10),
    ]

    cardholders_df = spark.createDataFrame(cardholders_data, schema=cardholders_schema)

    # 3. Apply Data Transformations (Simulating Production Logic)
    transactions_df = transactions_df.withColumn(
        "transaction_category",
        when(col("transaction_amount") <= 100, lit("Low"))
        .when((col("transaction_amount") > 100) & (col("transaction_amount") <= 500), lit("Medium"))
        .otherwise(lit("High"))
    ).withColumn(
        "transaction_timestamp", to_timestamp(col("transaction_timestamp"))
    ).withColumn(
        "high_risk", (col("fraud_flag") == True) | (col("transaction_amount") > 10000) | (col("transaction_category") == "High")
    )

    # 4. Perform Join (Simulating Enrichment with Cardholders Data)
    enriched_df = transactions_df.join(cardholders_df, on="cardholder_id", how="left")

    # 5. Update Reward Points (Earn 1 point per $10 spent)
    enriched_df = enriched_df.withColumn(
        "updated_reward_points", col("reward_points") + round(col("transaction_amount") / 10)
    )

    # 6. Calculate Fraud Risk Level
    enriched_df = enriched_df.withColumn(
        "fraud_risk_level",
        when(col("high_risk") == True, lit("Critical"))
        .when((col("risk_score") > 0.3) | (col("fraud_flag") == True), lit("High"))
        .otherwise(lit("Low"))
    )

    # 7. Assertions: Verify Transformations
    result = enriched_df.select("transaction_id", "transaction_category", "high_risk", "fraud_risk_level", "updated_reward_points").collect()

    assert result[0]["transaction_category"] == "Medium"  # T001 (120.50 USD)
    assert result[1]["transaction_category"] == "High"    # T002 (9500.75 USD)
    assert result[2]["transaction_category"] == "Low"     # T003 (75.20 USD)

    assert result[0]["high_risk"] == False
    assert result[1]["high_risk"] == True  # Fraud flag is True
    assert result[2]["high_risk"] == False

    assert result[0]["fraud_risk_level"] == "Low"
    # assert result[1]["fraud_risk_level"] == "High"
    assert result[1]["fraud_risk_level"] == "Critical"
    assert result[2]["fraud_risk_level"] == "Low"

    assert result[0]["updated_reward_points"] == 4512  # 4500 + (120.50 / 10)
    # assert result[1]["updated_reward_points"] == 2195  # 1200 + (9500.75 / 10)
    assert result[1]["updated_reward_points"] == 2150  # 1200 + (9500.75 / 10)
    assert result[2]["updated_reward_points"] == 8008  # 8000 + (75.20 / 10)

    print("All Unit Tests Passed!")