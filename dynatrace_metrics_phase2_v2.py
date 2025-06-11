import requests
import csv
import json
import os
import logging
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

# Logging Setup
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_filename = f"dynatrace_metrics_phase2_{timestamp}.log"
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Prompt for user inputs
base_url = input("Enter Dynatrace base URL (e.g., https://your.domain/e/ENV_ID): ").strip()
api_token = input("Enter Dynatrace API Token: ").strip()
timeframe = input("Enter timeframe (e.g., now-1h): ").strip()
mz_name = input("Enter Management Zone name exactly as it appears (case-sensitive): ").strip()

# GUI file picker for CSV
root = tk.Tk()
root.withdraw()
csv_file_path = filedialog.askopenfilename(title="Select the CSV file with metricIds", filetypes=[("CSV files", "*.csv")])

if not csv_file_path:
    print("No CSV file selected. Exiting.")
    exit()

# Read metricIds from CSV
with open(csv_file_path, 'r') as csvfile:
    reader = csv.reader(csvfile)
    metrics = [row[0].strip() for row in reader if row]

# Prepare output files
output_json = f"metrics_raw_{timestamp}.json"
output_csv = f"metrics_summary_{timestamp}.csv"

summary_data = []

# Process each metric
for metric in metrics:
    try:
        query_url = (
            f"{base_url}/api/v2/metrics/query"
            f"?metricSelector={metric}"
            f"&from={timeframe}"
            f"&mzSelector=mzName(\"{mz_name}\")"
        )

        headers = {
            "Authorization": f"Api-Token {api_token}"
        }

        response = requests.get(query_url, headers=headers)
        response.raise_for_status()

        data = response.json()
        logging.info(f"Fetched data for metric: {metric}")

        # Write to JSON file (append mode)
        with open(output_json, 'a') as jsonfile:
            json.dump({metric: data}, jsonfile)
            jsonfile.write('\n')

        # Count data points in the time series
        count = 0
        for series in data.get("result", []):
            for datapoint in series.get("data", []):
                count += len(datapoint[1:])  # counting data points

        summary_data.append([metric, count])

    except Exception as e:
        logging.error(f"Error fetching metric {metric}: {str(e)}")
        summary_data.append([metric, "ERROR"])

# Write summary to CSV
with open(output_csv, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["MetricId", "DataPointCount"])
    writer.writerows(summary_data)

print(f"Summary written to {output_csv}")
print(f"Raw JSON data written to {output_json}")
print(f"Log written to {log_filename}")
