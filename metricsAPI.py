import requests
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
import logging
import tempfile
import re

# Configure logging with timestamp in filename
log_filename = f"MetricAPI2PDF_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

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
    return response.json()

def fetch_host_name(api_url, headers, host_id):
    """
    Fetch human-readable hostname from the Entities API.
    """
    base_url = api_url.split("metrics/query")[0]  # Remove /metrics/query from the base URL
    url = f"{base_url}/entities/{host_id}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        entity_data = response.json()
        display_name = entity_data.get("displayName", host_id)  # Fallback to host_id if displayName is missing
        logging.debug(f"Resolved {host_id} to {display_name}")
        return display_name
    except requests.exceptions.RequestException as e:
        logging.warning(f"Error fetching display name for {host_id}: {e}")
        return host_id

def parse_data(raw_data, api_url, headers):
    """
    Parse the raw data to group metrics by host.
    """
    grouped_data = {}
    host_name_cache = {}

    try:
        logging.debug(f"Raw API Response: {raw_data}")

        for data in raw_data['result'][0]['data']:
            # Attempt to extract host information
            dimension_map = data.get('dimensionMap', {})
            host_id = dimension_map.get('hostId', None)

            if not host_id and 'dimensions' in data:
                # Fallback to dimensions[0] for host ID
                host_id = data['dimensions'][0]

            if not host_id:
                logging.warning(f"Cannot determine host ID for data point: {data}")
                continue

            # Resolve the host name using the Entities API
            if host_id not in host_name_cache:
                host_name_cache[host_id] = fetch_host_name(api_url, headers, host_id)

            host_name = host_name_cache.get(host_id, host_id)
            metric_id = raw_data['result'][0]['metricId']
            timestamps = data.get('timestamps', [])
            values = data.get('values', [])

            if not timestamps or not values:
                logging.warning(f"Missing data for metric '{metric_id}' on host '{host_name}': Timestamps: {timestamps}, Values: {values}")
                continue

            if host_name not in grouped_data:
                grouped_data[host_name] = {}

            grouped_data[host_name][metric_id] = {"timestamps": timestamps, "values": values or [None] * len(timestamps)}

        logging.debug(f"Grouped Data: {grouped_data}")
        return grouped_data

    except Exception as e:
        logging.error(f"Error parsing data: {e}")
        raise

def generate_graph(timestamps, values, metric_name):
    """
    Generate a graph for the given metric.
    """
    try:
        if not timestamps or not values:
            logging.warning(f"Cannot generate graph for metric '{metric_name}': Missing timestamps or values.")
            return None

        if len(timestamps) != len(values):
            logging.error(f"Mismatch in data lengths for metric '{metric_name}': Timestamps length {len(timestamps)}, Values length {len(values)}.")
            return None

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
        logging.info(f"Graph successfully generated for metric '{metric_name}'.")
        return buffer
    except Exception as e:
        logging.error(f"Error generating graph for metric '{metric_name}': {e}")
        return None

def create_pdf(grouped_data, management_zone, agg_time, output_pdf):
    """
    Create a PDF report organized by host, embedding the graphs for each metric.
    """
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter

    # Calculate the number of unique hosts
    num_hosts = len(grouped_data)

    # Title Block
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, f"Team Name/Management Zone: {management_zone}")
    c.drawString(50, height - 70, f"Report Time: {report_time}")
    c.drawString(50, height - 90, f"Aggregation Period: {agg_time}")
    c.drawString(50, height - 110, f"Number of Hosts: {num_hosts}")

    y_position = height - 150

    # Host-Specific Sections
    for host_name, metrics_data in grouped_data.items():
        logging.debug(f"Processing host: {host_name}")
        if y_position < 150:
            c.showPage()
            y_position = height - 50

        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_position, f"Host: {host_name}")
        y_position -= 30

        for metric_name, data in metrics_data.items():
            timestamps = data.get('timestamps', [])
            values = data.get('values', [])

            logging.debug(f"Metric '{metric_name}' for host '{host_name}': Timestamps: {timestamps}, Values: {values}")

            if not timestamps or not values:
                logging.warning(f"Skipping graph for metric '{metric_name}' on host '{host_name}': Missing data.")
                continue

            if len(timestamps) != len(values):
                logging.error(f"Skipping graph for metric '{metric_name}' on host '{host_name}': Data length mismatch (Timestamps: {len(timestamps)}, Values: {len(values)}).")
                continue

            graph = generate_graph(timestamps, values, metric_name)
            if graph is None:
                logging.warning(f"Graph generation failed for metric '{metric_name}' on host '{host_name}'.")
                continue

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_image:
                temp_image.write(graph.getvalue())
                temp_image_path = temp_image.name

            logging.debug(f"Graph for metric '{metric_name}' on host '{host_name}' saved to temporary file '{temp_image_path}'.")

            c.drawImage(temp_image_path, 50, y_position, width=450, height=150)
            y_position -= 180

            if y_position < 150:
                c.showPage()
                y_position = height - 50

    c.save()

def sanitize_filename(filename):
    """
    Sanitize the filename by replacing specific patterns while preserving other conventions.
    """
    if ':' in filename:
        # Handle specific 'ABC: ABCD_1234' convention
        filename = re.sub(r'\s*:\s*', '_', filename)  # Replace colon and surrounding spaces with _
    # Remove other invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Strip leading/trailing spaces
    filename = filename.strip()
    return filename

if __name__ == "__main__":
    API_URL = input("Enter API URL: ").strip()
    API_TOKEN = input("Enter API Token: ").strip()
    MZ_SELECTOR = input("Enter Management Zone Name: ").strip()
    AGG_TIME = input("Enter Aggregation Time (e.g., now-1w): ").strip()

    HEADERS = {"Authorization": f"Api-Token {API_TOKEN}"}

    grouped_data = {}
    for metric_name, metric_selector in metrics.items():
        raw_data = fetch_metrics(API_URL, HEADERS, metric_selector, MZ_SELECTOR, AGG_TIME)
        parsed_data = parse_data(raw_data, API_URL, HEADERS)
        for host_name, data in parsed_data.items():
            if host_name not in grouped_data:
                grouped_data[host_name] = {}
            grouped_data[host_name][metric_name] = data

    OUTPUT_PDF = f"{MZ_SELECTOR}-Dynatrace_Metrics_Report-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
    OUTPUT_PDF = sanitize_filename(OUTPUT_PDF)
    create_pdf(grouped_data, MZ_SELECTOR, AGG_TIME, OUTPUT_PDF)

    print(f"PDF report generated: {OUTPUT_PDF}")
