import requests
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
import logging
import tempfile
import re

# Configure logging
log_filename = f"MetricAPI2PDF-corecount_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Metrics definition
metrics = {
    "Processor": "builtin:host.cpu.usage",
    "Memory": "builtin:host.mem.usage",
    "Average Disk Used Percentage": "builtin:host.disk.usedPct",
    "Network Traffic In": "builtin:host.net.nic.trafficIn",
    "Network Traffic Out": "builtin:host.net.nic.trafficOut"
}

def fetch_host_details(api_url, headers):
    """
    Fetch host details including display name and CPU core count.
    """
    url = f"{api_url.split('/metrics/query')[0]}/entities?type=HOST&fields=properties.cpuCores"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    host_data = response.json()

    host_details = {}
    for entity in host_data.get("entities", []):
        host_id = entity["entityId"]
        display_name = entity.get("displayName", host_id)
        cpu_cores = entity.get("properties", {}).get("cpuCores", 1)  # Default to 1 if missing
        host_details[host_id] = {"displayName": display_name, "cpuCores": cpu_cores}
    
    return host_details

def fetch_metrics(api_url, headers, metric, mz_selector, agg_time, resolution):
    """
    Fetch metrics from the Dynatrace API.
    """
    resolution_param = f"&resolution={resolution}" if resolution else ""
    query_url = f'{api_url}?metricSelector={metric}&from={agg_time}&entitySelector=type("HOST")&mzSelector=mzName("{mz_selector}"){resolution_param}'
    logging.debug(f"Fetching metrics with URL: {query_url}")
    response = requests.get(query_url, headers=headers)
    response.raise_for_status()
    return response.json()

def group_data(raw_data, api_url, headers):
    """
    Group metrics data by resolved host names and metrics.
    """
    grouped_data = {}
    host_name_cache = {}

    for metric_name, metric_data in raw_data.items():
        for data_point in metric_data.get('result', [])[0].get('data', []):
            host_id = data_point.get('dimensions', [None])[0]
            if not host_id:
                logging.warning(f"Missing host ID in data point: {data_point}")
                continue

            if host_id not in host_name_cache:
                host_name_cache[host_id] = fetch_host_details(api_url, headers).get(host_id, {})

            resolved_name = host_name_cache.get(host_id, {}).get("displayName", host_id)
            timestamps = data_point.get('timestamps', [])
            values = data_point.get('values', [])

            if resolved_name not in grouped_data:
                grouped_data[resolved_name] = {}

            grouped_data[resolved_name][metric_name] = {"timestamps": timestamps, "values": values}

    logging.debug(f"Grouped Data: {grouped_data}")
    return grouped_data

def normalize_processor_data(metrics_data, host_details):
    """
    Normalize processor data by dividing by the number of cores.
    """
    for host_name, metrics in metrics_data.items():
        cpu_cores = host_details.get(host_name, {}).get("cpuCores", 1)
        for metric_name, metric_data in metrics.items():
            if metric_name == "Processor":
                metric_data["values"] = [
                    (value / cpu_cores) * 100 if value is not None else None
                    for value in metric_data["values"]
                ]
    return metrics_data

def generate_graph(timestamps, values, metric_name, core_count, host_name):
    """
    Generate a graph for the given metric.
    """
    plt.figure(figsize=(8, 3.5))
    plt.plot(timestamps, values, label=f"{metric_name} (Normalized)", marker='o', color='blue')
    plt.title(f"{metric_name} - {host_name} ({core_count} Cores)")
    plt.xlabel("Time")
    plt.ylabel("CPU Usage (%)")
    plt.grid(True)
    plt.legend()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    return buffer

def create_pdf(grouped_data, host_details, management_zone, agg_time, output_pdf):
    """
    Create a PDF report with normalized processor data.
    """
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter
    margin = 50
    chart_height = 120
    chart_spacing = 20
    y_position = height - margin

    def start_new_page():
        nonlocal y_position
        c.showPage()
        y_position = height - margin
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, height - 50, f"Team Name/Management Zone: {management_zone}")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, height - 50, f"Team Name/Management Zone: {management_zone}")
    c.drawString(margin, height - 70, f"Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(margin, height - 90, f"Aggregation Period: {agg_time}")
    y_position -= 150

    for host_name, metrics_data in grouped_data.items():
        start_new_page()
        core_count = host_details.get(host_name, {}).get("cpuCores", 1)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y_position, f"Host: {host_name} ({core_count} Cores)")
        y_position -= 30

        for metric_name, data in metrics_data.items():
            timestamps = data.get('timestamps', [])
            values = data.get('values', [])

            graph = generate_graph(timestamps, values, metric_name, core_count, host_name)
            if graph is None:
                logging.warning(f"Skipping graph for metric '{metric_name}' on host '{host_name}'.")
                continue

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_image:
                temp_image.write(graph.getvalue())
                temp_image_path = temp_image.name

            if y_position - chart_height - chart_spacing < margin:
                start_new_page()

            c.drawImage(temp_image_path, margin, y_position - chart_height, width=450, height=chart_height)
            y_position -= (chart_height + chart_spacing)

    c.save()

def sanitize_filename(filename):
    """
    Sanitize the filename by replacing specific patterns while preserving other conventions.
    """
    if ':' in filename:
        filename = re.sub(r'\s*:\s*', '_', filename)
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip()
    return filename

if __name__ == "__main__":
    API_URL = input("Enter API URL: ").strip()
    API_TOKEN = input("Enter API Token: ").strip()
    MZ_SELECTOR = input("Enter Management Zone Name: ").strip()
    AGG_TIME = input("Enter Aggregation Time (e.g., now-1m, now-5m, now-1h, now-1d): ").strip()
    RESOLUTION = input("Enter Resolution (e.g., 1m, 5m, 1h, 1d, or leave blank for default): ").strip()

    HEADERS = {"Authorization": f"Api-Token {API_TOKEN}"}

    host_details = fetch_host_details(API_URL, HEADERS)

    raw_data = {}
    for metric_name, metric_selector in metrics.items():
        raw_data[metric_name] = fetch_metrics(API_URL, HEADERS, metric_selector, MZ_SELECTOR, AGG_TIME, RESOLUTION)

    grouped_data = group_data(raw_data, API_URL, HEADERS)
    grouped_data = normalize_processor_data(grouped_data, host_details)

    OUTPUT_PDF = f"{sanitize_filename(MZ_SELECTOR)}-Metrics_Report-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
    create_pdf(grouped_data, host_details, MZ_SELECTOR, AGG_TIME, OUTPUT_PDF)

    print(f"PDF report generated: {OUTPUT_PDF}")
