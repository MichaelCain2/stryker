import requests
import csv
import json
import logging
from datetime import datetime
from tkinter import Tk
from tkinter.filedialog import askopenfilename

# Setup logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"metric_count_log_{timestamp}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Prompt for CSV file
Tk().withdraw()
csv_file_path = askopenfilename(title="Select CSV file with metric IDs", filetypes=[("CSV files", "*.csv")])
if not csv_file_path:
    print("No file selected. Exiting.")
    exit()

# Prompt for Dynatrace API details
api_url = input("Enter your Dynatrace API base URL (e.g., https://your.domain/e/yourenv/api): ").strip().rstrip("/")
api_token = input("Enter your Dynatrace API token: ").strip()
timeframe = input("Enter the timeframe (e.g., now-1h, now-7d): ").strip()

headers = {
    "Authorization": f"Api-Token {api_token}",
    "Content-Type": "application/json"
}

# Prepare output filenames
base_filename = os.path.splitext(os.path.basename(csv_file_path))[0]
output_json = f"{base_filename}_counts_{timestamp}.json"
output_csv = f"{base_filename}_counts_{timestamp}.csv"

results = {}

# Read metric IDs from CSV
with open(csv_file_path, "r") as f:
    metric_ids = [line.strip() for line in f if line.strip()]

# Fetch data for each metric
for metric_id in metric_ids:
    try:
        query_url = f"{api_url}/v2/metrics/query?metricId={metric_id}&resolution=Inf&from={timeframe}"
        response = requests.get(query_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        count = sum(len(series["data"]) for result in data.get("result", []) for series in result.get("data", []))
        results[metric_id] = count
        logging.info(f"Fetched {count} datapoints for {metric_id}")
    except Exception as e:
        logging.error(f"Error fetching {metric_id}: {e}")

# Save results to JSON
with open(output_json, "w") as jf:
    json.dump(results, jf, indent=2)

# Save results to CSV
with open(output_csv, "w", newline="") as cf:
    writer = csv.writer(cf)
    for metric_id, count in results.items():
        writer.writerow([metric_id, count])

print(f"JSON output saved to: {output_json}")
print(f"CSV output saved to: {output_csv}")
print(f"Log file created: {log_filename}")
