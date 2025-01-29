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
import matplotlib.dates as mdates

# Configure logging
log_filename = f"MetricAPI2PDF_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Full metrics definition (restored)
metrics = {
    "Processor": "builtin:host.cpu.usage",
    "Memory": "builtin:host.mem.usage",
    "Average Disk Used Percentage": "builtin:host.disk.usedPct",
    "Average Disk Utilization Time": "builtin:host.disk.utilTime",
    "Disk Write Time Per Second": "builtin:host.disk.writeTime",
    "Average Disk Queue Length": "builtin:host.disk.queueLength",
    "Network Adapter In": "builtin:host.net.nic.trafficIn",
    "Network Adapter Out": "builtin:host.net.nic.trafficOut"
}

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

def group_data(raw_data):
    """
    Group metrics data by resolved host names and metrics, with human-readable value adjustments.
    """
    grouped_data = {}

    for metric_name, metric_data in raw_data.items():
        for data_point in metric_data.get('result', [])[0].get('data', []):
            host_id = data_point.get('dimensions', [None])[0]
            timestamps = [datetime.utcfromtimestamp(ts / 1000) for ts in data_point.get('timestamps', [])]
            values = data_point.get('values', [])

            # Adjust values based on metric type
            if metric_name == "Processor":
                values = [v * 100 if v is not None else None for v in values]  # Convert to percentage

            elif metric_name == "Memory":
                values = [v if v is not None else None for v in values]  # Memory is already percentage

            elif metric_name in ["Average Disk Used Percentage", "Average Disk Utilization Time"]:
                values = [v * 100 if v is not None else None for v in values]  # Convert to percentage

            elif metric_name == "Disk Write Time Per Second":
                values = [v * 1000 if v is not None else None for v in values]  # Convert seconds to milliseconds

            elif metric_name in ["Network Adapter In", "Network Adapter Out"]:
                values = [v / 1024 / 1024 if v is not None else None for v in values]  # Convert bytes to MB

            if host_id not in grouped_data:
                grouped_data[host_id] = {}

            grouped_data[host_id][metric_name] = {"timestamps": timestamps, "values": values}

    logging.debug(f"Grouped Data: {grouped_data}")
    return grouped_data

def generate_graph(timestamps, values, metric_name, host_name):
    """
    Generate a graph for the given metric with human-readable timestamps.
    """
    plt.figure(figsize=(8, 3.5))
    plt.plot(timestamps, values, label=f"{metric_name}", marker='o', color='blue')
    plt.title(f"{metric_name} - {host_name}")
    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.grid(True)
    plt.legend()
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))  # Human-readable time format
    plt.xticks(rotation=45)

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    return buffer

def create_pdf(grouped_data, management_zone, agg_time, output_pdf):
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
        y_position -= 20  # Add extra space between the header and the hostname

    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, height - 50, f"Team Name/Management Zone: {management_zone}")
    c.drawString(margin, height - 70, f"Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(margin, height - 90, f"Aggregation Period: {agg_time}")
    y_position -= 150

    for host_id, metrics_data in grouped_data.items():
        start_new_page()
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y_position, f"Host: {host_id}")
        y_position -= 40  # Increase spacing to avoid merging of text

        for metric_name, data in metrics_data.items():
            timestamps = data.get('timestamps', [])
            values = data.get('values', [])

            graph = generate_graph(timestamps, values, metric_name, host_id)
            if graph is None:
                logging.warning(f"Skipping graph for metric '{metric_name}' on host '{host_id}'.")
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
    API_URL = input("Enter API URL: ").strip()
    API_TOKEN = input("Enter API Token: ").strip()
    MZ_SELECTOR = input("Enter Management Zone Name: ").strip()
    AGG_TIME = input("Enter Aggregation Time (e.g., now-1m, now-5m, now-1h, now-1d): ").strip()
    RESOLUTION = input("Enter Resolution (e.g., 1m, 5m, 1h, 1d, or leave blank for default): ").strip()

    HEADERS = {"Authorization": f"Api-Token {API_TOKEN}"}

    raw_data = {}
    for metric_name, metric_selector in metrics.items():
        raw_data[metric_name] = fetch_metrics(API_URL, HEADERS, metric_selector, MZ_SELECTOR, AGG_TIME, RESOLUTION)

    grouped_data = group_data(raw_data)

    OUTPUT_PDF = f"{sanitize_filename(MZ_SELECTOR)}-Metrics_Report-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
    create_pdf(grouped_data, MZ_SELECTOR, AGG_TIME, OUTPUT_PDF)

    print(f"PDF report generated: {OUTPUT_PDF}")
