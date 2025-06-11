import requests
import json
import csv
import logging
from datetime import datetime
import os

# === SET THESE BEFORE RUNNING ===
API_URL = "https://your.dynatrace.instance/api/v2/metrics"
API_TOKEN = "your_api_token_here"
OUTPUT_JSON = "dynatrace_metrics.json"
OUTPUT_CSV = "dynatrace_metrics.csv"
# ================================

# Logging Setup
log_filename = f"dynatrace_metric_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_path = os.path.join(os.getcwd(), log_filename)
logging.basicConfig(filename=log_path, level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

HEADERS = {
    "Authorization": f"Api-Token {API_TOKEN}",
    "Content-Type": "application/json"
}

all_metrics = []
next_page_key = None

try:
    while True:
        if next_page_key:
            url = f"{API_URL}?nextPageKey={next_page_key}"
        else:
            url = f"{API_URL}?pageSize=500"

        logging.debug(f"Requesting: {url}")
        response = requests.get(url, headers=HEADERS)

        if response.status_code != 200:
            logging.error(f"Error {response.status_code}: {response.text}")
            break

        data = response.json()
        all_metrics.extend(data.get("metrics", []))
        next_page_key = data.get("nextPageKey")
        if not next_page_key:
            break

    # Write raw output to JSON
    with open(OUTPUT_JSON, "w") as f_json:
        json.dump(all_metrics, f_json, indent=2)
    logging.info(f"Full JSON written to {OUTPUT_JSON}")

    # Write clean metricIds to CSV
    with open(OUTPUT_CSV, "w", newline="") as f_csv:
        writer = csv.writer(f_csv)
        writer.writerow(["metricId"])
        for item in all_metrics:
            if isinstance(item, str):
                writer.writerow([item])
    logging.info(f"Metric IDs written to {OUTPUT_CSV}")

except Exception as e:
    logging.exception("Unhandled error occurred:")
