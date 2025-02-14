mport requests
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, date2num
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

def group_data(raw_data, api_url, headers):
    """
    Group metrics data by resolved host names and metrics.
    """
    grouped_data = {}
    host_name_cache = {}

    for metric_name, metric_data in raw_data.items():
        for data_point in metric_data.get('result', [])[0].get('data', []):
            # Extract host ID
            host_id = data_point.get('dimensions', [None])[0]
            if not host_id:
                logging.warning(f"Missing host ID in data point: {data_point}")
                continue

            # Resolve host name if not already cached
            if host_id not in host_name_cache:
                host_name_cache[host_id] = fetch_host_name(api_url, headers, host_id)

            resolved_name = host_name_cache.get(host_id, host_id)
            timestamps = data_point.get('timestamps', [])
            values = data_point.get('values', [])

            # Organize data by host and metric
            if resolved_name not in grouped_data:
                grouped_data[resolved_name] = {}

            grouped_data[resolved_name][metric_name] = {"timestamps": timestamps, "values": values}

    logging.debug(f"Grouped Data: {grouped_data}")
    return grouped_data

def generate_graph(timestamps, values, metric_name):
    """
    Generate a graph for the given metric.
    """
    try:
        if not timestamps or all(v is None for v in values):
            logging.warning(f"Cannot generate graph for metric '{metric_name}': Missing or invalid data.")
            return None

        # Convert timestamps to human-readable datetime
        datetime_timestamps = [datetime.fromtimestamp(ts / 1000) for ts in timestamps]

        plt.figure(figsize=(8, 4))
        plt.plot(datetime_timestamps, values, label=metric_name, marker='o', color='blue')
        plt.title(metric_name)
        plt.xlabel("Time")
        plt.ylabel("Value")
        plt.grid(True)
        plt.legend()

        # Format x-axis for better readability
        ax = plt.gca()
        ax.xaxis.set_major_formatter(DateFormatter("%H:%M:%S"))
        plt.xticks(rotation=45)

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

    # Title Block
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, f"Team Name/Management Zone: {management_zone}")
    c.drawString(50, height - 70, f"Report Time: {report_time}")
    c.drawString(50, height - 90, f"Aggregation Period: {agg_time}")
    c.drawString(50, height - 110, f"Number of Hosts: {len(grouped_data)}")

    y_position = height - 150

    # Host-Specific Sections
    for host_name, metrics_data in grouped_data.items():
        logging.debug(f"Processing host: {host_name}")
        if y_position < 150:
            c.showPage()
            y_position = height - 50

        # Add host name as a distinct section header
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_position, f"Host: {host_name}")
        y_position -= 30

        for metric_name, data in metrics_data.items():
            timestamps = data.get('timestamps', [])
            values = data.get('values', [])

            logging.debug(f"Metric '{metric_name}' for host '{host_name}': Timestamps: {timestamps}, Values: {values}")

            if not timestamps or all(v is None for v in values):
                logging.warning(f"Skipping graph for metric '{metric_name}' on host '{host_name}': Missing or invalid data.")
                continue

            graph = generate_graph(timestamps, values, metric_name)
            if graph is None:
                logging.warning(f"Graph generation failed for metric '{metric_name}' on host '{host_name}'.")
                continue

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_image:
                temp_image.write(graph.getvalue())
                temp_image_path = temp_image.name

            logging.debug(f"Graph for metric '{metric_name}' on host '{host_name}' saved to temporary file '{temp_image_path}'.")

            # Check y_position and add page breaks if necessary
            if y_position < 200:
                c.showPage()
                y_position = height - 50

            c.drawImage(temp_image_path, 50, y_position - 150, width=450, height=150)
            y_position -= 180

    c.save()

def sanitize_filename(filename):
    """
    Sanitize the filename by replacing specific patterns while preserving other conventions.
    """
    if ':' in filename:
        filename = re.sub(r'\s*:\s*', '_', filename)  # Replace colon and surrounding spaces with _
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)  # Remove invalid characters
    filename = filename.strip()  # Strip leading/trailing spaces
    return filename

if __name__ == "__main__":
    API_URL = input("Enter API URL: ").strip()
    API_TOKEN = input("Enter API Token: ").strip()
    MZ_SELECTOR = input("Enter Management Zone Name: ").strip()
    AGG_TIME = input("Enter Aggregation Time (e.g., now-1w): ").strip()

    HEADERS = {"Authorization": f"Api-Token {API_TOKEN}"}

    # Fetch and group data
    raw_data = {}
    for metric_name, metric_selector in metrics.items():
        raw_data[metric_name] = fetch_metrics(API_URL, HEADERS, metric_selector, MZ_SELECTOR, AGG_TIME)

    grouped_data = group_data(raw_data, API_URL, HEADERS)

    # Generate PDF
    OUTPUT_PDF = f"{sanitize_filename(MZ_SELECTOR)}-Dynatrace_Metrics_Report-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
    create_pdf(grouped_data, MZ_SELECTOR, AGG_TIME, OUTPUT_PDF)

    print(f"PDF report generated: {OUTPUT_PDF}")
