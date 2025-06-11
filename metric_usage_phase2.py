
import requests
import csv
import json
import logging
from datetime import datetime
from tkinter import Tk
from tkinter.filedialog import askopenfilename

# Setup logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"dynatrace_metrics_phase2_{timestamp}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Prompt for required information
api_url = input("Enter Dynatrace API URL (e.g., https://your.domain.com/e/yourenv/api): ").strip()
api_token = input("Enter API Token: ").strip()
start_timeframe = input("Enter Start Timeframe (e.g., now-1h): ").strip()

# Prompt for CSV file using file dialog
Tk().withdraw()
csv_file_path = askopenfilename(title="Select the metrics CSV file", filetypes=[("CSV files", "*.csv")])

if not csv_file_path:
    logging.error("No CSV file selected. Exiting.")
    print("No CSV file selected. Exiting.")
    exit(1)

headers = {
    "Authorization": f"Api-Token {api_token}"
}

output_data = []

with open(csv_file_path, 'r') as csvfile:
    csvreader = csv.reader(csvfile)
    for row in csvreader:
        if not row:
            continue
        metric_selector = row[0].strip()  # FIXED: Actually use value from CSV
        url = f"{api_url}/v2/metrics/query?metricSelector={metric_selector}&from={start_timeframe}"

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Count number of datapoints
            total_count = 0
            for series in data.get("result", []):
                for dp in series.get("data", []):
                    total_count += 1

            output_data.append([metric_selector, total_count])
            logging.info(f"Processed {metric_selector} with {total_count} datapoints")

        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error for {metric_selector}: {http_err}")
        except Exception as err:
            logging.error(f"Error fetching {metric_selector}: {err}")

# Write results to CSV
output_filename = f"metric_datapoint_counts_{timestamp}.csv"
with open(output_filename, 'w', newline='') as f:
    writer = csv.writer(f)
    for entry in output_data:
        writer.writerow(entry)

print(f"Summary written to {output_filename}")
