
import requests
import csv
import logging
from datetime import datetime

# Setup logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"metric_list_{timestamp}.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Prompt for inputs
api_url_base = input("Enter the base Dynatrace API URL (e.g., https://your-domain.com): ").strip()
api_token = input("Enter your Dynatrace API token: ").strip()
start_timeframe = input("Enter the start timeframe (e.g., now-1w): ").strip()

# Construct API URL with parameters
params = {
    "pageSize": 500,
    "fields": "displayName",
    "writtenSince": start_timeframe
}

headers = {
    "Authorization": f"Api-Token {api_token}",
    "Content-Type": "application/json"
}

api_url = f"{api_url_base}/api/v2/metrics"
all_metrics = []

try:
    while True:
        response = requests.get(api_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        for metric in data.get("metrics", []):
            metric_id = metric.get("metricId")
            if metric_id:
                all_metrics.append([metric_id])

        if "nextPageKey" in data:
            api_url = f"{api_url_base}/api/v2/metrics"
            params = {
                "nextPageKey": data["nextPageKey"]
            }
        else:
            break

    csv_filename = f"available_metrics_{timestamp}.csv"
    with open(csv_filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Metric ID"])
        writer.writerows(all_metrics)

    logging.info(f"Successfully written {len(all_metrics)} metrics to {csv_filename}")
    print(f"Metric list written to {csv_filename}")

except requests.RequestException as e:
    logging.error(f"API request failed: {e}")
    print(f"API request failed: {e}")

except Exception as e:
    logging.error(f"Unexpected error: {e}")
    print(f"Unexpected error: {e}")
