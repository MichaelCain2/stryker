import requests
import json
import csv
import os
from datetime import datetime
import logging

# Setup logging
log_filename = f"dynatrace_metrics_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Prompt user for required inputs
base_url = input("Enter Dynatrace API base URL (e.g., https://your.domain.com): ").strip()
api_token = input("Enter API token: ").strip()

# Create output filenames
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
json_filename = f"metrics_output_{timestamp}.json"
csv_filename = f"metrics_list_{timestamp}.csv"

# Setup headers
headers = {
    "Authorization": f"Api-Token {api_token}"
}

# Initialize request
initial_url = f"{base_url}/api/v2/metrics?pageSize=500&fields=metricId"
metric_ids = []

try:
    response = requests.get(initial_url, headers=headers)
    response.raise_for_status()
    data = response.json()

    # Save first page of JSON response
    with open(json_filename, "w") as json_file:
        json.dump(data, json_file, indent=2)

    # Extract metricIds
    for item in data.get("metrics", []):
        metric_ids.append(item)

    # Handle pagination with nextPageKey
    next_page_key = data.get("nextPageKey")
    while next_page_key:
        next_url = f"{base_url}/api/v2/metrics?nextPageKey={next_page_key}"
        response = requests.get(next_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        for item in data.get("metrics", []):
            metric_ids.append(item)
        next_page_key = data.get("nextPageKey")

    # Write metrics to CSV
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["metricId"])
        for metric in metric_ids:
            writer.writerow([metric])

    logging.info(f"Script completed successfully. Output written to {csv_filename}")

except requests.exceptions.RequestException as e:
    logging.error(f"Request failed: {e}")
except Exception as ex:
    logging.error(f"An error occurred: {ex}")
