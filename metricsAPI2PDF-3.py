import requests
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
import logging
import re
import tempfile

# Configure logging
logging.basicConfig(filename="MetricAPI2PDF_debug.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Metrics definition
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

def fetch_metrics(api_url, headers, metric, mz_selector, agg_time):
    """
    Fetch metrics from the Dynatrace API.
    """
    query_url = f'{api_url}?metricSelector={metric}&from={agg_time}&entitySelector=type("HOST")&mzSelector=mzName("{mz_selector}")'
    logging.debug(f"Fetching metrics with URL: {query_url}")
    response = requests.get(query_url, headers=headers)
    response.raise_for_status()
    logging.debug(f"API response: {response.json()}")
    return response.json()

def parse_data(raw_data):
    """
    Parse the raw data to group metrics by host.
    """
    grouped_data = {}
    try:
        for data in raw_data['result'][0]['data']:
            host_name = data['dimensionMap'].get('hostName', 'Unknown')
            timestamps = data.get('timestamps', [])
            values = data.get('values', [])

            if host_name not in grouped_data:
                grouped_data[host_name] = {}

            # Store timestamps and values under the metric name
            metric_id = raw_data['result'][0]['metricId']
            grouped_data[host_name][metric_id] = {"timestamps": timestamps, "values": values}

        logging.debug(f"Grouped data: {grouped_data}")
        return grouped_data
    except Exception as e:
        logging.error(f"Error parsing data: {e}")
        raise ValueError("Unexpected data structure in API response.")
def generate_graph(timestamps, values, metric_name):
    """
    Generate a graph for the given metric.
    """
    plt.figure(figsize=(8, 4))
    plt.plot(timestamps, values, label=metric_name, marker='o', color='blue')
    plt.title(metric_name)
    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.grid(True)
    plt.legend()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    return buffer

def create_pdf(grouped_data, management_zone, agg_time, output_pdf):
    """
    Create a PDF report organized by host, embedding the graphs for each metric.
    """
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter

    # Title Block
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_time = agg_time
    duration = "Custom Aggregation Period"
    num_servers = len(grouped_data)

    y_position = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y_position, f"Team Name/Management Zone: {management_zone}")
    y_position -= 20
    c.drawString(50, y_position, f"Report Time: {report_time}")
    y_position -= 20
    c.drawString(50, y_position, f"Report Duration: {start_time}")
    y_position -= 20
    c.drawString(50, y_position, f"Data Aggregation: {duration}")
    y_position -= 20
    c.drawString(50, y_position, f"Number of Servers: {num_servers}")
    y_position -= 40

    # Host-Specific Sections
    for host_name, metrics_data in grouped_data.items():
        if y_position < 150:
            c.showPage()
            y_position = height - 50

        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_position, f"Host: {host_name}")
        y_position -= 30

        for metric_name, data in metrics_data.items():
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y_position, f"Metric: {metric_name}")
            y_position -= 20

            # Generate and insert the chart
            graph = generate_graph(data['timestamps'], data['values'], metric_name)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_image:
                temp_image.write(graph.getvalue())
                temp_image_path = temp_image.name

            c.drawImage(temp_image_path, 50, y_position, width=450, height=150)
            y_position -= 180

            if y_position < 150:
                c.showPage()
                y_position = height - 50

    # Save PDF
    c.save()

def sanitize_filename(filename):
    """
    Remove or replace invalid characters in a filename.
    """
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

if __name__ == "__main__":
    API_URL = input("Enter API URL: ").strip()
    API_TOKEN = input("Enter API Token: ").strip()
    MZ_SELECTOR = input("Enter Management Zone Name: ").strip()
    AGG_TIME = input("Enter Aggregation Time (e.g., now-1w): ").strip()

    HEADERS = {"Authorization": f"Api-Token {API_TOKEN}"}

    grouped_data = {}
    for metric_name, metric_selector in metrics.items():
        try:
            raw_data = fetch_metrics(API_URL, HEADERS, metric_selector, MZ_SELECTOR, AGG_TIME)
            parsed_data = parse_data(raw_data)
            for host_name, data in parsed_data.items():
                if host_name not in grouped_data:
                    grouped_data[host_name] = {}
                grouped_data[host_name][metric_name] = data
        except Exception as e:
            logging.error(f"Failed to fetch or process metric '{metric_name}': {e}")

    OUTPUT_PDF = f"{MZ_SELECTOR}-Dynatrace_Metrics_Report-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
    OUTPUT_PDF = sanitize_filename(OUTPUT_PDF)
    create_pdf(grouped_data, MZ_SELECTOR, AGG_TIME, OUTPUT_PDF)

    print(f"PDF report generated: {OUTPUT_PDF}")
