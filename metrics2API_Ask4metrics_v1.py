#Stryker Cain
import requests  # … (same as before)
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from matplotlib.ticker import FormatStrFormatter
from datetime import datetime
import logging
import tempfile
import re
import sys
import time

# … [lines 1–28 unchanged] …

# ### REMOVE the static metrics definition ###
# metrics = {
#     "Processor": "builtin:host.cpu.usage",
#     "Memory": "builtin:host.mem.usage",
#     "Average Disk Used Percentage": "builtin:host.disk.usedPct",
#     …
# }
# MODIFIED: Metrics will be prompted at runtime, not hard-coded here.

# … [print_progress, fetch_host_name, fetch_disk_owner functions unchanged] …

def fetch_metrics(api_url, headers, metric, mz_selector, agg_time, resolution):
    """
    Fetch metrics from the Dynatrace API.
    """
    resolution_param = f"&resolution={resolution}" if resolution else ""
    query_url = f'{api_url}?metricSelector={metric}&from={agg_time}' \
                f'&entitySelector=type("HOST")&mzSelector=mzName("{mz_selector}"){resolution_param}'
    # logging.debug(f"Fetching metrics with URL: {query_url}")  # MODIFIED: Removed URL logging to avoid exposing the full request in logs
    response = requests.get(query_url, headers=headers)
    response.raise_for_status()
    return response.json()

# … [group_data, generate_graph, sanitize_filename, create_pdf unchanged] …

if __name__ == "__main__":
    overall_start = time.time()

    API_URL = input("Enter API URL: ").strip()
    API_TOKEN = input("Enter API Token: ").strip()
    MZ_SELECTOR = input("Enter Management Zone Name: ").strip()
    AGG_TIME = input("Enter Aggregation Time: ").strip()
    RESOLUTION = input("Enter Resolution: ").strip()

    # MODIFIED: Prompt the user for metric selectors instead of using a static dict
    metrics_input = input(
        "What metric or metrics are you looking to pull from the API? (comma separated full selectors)\n> "
    ).split(",")
    metrics = [m.strip() for m in metrics_input if m.strip()]
    # End MODIFIED

    HEADERS = {"Authorization": f"Api-Token {API_TOKEN}"}

    # MODIFIED: Build raw_data from the user-provided metrics list
    raw_data = {}
    fetch_start_time = time.time()
    total_metrics = len(metrics)
    for idx, metric_selector in enumerate(metrics, start=1):
        raw_data[metric_selector] = fetch_metrics(
            API_URL, HEADERS, metric_selector, MZ_SELECTOR, AGG_TIME, RESOLUTION
        )
        print_progress(idx, total_metrics, fetch_start_time, prefix='Fetching metrics')
    # End MODIFIED

    grouped_data = group_data(raw_data, API_URL, HEADERS)
    OUTPUT_PDF = f"{sanitize_filename(MZ_SELECTOR)}-Dynatrace_Metrics_Report-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"

    if grouped_data:
        logging.info("Starting PDF generation...")
        pdf_start_time = time.time()
        create_pdf(grouped_data, MZ_SELECTOR, AGG_TIME, OUTPUT_PDF)
        pdf_generation_time = time.time() - pdf_start_time
        logging.info(f"PDF generation took: {pdf_generation_time:.2f} seconds")
        logging.info(f"PDF report generated: {OUTPUT_PDF}")
    else:
        logging.info("No data available to generate PDF.")

    total_running_time = time.time() - overall_start
    logging.info(f"Total running time: {total_running_time:.2f} seconds")
