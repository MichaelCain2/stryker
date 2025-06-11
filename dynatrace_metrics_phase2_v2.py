import requests
import csv
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import logging
import os

# ========== USER SETUP SECTION ==========
# Replace these values manually before running
api_url = "https://your.domain/e/yourenv"
api_token = "your_api_token_here"
timeframe = "now-1h"
mz_name = "AA-BBB-VASI_1234"
# ========================================

# Set up logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"dynatrace_phase2_{timestamp}.log"
log_filepath = os.path.join(os.getcwd(), log_filename)
logging.basicConfig(filename=log_filepath, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Prompt for CSV file selection
root = tk.Tk()
root.withdraw()
csv_file_path = filedialog.askopenfilename(title="Select CSV File with Metric IDs", filetypes=[("CSV files", "*.csv")])

# Prepare output CSV
output_filename = f"metric_counts_{timestamp}.csv"
with open(output_filename, mode='w', newline='') as output_file:
    writer = csv.writer(output_file)
    writer.writerow(["MetricID", "DataPointCount"])

    # Read the metric IDs from the CSV
    with open(csv_file_path, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            if not row:
                continue
            metric = row[0].strip()
            query_url = f'{api_url}/api/v2/metrics/query?metricSelector={metric}&from={timeframe}&mzSelector=mzName("{mz_name}")'
            headers = {
                "Authorization": f"Api-Token {api_token}"
            }
            try:
                response = requests.get(query_url, headers=headers)
                response.raise_for_status()
                data = response.json()
                count = 0
                for result in data.get("result", []):
                    for dp in result.get("data", []):
                        count += len(dp.get("values", []))
                writer.writerow([metric, count])
                logging.info(f"Processed metric: {metric} - DataPointCount: {count}")
            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching metric {metric}: {e}")

print(f"Done. Output saved to: {output_filename}")
