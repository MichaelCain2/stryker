import requests
import json
import csv
import logging
from datetime import datetime

# === CONFIGURATION ===
API_URL = "https://your-dynatrace-url.com/api/v2/metrics"
API_TOKEN = "your_api_token_here"

# === SETUP LOGGING ===
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"metrics_query_{timestamp}.log"
logging.basicConfig(
    filename=log_filename,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# === HEADERS FOR API REQUEST ===
headers = {
    "Authorization": f"Api-Token {API_TOKEN}"
}

# === INITIALIZE ===
metrics = []
params = {
    "pageSize": 500
}

try:
    response = requests.get(API_URL, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    metrics.extend(data.get("metrics", []))
    logging.info(f"Fetched {len(data.get('metrics', []))} metrics on first page.")

    # Write first page to JSON
    json_filename = f"metrics_raw_{timestamp}.json"
    with open(json_filename, "w") as jf:
        json.dump(data, jf, indent=2)

    # Handle nextPageKey pagination
    while "nextPageKey" in data:
        next_key = data["nextPageKey"]
        next_params = {"nextPageKey": next_key}
        response = requests.get(API_URL, headers=headers, params=next_params)
        response.raise_for_status()
        data = response.json()
        metrics.extend(data.get("metrics", []))
        logging.info(f"Fetched {len(data.get('metrics', []))} more metrics.")

    # Save only metricId to CSV
    csv_filename = f"metrics_ids_{timestamp}.csv"
    with open(csv_filename, "w", newline="") as cf:
        writer = csv.writer(cf)
        for metric in metrics:
            metric_id = metric.get("metricId", "").strip()
            if metric_id:
                writer.writerow([metric_id])
    logging.info(f"Successfully wrote {len(metrics)} metric IDs to CSV.")

except requests.exceptions.RequestException as e:
    logging.error(f"API request failed: {str(e)}")
except Exception as ex:
    logging.error(f"An error occurred: {str(ex)}")
