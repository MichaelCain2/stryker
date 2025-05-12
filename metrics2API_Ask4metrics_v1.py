
# Stryker Cain - Validated Dynatrace Metrics PDF Report Script

import requests
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

# Configure logging
log_filename = f"MetricAPI2PDF_debug_{datetime.now():%Y%m%d_%H%M%S}.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.DEBUG)
logging.getLogger().addHandler(console)

def print_progress(current, total, start_time, prefix='Progress'):
    elapsed = time.time() - start_time
    progress = current / total if total else 1
    eta = (elapsed / progress - elapsed) if progress > 0 else 0
    bar_length = 30
    filled_length = int(round(bar_length * progress))
    bar = '=' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write(f'\r{prefix}: |{bar}| {progress*100:5.1f}% Elapsed: {elapsed:5.1f}s ETA: {eta:5.1f}s')
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write('\n')

def fetch_metrics(api_url, headers, metric, mz_selector, agg_time, resolution):
    resolution_param = f"&resolution={resolution}" if resolution else ""
    query_url = f'{api_url}?metricSelector={metric}&from={agg_time}&entitySelector=type("HOST")&mzSelector=mzName("{mz_selector}"){resolution_param}'
    response = requests.get(query_url, headers=headers)
    response.raise_for_status()
    return response.json()

def fetch_host_name(api_url, headers, host_id):
    base_url = api_url.split("metrics/query")[0]
    url = f"{base_url}/entities/{host_id}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        entity_data = response.json()
        return entity_data.get("displayName", host_id)
    except requests.exceptions.RequestException:
        return host_id

def group_data(raw_data, api_url, headers):
    grouped_data = {}
    host_name_cache = {}
    for metric_name, metric_data in raw_data.items():
        for data_point in metric_data.get('result', [{}])[0].get('data', []):
            host_id = data_point.get('dimensions', [None])[0]
            if not host_id:
                continue
            if host_id not in host_name_cache:
                host_name_cache[host_id] = fetch_host_name(api_url, headers, host_id)
            resolved_name = host_name_cache[host_id]
            grouped_data.setdefault(resolved_name, {})[metric_name] = {
                "timestamps": data_point.get('timestamps', []),
                "values": data_point.get('values', [])
            }
    return grouped_data

def sanitize_filename(filename):
    filename = re.sub(r'\s*:\s*', '_', filename)
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return filename.strip()

def generate_graph(timestamps, values, metric_name):
    try:
        if not timestamps or all(v is None for v in values):
            return None
        datetime_timestamps = [datetime.fromtimestamp(ts / 1000) for ts in timestamps]
        if metric_name == "Processor":
            values = [v * 100 if v is not None else 0 for v in values]
        plt.figure(figsize=(8, 4))
        plt.plot(datetime_timestamps, values, label=metric_name, marker='o', color='blue')
        plt.title(metric_name)
        plt.xlabel("")
        plt.ylabel("Percentage" if metric_name == "Processor" else "")
        plt.grid(True)
        plt.legend(loc="upper right", fontsize="medium", borderaxespad=1.5, labelspacing=1.0)
        ax = plt.gca()
        ax.xaxis.set_major_formatter(DateFormatter("%d-%b-%y"))
        plt.xticks(rotation=15)
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close()
        return buffer
    except Exception as e:
        logging.error(f"Graph generation error for '{metric_name}': {e}")
        return None

def create_pdf(grouped_data, management_zone, agg_time, output_pdf):
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter
    margin = 55
    chart_height = 120
    chart_spacing = 15
    y_position = height - margin

    def start_new_page():
        nonlocal y_position
        c.showPage()
        y_position = height - margin
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, height - 50, f"Team Name/Management Zone: {management_zone}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, height - 50, f"Team Name/Management Zone: {management_zone}")
    c.drawString(margin, height - 65, f"Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(margin, height - 80, f"Aggregation Period: {agg_time}")
    c.drawString(margin, height - 95, f"Number of Hosts/Servers: {len(grouped_data)}")
    y_position = height - 110

    for host_name, metrics_data in grouped_data.items():
        start_new_page()
        c.setFont("Helvetica-Bold", 14)
        y_position -= 20
        c.drawString(margin, y_position, f"Host: {host_name}")
        y_position -= 30
        for metric_name, data in metrics_data.items():
            timestamps = data.get('timestamps', [])
            values = data.get('values', [])
            if not timestamps or all(v is None for v in values):
                continue
            graph = generate_graph(timestamps, values, metric_name)
            if graph is None:
                continue
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_image:
                temp_image.write(graph.getvalue())
                temp_image_path = temp_image.name
            if y_position - chart_height - chart_spacing < margin:
                start_new_page()
            c.drawImage(temp_image_path, margin, y_position - chart_height, width=450, height=chart_height)
            y_position -= (chart_height + chart_spacing)
    c.save()

if __name__ == "__main__":
    overall_start = time.time()
    API_URL = input("Enter API URL: ").strip()
    API_TOKEN = input("Enter API Token: ").strip()
    MZ_SELECTOR = input("Enter Management Zone Name: ").strip()
    AGG_TIME = input("Enter Aggregation Time: ").strip()
    RESOLUTION = input("Enter Resolution: ").strip()
    metrics_input = input("What metric or metrics are you looking to pull from the API? (comma separated full selectors)\n> ").split(",")
    metrics = [m.strip() for m in metrics_input if m.strip()]
    HEADERS = {"Authorization": f"Api-Token {API_TOKEN}"}
    raw_data = {}
    fetch_start_time = time.time()
    total_metrics = len(metrics)
    for idx, metric_selector in enumerate(metrics, start=1):
        raw_data[metric_selector] = fetch_metrics(API_URL, HEADERS, metric_selector, MZ_SELECTOR, AGG_TIME, RESOLUTION)
        print_progress(idx, total_metrics, fetch_start_time, prefix='Fetching metrics')
    grouped_data = group_data(raw_data, API_URL, HEADERS)
    OUTPUT_PDF = f"{sanitize_filename(MZ_SELECTOR)}-Dynatrace_Metrics_Report-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
    if grouped_data:
        logging.info("Starting PDF generation...")
        pdf_start_time = time.time()
        create_pdf(grouped_data, MZ_SELECTOR, AGG_TIME, OUTPUT_PDF)
        logging.info(f"PDF generation took: {time.time() - pdf_start_time:.2f} seconds")
        logging.info(f"PDF report generated: {OUTPUT_PDF}")
    else:
        logging.info("No data available to generate PDF.")
    total_running_time = time.time() - overall_start
    logging.info(f"Total running time: {total_running_time:.2f} seconds")
