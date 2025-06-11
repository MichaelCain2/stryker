import requests
import csv
import logging
from datetime import datetime
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilename

# Setup logging
log_filename = f"dynatrace_phase2_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def prompt_user_input():
    url = input("Enter your Dynatrace API URL (e.g., https://your.domain/e/yourenv/api): ").strip()
    token = input("Enter your Dynatrace API Token: ").strip()
    timeframe = input("Enter the start timeframe (e.g., now-1h): ").strip()

    # Open file explorer to select CSV file
    print("Please select the CSV file containing metric IDs.")
    Tk().withdraw()
    csv_path = askopenfilename(title="Select Metric CSV File")

    return url, token, timeframe, csv_path

def query_metric_data(api_url, token, timeframe, csv_file):
    output_csv = f"metric_data_count_20250611_174956.csv"

    with open(csv_file, "r") as file, open(output_csv, "w", newline="") as out_file:
        reader = csv.reader(file)
        writer = csv.writer(out_file)
        writer.writerow(["metricId", "dataPointCount"])

        for row in reader:
            if not row: continue
            metric_id = row[0].strip()
            full_url = f"{api_url}/v2/metrics/query?metricSelector={metric_id}&from={timeframe}"

            headers = {
                "Authorization": f"Api-Token {token}"
            }

            try:
                response = requests.get(full_url, headers=headers)
                response.raise_for_status()
                data = response.json()

                if "result" in data and data["result"]:
                    total_points = 0
                    for item in data["result"]:
                        for ts in item.get("data", []):
                            total_points += len(ts.get("values", []))
                    writer.writerow([metric_id, total_points])
                    logging.info(f"Metric: {metric_id}, Data Points: {total_points}")
                else:
                    writer.writerow([metric_id, 0])
                    logging.warning(f"No data for metric: {metric_id}")
            except Exception as e:
                logging.error(f"Error fetching metricId {metric_id}: {str(e)}")
                writer.writerow([metric_id, "ERROR"])

    print(f"Metric query results saved to: {output_csv}")

if __name__ == "__main__":
    api_url, token, timeframe, csv_file = prompt_user_input()
    query_metric_data(api_url, token, timeframe, csv_file)
