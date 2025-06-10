import requests
import json
import csv
import time
from datetime import datetime
import os
import logging

# Setup logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"dynatrace_metrics_query_{timestamp}.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# REPLACE with your values
api_url = "https://your.dynatrace.instance/api"  # ← Change this
api_token = "dt0c01.XXXXXXXXXXXXXXXXXXXXXXXX"     # ← And this

# Initial setup
headers = {
    "Authorization": f"Api-Token {api_token}",
    "Content-Type": "application/json"
}

base_url = f"{api_url}/v2/metrics?pageSize=500&fields=metricId"

all_metrics = []
next_page_key = None

while True:
    try:
        url = base_url if not next_page_key else f"{api_url}/v2/metrics?nextPageKey={next_page_key}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()
        all_metrics.extend(data.get("metrics", []))
        next_page_key = data.get("nextPageKey", None)

        if not next_page_key:
            break

    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        break

# Save to JSON
json_filename = f"dynatrace_metrics_{timestamp}.json"
with open(json_filename, "w") as json_file:
    json.dump(all_metrics, json_file, indent=4)
    logging.info(f"Saved JSON output to {json_filename}")

# Extract metricIds and save to CSV
csv_filename = f"dynatrace_metrics_{timestamp}.csv"
with open(csv_filename, "w", newline="") as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow([metric['metricId'].replace(\"{'metricId': '\", '').replace(\"'}\", '')])
    for metric in all_metrics:
        writer.writerow([metric['metricId'].replace(\"{'metricId': '\", '').replace(\"'}\", '')])
    logging.info(f"Saved CSV output to {csv_filename}")