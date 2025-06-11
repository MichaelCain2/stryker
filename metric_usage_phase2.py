
import requests
import csv
import json
import logging
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from datetime import datetime

# Configure logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
base_filename = f"dynatrace_metrics_phase2_{timestamp}"
log_filename = f"{base_filename}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def prompt_file_selection():
    Tk().withdraw()
    filepath = askopenfilename(title="Select the metrics CSV file")
    return filepath

def read_metrics_from_csv(csv_path):
    with open(csv_path, newline='') as csvfile:
        return [row[0].strip() for row in csv.reader(csvfile) if row]

def query_metric_count(api_url, token, metric_id, resolution, from_time):
    headers = {"Authorization": f"Api-Token {token}"}
    query_url = f"{api_url}/metrics/query?metricSelector={metric_id}&resolution={resolution}&from={from_time}"
    try:
        response = requests.get(query_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Successfully fetched metricId: {metric_id}")
        return len(data.get("result", [])[0].get("data", [])) if data.get("result") else 0
    except requests.RequestException as e:
        logging.error(f"Error fetching metricId: {metric_id} -> {e}")
        return 0

def main():
    api_url = input("Enter Dynatrace API base URL (e.g., https://your.domain.com/e/xxxxx/api/v2): ").strip()
    token = input("Enter your Dynatrace API token: ").strip()
    from_time = input("Enter the start timeframe (e.g., now-1h, now-1d, etc.): ").strip()
    resolution = input("Enter resolution (e.g., 1m, 1h, 1d): ").strip()

    csv_path = prompt_file_selection()
    metric_ids = read_metrics_from_csv(csv_path)

    summary = []
    full_json = {}

    for metric_id in metric_ids:
        count = query_metric_count(api_url, token, metric_id, resolution, from_time)
        summary.append([metric_id, count])
        full_json[metric_id] = {"count": count}

    json_filename = f"{base_filename}.json"
    csv_filename = f"{base_filename}.csv"

    with open(json_filename, "w") as json_file:
        json.dump(full_json, json_file, indent=4)

    with open(csv_filename, "w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Metric ID", "Data Point Count"])
        writer.writerows(summary)

    logging.info(f"Output written to {csv_filename} and {json_filename}")

if __name__ == "__main__":
    main()
