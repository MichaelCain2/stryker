
import requests
import csv
import logging
from datetime import datetime

# Configure logging with an incrementing filename
log_counter = 1
while True:
    log_filename = f"metric_usage_log_{log_counter}.log"
    try:
        with open(log_filename, "x") as f:
            break
    except FileExistsError:
        log_counter += 1

logging.basicConfig(filename=log_filename, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Prompt for required inputs
api_url = input("Enter the Dynatrace API URL (e.g., https://your-environment.com/api/v2/metrics): ").strip()
api_token = input("Enter your Dynatrace API Token: ").strip()
start_time = input("Enter start time (e.g., now-1h): ").strip()
end_time = input("Enter end time (e.g., now): ").strip()

headers = {
    "Authorization": f"Api-Token {api_token}"
}

params = {
    "from": start_time,
    "to": end_time,
    "pageSize": 500
}

metrics_usage = {}

print("Fetching metric usage...")

next_page_key = None
while True:
    if next_page_key:
        response = requests.get(f"{api_url}?nextPageKey={next_page_key}", headers=headers)
    else:
        response = requests.get(api_url, headers=headers, params=params)

    if response.status_code != 200:
        logging.error(f"Failed API call. Status Code: {response.status_code}, Response: {response.text}")
        print("Error fetching data. Check log for details.")
        break

    data = response.json()

    for metric in data.get("metrics", []):
        metrics_usage[metric] = metrics_usage.get(metric, 0) + 1

    next_page_key = data.get("nextPageKey")
    if not next_page_key:
        break

# Save to CSV
csv_filename = f"metric_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
with open(csv_filename, mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Metric Name", "Usage Count"])
    for metric, count in metrics_usage.items():
        writer.writerow([metric, count])

print(f"Metric usage statistics saved to: {csv_filename}")
logging.info(f"Metric usage statistics saved to: {csv_filename}")
