import requests
import json
import csv
import logging
from datetime import datetime

# --- Static Configuration ---
API_URL = "https://your.dynatrace.instance/api/v2/metrics"
API_TOKEN = "your_api_token_here"
HEADERS = {
    "Authorization": f"Api-Token {API_TOKEN}"
}

# --- Setup Logging ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"metrics_collection_{timestamp}.log"
logging.basicConfig(filename=f"/mnt/data/{log_filename}", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logging.info("Starting metrics collection script")

# --- Initialize ---
all_metrics = []
params = {
    "pageSize": 500
}

# --- Paging Loop ---
try:
    while True:
        response = requests.get(API_URL, headers=HEADERS, params=params)
        if response.status_code != 200:
            logging.error(f"Failed to fetch metrics: {response.status_code} - {response.text}")
            break

        data = response.json()
        all_metrics.extend(data.get("metrics", []))
        logging.info(f"Retrieved {len(data.get('metrics', []))} metrics (Total so far: {len(all_metrics)})")

        if "nextPageKey" in data:
            params = {
                "nextPageKey": data["nextPageKey"]
            }
        else:
            break

    # --- Save Raw JSON Output ---
    with open("/mnt/data/metrics.json", "w") as json_file:
        json.dump(all_metrics, json_file, indent=2)
        logging.info("Saved metrics to metrics.json")

    # --- Extract metricIds to CSV ---
    with open("/mnt/data/metrics.csv", "w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["metricId"])
        for metric in all_metrics:
            if isinstance(metric, dict) and "metricId" in metric:
                writer.writerow([metric["metricId"]])
            elif isinstance(metric, str):
                writer.writerow([metric])
        logging.info("Saved metricId list to metrics.csv")

except Exception as e:
    logging.exception(f"Script failed with exception: {e}")
