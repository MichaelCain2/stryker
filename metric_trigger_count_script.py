
import requests
import logging
from datetime import datetime
from urllib.parse import quote
import csv
import os

# Generate unique log filename
def get_log_filename(base_name="metrics_trigger_log"):
    counter = 1
    while True:
        filename = f"{base_name}_{counter}.log"
        if not os.path.exists(filename):
            return filename
        counter += 1

# Configure logging
log_filename = get_log_filename()
logging.basicConfig(
    filename=log_filename,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def main():
    try:
        base_url = input("Enter Dynatrace API base URL (e.g., https://yourdomain.com/api/v2): ").strip()
        api_token = input("Enter Dynatrace API token: ").strip()
        timeframe = input("Enter timeframe (e.g., now-1h or now-1d): ").strip()

        headers = {
            "Authorization": f"Api-Token {api_token}",
            "Accept": "application/json"
        }

        # Placeholder metricSelector. Replace or allow user input for dynamic selection if needed
        query_url = f"{base_url}/metrics/query?metricSelector=builtin%3Ahost.cpu.usage&from={quote(timeframe)}"

        logging.info(f"Querying: {query_url}")
        response = requests.get(query_url, headers=headers)

        if response.status_code != 200:
            logging.error(f"Failed to fetch data: {response.status_code} {response.text}")
            print("API request failed. Check log for details.")
            return

        data = response.json()

        # Extract time series counts per metric
        metrics_summary = []
        for result in data.get("result", []):
            metric_id = result.get("metricId", "Unknown")
            datapoints_count = 0
            for series in result.get("data", []):
                datapoints_count += len(series.get("values", []))
            metrics_summary.append({
                "Metric Key": metric_id,
                "Times Triggered": datapoints_count
            })

        # Write output to CSV
        output_filename = "metric_triggers_summary.csv"
        with open(output_filename, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["Metric Key", "Times Triggered"])
            writer.writeheader()
            writer.writerows(metrics_summary)

        logging.info(f"Summary written to {output_filename}")
        print(f"CSV report generated: {output_filename}")

    except Exception as e:
        logging.exception("Script failed with an exception")
        print("An error occurred. Check log for details.")

main()
