
import requests
import csv
import json
import logging
from datetime import datetime

# Configure logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"metric_usage_{timestamp}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Prompt for user inputs
API_URL = input("Enter Dynatrace API URL (e.g., https://your.domain.com/api/v2): ").strip()
API_TOKEN = input("Enter API Token: ").strip()
CSV_INPUT_PATH = input("Enter path to input CSV file with metric IDs: ").strip()
FROM_TIME = input("Enter start time (e.g., now-7d): ").strip()
TO_TIME = input("Enter end time (e.g., now): ").strip()

HEADERS = {
    "Authorization": f"Api-Token {API_TOKEN}"
}

output_csv = f"metric_usage_results_{timestamp}.csv"
output_json = f"metric_usage_raw_{timestamp}.json"
all_results = {}

with open(CSV_INPUT_PATH, newline='') as csvfile:
    reader = csv.reader(csvfile)
    metric_ids = [row[0] for row in reader if row]

usage_counts = []

for metric_id in metric_ids:
    try:
        query_url = (
            f"{API_URL}/metrics/query"
            f"?metricSelector={metric_id}"
            f"&from={FROM_TIME}&to={TO_TIME}"
        )
        response = requests.get(query_url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        all_results[metric_id] = data

        # Count non-null values in the response
        values = []
        for result in data.get("result", []):
            for d in result.get("data", []):
                values.extend([v for v in d.get("values", []) if v is not None])

        count = len(values)
        usage_counts.append((metric_id, count))
        logging.info(f"Metric: {metric_id}, Count: {count}")
    except Exception as e:
        logging.error(f"Failed to process metric {metric_id}: {str(e)}")

# Write counts to output CSV
with open(output_csv, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["metricId", "data_point_count"])
    writer.writerows(usage_counts)

# Write raw JSON output
with open(output_json, "w") as f:
    json.dump(all_results, f, indent=2)

print(f"Metric usage written to: {output_csv}")
print(f"Raw JSON saved to: {output_json}")
print(f"Log file: {log_filename}")
