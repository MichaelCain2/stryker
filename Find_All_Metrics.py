import requests
import csv
import logging
from datetime import datetime

# === Configuration ===
API_URL = "https://your-environment-url/api/v2/metrics"
API_TOKEN = "your-api-token"

# === Logging Setup ===
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"metric_list_{timestamp}.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

headers = {
    "Authorization": f"Api-Token {API_TOKEN}",
    "Content-Type": "application/json"
}

params = {"pageSize": 100}
all_metrics = []

try:
    while True:
        response = requests.get(API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        for metric in data.get("metrics", []):
            all_metrics.append([metric])

        if "nextPageKey" in data:
            params["nextPageKey"] = data["nextPageKey"]
        else:
            break

    csv_filename = f"available_metrics_{timestamp}.csv"
    with open(csv_filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Metric Key"])
        writer.writerows(all_metrics)

    logging.info(f"Successfully written {len(all_metrics)} metrics to {csv_filename}")
    print(f"Metric list written to {csv_filename}")

except requests.RequestException as e:
    logging.error(f"API request failed: {e}")
    print(f"API request failed: {e}")

except Exception as e:
    logging.error(f"Unexpected error: {e}")
    print(f"Unexpected error: {e}")
