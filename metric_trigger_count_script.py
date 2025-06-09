import requests
import csv
import logging
from datetime import datetime

# Setup logging with sequential filename
def get_next_log_filename(base_name):
    index = 1
    while True:
        filename = f"{base_name}_{index}.log"
        if not os.path.exists(filename):
            return filename
        index += 1

log_filename = get_next_log_filename("MetricUsageSummary")
logging.basicConfig(filename=log_filename, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Prompt user for input
api_url = input("Enter Dynatrace API URL (e.g., https://yourdomain/e/yourenv/api/v2/metrics/usage): ").strip()
api_token = input("Enter Dynatrace API Token: ").strip()
from_time = input("Enter start timeframe (e.g., now-2h): ").strip()
to_time = input("Enter end timeframe (e.g., now): ").strip()

headers = {
    "Authorization": f"Api-Token {api_token}",
    "Accept": "application/json"
}

params = {
    "from": from_time,
    "to": to_time,
    "pageSize": 500
}

metrics = []

try:
    response = requests.get(api_url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()

    # Collect metrics from first page
    if "metrics" in data:
        metrics.extend(data["metrics"])

    # Handle pagination
    while "nextPageKey" in data:
        logging.info("Fetching next page of data...")
        next_params = {
            "nextPageKey": data["nextPageKey"]
        }
        response = requests.get(api_url, headers=headers, params=next_params)
        response.raise_for_status()
        data = response.json()
        if "metrics" in data:
            metrics.extend(data["metrics"])

    # Write to CSV
    csv_filename = f"MetricUsageSummary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Metric ID", "Count"])
        for metric in metrics:
            writer.writerow([metric.get("metricId", ""), metric.get("count", 0)])

    logging.info(f"Summary written to {csv_filename}")
    print(f"Summary written to {csv_filename}")

except Exception as e:
    logging.error(f"An error occurred: {e}")
    print(f"Error: {e}")
