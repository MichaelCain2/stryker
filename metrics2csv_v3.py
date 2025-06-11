import requests
import json
import csv
import logging
from datetime import datetime

# Set timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Log file setup
log_filename = f"dynatrace_metrics_{timestamp}.log"
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# CONFIGURATION - set manually
API_URL = "https://your-dynatrace-environment.com/api/v2/metrics"
API_TOKEN = "your_api_token_here"
HEADERS = {"Authorization": f"Api-Token {API_TOKEN}"}

# Output files
json_filename = f"dynatrace_metrics_{timestamp}.json"
csv_filename = f"dynatrace_metrics_{timestamp}.csv"

def fetch_all_metrics():
    metrics = []
    next_page_key = None
    base_url = f"{API_URL}?pageSize=500"

    while True:
        url = f"{base_url}" if not next_page_key else f"{API_URL}?nextPageKey={next_page_key}"
        logging.info(f"Requesting URL: {url}")
        response = requests.get(url, headers=HEADERS)

        if response.status_code != 200:
            logging.error(f"Failed to fetch data: {response.status_code}")
            break

        data = response.json()
        metrics.extend(data.get("metrics", []))
        next_page_key = data.get("nextPageKey")

        if not next_page_key:
            break

    return metrics

def save_metrics_to_json(metrics):
    with open(json_filename, "w") as json_file:
        json.dump(metrics, json_file, indent=2)
    logging.info(f"Saved {len(metrics)} metrics to JSON file: {json_filename}")

def save_metric_ids_to_csv(metrics):
    with open(csv_filename, mode="w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        for metric in metrics:
            if isinstance(metric, dict):
                metric_id = metric.get("metricId", "")
                writer.writerow([metric_id])
            elif isinstance(metric, str):
                writer.writerow([metric])
    logging.info(f"Metric IDs written to CSV file: {csv_filename}")

if __name__ == "__main__":
    logging.info("Starting Dynatrace metric export process...")
    all_metrics = fetch_all_metrics()
    save_metrics_to_json(all_metrics)
    save_metric_ids_to_csv(all_metrics)
    logging.info("Export complete.")
