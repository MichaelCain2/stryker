import os
import json
import csv
import logging
import requests
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

# Timestamp for unique file names
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Setup logging
log_filename = f"metric_data_fetch_{timestamp}.log"
logging.basicConfig(
    filename=f"metric_data_fetch_{timestamp}.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Prompt user to select CSV file using file dialog
def select_csv_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select the CSV file with metric IDs",
        filetypes=[("CSV files", "*.csv")]
    )
    return file_path

# Read metric IDs from CSV
def read_metric_ids(file_path):
    try:
        with open(file_path, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        logging.error(f"Failed to read CSV: {e}")
        return []

# Prompt for user inputs
def get_user_inputs():
    api_url = input("Enter Dynatrace API URL (base, not including /metrics): ").strip()
    token = input("Enter API Token: ").strip()
    start_time = input("Enter start timeframe (e.g., now-1h): ").strip()
    end_time = input("Enter end timeframe (e.g., now): ").strip()
    return api_url, token, start_time, end_time

# Fetch metric usage
def fetch_metric_counts(api_url, token, metrics, start, end):
    headers = {"Authorization": f"Api-Token {token}"}
    metric_data = {}

    for metric_id in metrics:
        params = {
            "metricSelector": metric_id,
            "resolution": "Inf",
            "from": start,
            "to": end,
        }

        try:
            response = requests.get(f"{api_url}/metrics/query", headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            try:
                count = sum(len(series["data"]) for series in data["result"][0]["data"])
            except Exception:
                count = 0

            metric_data[metric_id] = count
            logging.info(f"Metric {metric_id} has {count} data points.")

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching {metric_id}: {e}")
            metric_data[metric_id] = 0

    return metric_data

# Write output to files
def write_outputs(metric_data):
    json_file = f"metric_counts_{timestamp}.json"
    csv_file = f"metric_counts_{timestamp}.csv"

    try:
        with open(json_file, "w") as jf:
            json.dump(metric_data, jf, indent=2)
        logging.info(f"JSON output written to {json_file}")

        with open(csv_file, "w", newline="") as cf:
            writer = csv.writer(cf)
            for metric_id, count in metric_data.items():
                writer.writerow([metric_id, count])
        logging.info(f"CSV output written to {csv_file}")
    except Exception as e:
        logging.error(f"Failed to write output files: {e}")

def main():
    csv_path = select_csv_file()
    if not os.path.exists(csv_path):
        logging.error("CSV file not found.")
        return

    metrics = read_metric_ids(csv_path)
    if not metrics:
        logging.error("No metric IDs loaded.")
        return

    api_url, token, start, end = get_user_inputs()
    results = fetch_metric_counts(api_url, token, metrics, start, end)
    write_outputs(results)

if __name__ == "__main__":
    main()
