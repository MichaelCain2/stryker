
import requests
import csv
import json
import logging
from datetime import datetime

# Configure logging
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_filename = f"metrics2csv_v3_log_{timestamp}.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Configuration
API_URL = "https://your-dynatrace-url.com/api/v2/metrics"
API_TOKEN = "your-api-token"

HEADERS = {
    "Authorization": f"Api-Token {API_TOKEN}",
    "Content-Type": "application/json"
}

# Query parameters
params = {
    "pageSize": 500,
    "fields": "displayName",
    "writtenSince": "now-1w"
}

all_metrics = []
try:
    logging.info("Starting API call to fetch metrics")
    response = requests.get(API_URL, headers=HEADERS, params=params)
    response.raise_for_status()
    data = response.json()

    # Store initial set of metrics
    all_metrics.extend(data.get("metrics", []))

    # Handle pagination
    next_page_key = data.get("nextPageKey")
    while next_page_key:
        logging.info(f"Fetching next page using nextPageKey: {next_page_key}")
        next_url = f"{API_URL}?nextPageKey={next_page_key}"
        response = requests.get(next_url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        all_metrics.extend(data.get("metrics", []))
        next_page_key = data.get("nextPageKey")

except requests.exceptions.RequestException as e:
    logging.error(f"Request failed: {e}")
except json.JSONDecodeError as e:
    logging.error(f"JSON decode error: {e}")
except Exception as e:
    logging.error(f"Unexpected error: {e}")

# Write to CSV
csv_filename = f"metrics2csv_v3_output_{timestamp}.csv"
try:
    with open(csv_filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        for metric in all_metrics:
            metric_id = metric.get("metricId", "")
            if metric_id:
                writer.writerow([metric_id])
    logging.info(f"Metric IDs successfully written to {csv_filename}")
except Exception as e:
    logging.error(f"Failed to write CSV: {e}")
