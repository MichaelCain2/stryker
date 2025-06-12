import requests
import csv
import json
import logging
import os
from datetime import datetime
from tkinter import Tk, filedialog

def setup_logging(log_filename):
    logging.basicConfig(
        filename=log_filename,
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

def prompt_for_file():
    root = Tk()
    root.withdraw()
    filepath = filedialog.askopenfilename(title="Select CSV with Metric IDs", filetypes=[("CSV files", "*.csv")])
    return filepath

def main():
    api_url = input("Enter the Dynatrace API URL (e.g., https://your.env/e/yourID/api/v2/metrics/query): ").strip()
    token = input("Enter your Dynatrace API token: ").strip()
    agg_time = input("Enter the timeframe (e.g., now-1h): ").strip()
    management_zone = input("Enter the Management Zone name: ").strip()

    headers = {
        "Authorization": f"Api-Token {token}"
    }

    csv_file = prompt_for_file()

    log_filename = "dynatrace_metrics_phase2_log_20250612_112908.log"
    csv_output = "dynatrace_metrics_summary_20250612_112908.csv"
    json_output = "dynatrace_metrics_data_20250612_112908.json"

    setup_logging(log_filename)

    summary = []

    with open(csv_file, 'r') as infile:
        metrics = infile.read().splitlines()

    for metric in metrics:
        metric = metric.strip()
        if not metric:
            continue

        query_url = f"{api_url}?metricSelector={metric}&from={agg_time}&entitySelector=type(\"HOST\")&mzSelector=mzName(\"{management_zone}\")"

        logging.info(f"Querying URL: {query_url}")
        try:
            response = requests.get(query_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            with open(json_output, 'a') as jf:
                json.dump(data, jf)
                jf.write("\n")

            count = 0
            if "result" in data and data["result"]:
                for series in data["result"]:
                    count += len(series.get("data", []))

            summary.append([metric, count])
            logging.info(f"Metric: {metric}, Count: {count}")

        except Exception as e:
            logging.error(f"Error fetching metric {metric}: {str(e)}")
            summary.append([metric, "Error"])

    with open(csv_output, 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(summary)

    logging.info(f"Summary written to {csv_output}")

if __name__ == "__main__":
    main()
