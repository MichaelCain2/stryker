import requests
import csv
import json
import logging
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, simpledialog

def fetch_metrics(api_url, headers, metric, mz_selector, agg_time):
    """
    Fetch metrics from the Dynatrace API.
    """
    query_url = f'{api_url}?metricSelector={metric}&from={agg_time}&entitySelector=type("HOST")&mzSelector=mzName("{mz_selector}")'
    logging.debug(f"Fetching metrics with URL: {query_url}")
    response = requests.get(query_url, headers=headers)
    response.raise_for_status()
    return response.json()

def main():
    # Setup logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"metrics_phase2_log_{timestamp}.log"
    logging.basicConfig(filename=os.path.join("/mnt/data", log_filename), level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("Starting Dynatrace Metrics Phase 2 Script")

    # Tkinter root setup for dialogs
    root = tk.Tk()
    root.withdraw()

    # Prompt user for necessary inputs
    api_url = simpledialog.askstring("API URL", "Enter the full Dynatrace API URL (e.g., https://your.env/e/your_id/api/v2/metrics/query):")
    api_token = simpledialog.askstring("API Token", "Enter your Dynatrace API token:", show='*')
    agg_time = simpledialog.askstring("Aggregation Time", "Enter the start timeframe (e.g., now-1h, now-1d, now-7d):")
    mz_selector = simpledialog.askstring("Management Zone", "Enter the Management Zone name exactly as defined in Dynatrace:")
    csv_file_path = filedialog.askopenfilename(title="Select the CSV file with metrics", filetypes=[("CSV files", "*.csv")])

    headers = {
        "Authorization": f"Api-Token {api_token}",
        "Content-Type": "application/json"
    }

    metrics_counts = []

    try:
        with open(csv_file_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                metric = row[0].strip()
                try:
                    data = fetch_metrics(api_url, headers, metric, mz_selector, agg_time)
                    count = sum(len(series.get("data", [])) for series in data.get("result", [{}])[0].get("data", []))
                    metrics_counts.append({"metricId": metric, "count": count})
                    logging.info(f"Metric {metric} has {count} datapoints.")
                except Exception as e:
                    logging.error(f"Error fetching metric {metric}: {e}")
    except Exception as e:
        logging.error(f"Error reading CSV: {e}")

    # Output results to CSV
    output_csv_path = os.path.join("/mnt/data", f"{base_filename}_results.csv")
    try:
        with open(output_csv_path, mode='w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["metricId", "count"])
            writer.writeheader()
            for entry in metrics_counts:
                writer.writerow(entry)
        logging.info(f"Metrics summary written to {output_csv_path}")
    except Exception as e:
        logging.error(f"Error writing output CSV: {e}")

if __name__ == "__main__":
    main()
