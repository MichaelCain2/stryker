import requests
import csv
import logging
from datetime import datetime
from tkinter import Tk
from tkinter.filedialog import askopenfilename

# Configure logging
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_filename = f"dynatrace_metrics_phase2_{timestamp}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Prompt user for API URL, token, timeframe, and Management Zone
api_url = input("Enter Dynatrace API URL (e.g., https://your-domain/api/v2/metrics/query): ").strip()
api_token = input("Enter Dynatrace API Token: ").strip()
timeframe = input("Enter the start of the timeframe (e.g., now-1h): ").strip()
management_zone = input("Enter the Management Zone name (or leave blank if none): ").strip()

# File selection dialog
print("Please select the CSV file containing metricIds:")
Tk().withdraw()
csv_file_path = askopenfilename(filetypes=[("CSV Files", "*.csv")])

# Read metrics from the CSV file
with open(csv_file_path, 'r') as f:
    metrics = [line.strip() for line in f if line.strip()]

# Process each metric
results = []
headers = {"Authorization": f"Api-Token {api_token}"}

for metric_id in metrics:
    try:
        # Build the URL with optional Management Zone
    query_url = f"{api_url}/api/v2/metrics/query?metricSelector={metric}&from={start_time}&mzSelector=mzName(\"{management_zone}\")"
        if management_zone:
            query_url += f"&mzSelector=mzName("{management_zone}")"

        response = requests.get(query_url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Count the number of data points
        data_count = 0
        for result in data.get('result', []):
            for series in result.get('data', []):
                values = series.get('values', [])
                data_count += len([v for v in values if v is not None])

        logging.info(f"Fetched data for metric: {metric_id} with {data_count} values")
        results.append((metric_id, data_count))

    except Exception as e:
        logging.error(f"Error fetching metricId {metric_id}: {e}")
        results.append((metric_id, "ERROR"))

# Write summary to CSV
output_csv = f"metric_data_counts_{timestamp}.csv"
with open(output_csv, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["MetricId", "DataPointCount"])
    writer.writerows(results)

logging.info(f"Summary written to {output_csv}")
print(f"Script completed. Results saved to {output_csv} and log file to {log_filename}")
