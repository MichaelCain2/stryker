import requests
import json
import csv
import time
from datetime import datetime
import logging
import os

# Logging setup with rotating file names
log_dir = "./"
existing_logs = [f for f in os.listdir(log_dir) if f.startswith("metrics2csv_") and f.endswith(".log")]
log_count = len(existing_logs) + 1
log_filename = os.path.join(log_dir, f"metrics2csv_{log_count}.log")

logging.basicConfig(
    filename=log_filename,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# User inputs
api_url = input("Enter Dynatrace API URL (e.g., https://yourdomain.com/api/v2/metrics): ").strip()
api_token = input("Enter Dynatrace API Token: ").strip()

headers = {
    "Authorization": f"Api-Token {api_token}"
}

params = {
    "pageSize": 500,
    "fields": "displayName",
    "writtenSince": "now-1w"
}

all_metrics = []

try:
    response = requests.get(api_url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    all_metrics.extend(data.get("metrics", []))
    logging.info("Initial batch fetched successfully.")

    # Handle nextPageKey
    while "nextPageKey" in data:
        next_key = data["nextPageKey"]
        next_response = requests.get(f"{api_url}?nextPageKey={next_key}", headers=headers)
        next_response.raise_for_status()
        data = next_response.json()
        all_metrics.extend(data.get("metrics", []))
        logging.info(f"Fetched page with nextPageKey: {next_key}")

except requests.exceptions.RequestException as e:
    logging.error(f"Error fetching metrics: {e}")
    print("Error during API request. Check log for details.")
    exit(1)

# Write metricId values to CSV, stripped clean
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_filename = f"metric_ids_{timestamp}.csv"
try:
    with open(csv_filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        for metric in all_metrics:
            metric_id = metric.get("metricId", "")
            if metric_id:
                cleaned = metric_id.strip()
                writer.writerow([cleaned])
    logging.info(f"Metrics successfully written to {csv_filename}")
    print(f"Success! {len(all_metrics)} metrics written to {csv_filename}")
except Exception as e:
    logging.error(f"Error writing to CSV: {e}")
    print("Error during CSV writing. Check log for details.")
