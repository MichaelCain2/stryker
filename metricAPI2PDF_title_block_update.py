import requests  # For making API requests to Dynatrace
import matplotlib.pyplot as plt  # To generate metric graphs
from matplotlib.dates import DateFormatter  # To format timestamps on graphs
from io import BytesIO  # Allows handling images in memory instead of disk
from reportlab.pdfgen import canvas  # Handles PDF generation
from reportlab.lib.pagesizes import letter  # Sets page size to standard US letter (8.5x11)
from datetime import datetime  # Used for timestamps in logs and reports
import logging  # Manages debug/error logs
import tempfile  # Temporarily stores images for the PDF
import re  # Cleans up filenames by removing invalid characters

# ------------------------------------------------------------------------
# CONFIGURE LOGGING - This ensures we track what happens during execution
# ------------------------------------------------------------------------

# Create a unique log file with a timestamp in the filename
log_filename = f"MetricAPI2PDF_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Set up logging configuration
logging.basicConfig(
    filename=log_filename, 
    level=logging.DEBUG,  # Logs everything from DEBUG level and up
    format="%(asctime)s - %(levelname)s - %(message)s"  # Adds timestamps and log levels
)

# ------------------------------------------------------------------------
# METRICS DEFINITION - Defines which Dynatrace metrics to fetch
# ------------------------------------------------------------------------

metrics = {
    "Processor": "builtin:host.cpu.usage",  # CPU usage percentage
    "Memory": "builtin:host.mem.usage",  # Memory usage percentage
    "Average Disk Used Percentage": "builtin:host.disk.usedPct",  # Disk space usage
    "Average Disk Utilization Time": "builtin:host.disk.utilTime",  # Disk activity
    "Disk Write Time Per Second": "builtin:host.disk.writeTime",  # Disk write time
    "Average Disk Queue Length": "builtin:host.disk.queueLength",  # Disk queue length
    "Network Adapter In": "builtin:host.net.nic.trafficIn",  # Incoming network traffic
    "Network Adapter Out": "builtin:host.net.nic.trafficOut"  # Outgoing network traffic
}

# ------------------------------------------------------------------------
# FUNCTION: fetch_metrics - Calls Dynatrace API to get metric data
# ------------------------------------------------------------------------

def fetch_metrics(api_url, headers, metric, mz_selector, agg_time, resolution):
    """
    Fetch metric data from the Dynatrace API.
    """
    resolution_param = f"&resolution={resolution}" if resolution else ""
    query_url = f'{api_url}?metricSelector={metric}&from={agg_time}&entitySelector=type("HOST")&mzSelector=mzName("{mz_selector}"){resolution_param}'
    logging.debug(f"Fetching metrics with URL: {query_url}")

    response = requests.get(query_url, headers=headers)
    response.raise_for_status()  # Raise an error if the API call fails
    return response.json()

# ------------------------------------------------------------------------
# FUNCTION: fetch_host_name - Resolves host ID to a readable name
# ------------------------------------------------------------------------

def fetch_host_name(api_url, headers, host_id):
    """
    Retrieve the display name for a given host ID using the Dynatrace Entities API.
    """
    base_url = api_url.split("metrics/query")[0]  # Get base URL without "/metrics/query"
    url = f"{base_url}/entities/{host_id}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        entity_data = response.json()
        display_name = entity_data.get("displayName", host_id)  # Use host_id if no name found
        logging.debug(f"Resolved {host_id} to {display_name}")
        return display_name
    except requests.exceptions.RequestException as e:
        logging.warning(f"Error fetching display name for {host_id}: {e}")
        return host_id  # Fall back to raw host ID if API call fails

# ------------------------------------------------------------------------
# FUNCTION: create_pdf - Generates a full PDF report with graphs
# ------------------------------------------------------------------------

def create_pdf(grouped_data, management_zone, agg_time, output_pdf):
    """
    Creates a PDF report with graphs for each metric, organized by host.
    """
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter
    margin = 55
    chart_height = 120
    chart_spacing = 15
    y_position = height - margin

    # Add Header Section
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, height - 50, f"Team Name/Management Zone: {management_zone}")
    c.drawString(margin, height - 65, f"Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(margin, height - 85, f"Aggregation Period: {agg_time}")
    c.drawString(margin, height - 100, f"Number of Hosts/Servers: {len(grouped_data)}")
    c.drawString(margin, height - 115, "Resources/Metrics:")

    # List Metrics
    y_position = height - 130
    for metric_name in metrics.keys():
        c.drawString(margin + 20, y_position, f"- {metric_name}")
        y_position -= 15

    y_position -= 20

    # Host-Specific Sections
    for host_name, metrics_data in grouped_data.items():
        c.showPage()  # Start a new page for each host
        y_position = height - margin
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
                c.showPage()
                y_position = height - margin

            c.drawImage(temp_image_path, margin, y_position - chart_height, width=450, height=chart_height)
            y_position -= (chart_height + chart_spacing)

    c.save()

# ------------------------------------------------------------------------
# MAIN EXECUTION - This runs when the script is executed
# ------------------------------------------------------------------------

if __name__ == "__main__":
    """
    The script starts here. It collects user inputs, fetches data, and generates the PDF report.
    """
    API_URL = input("Enter API URL: ").strip()  # URL for Dynatrace API
    API_TOKEN = input("Enter API Token: ").strip()  # Auth token for API access
    MZ_SELECTOR = input("Enter Management Zone Name: ").strip()  # Management Zone name
    AGG_TIME = input("Enter Aggregation Time (e.g., now-1h, now-1d): ").strip()  # Time range
    RESOLUTION = input("Enter Resolution (e.g., 1m, 5m, 1h): ").strip()  # Data resolution

    HEADERS = {"Authorization": f"Api-Token {API_TOKEN}"}  # Add token to request headers

    # Fetch data for each metric and store results in raw_data
    raw_data = {metric_name: fetch_metrics(API_URL, HEADERS, metric_selector, MZ_SELECTOR, AGG_TIME, RESOLUTION) for metric_name, metric_selector in metrics.items()}

    # Organize the data by host and metric
    grouped_data = group_data(raw_data, API_URL, HEADERS)

    # Generate the output filename with a timestamp
    OUTPUT_PDF = f"{re.sub(r'[<>:\"/\\|?*]', '_', MZ_SELECTOR)}-Dynatrace_Metrics_Report-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"

    # Generate the PDF report
    create_pdf(grouped_data, MZ_SELECTOR, AGG_TIME, OUTPUT_PDF)

    print(f"PDF report generated: {OUTPUT_PDF}")  # Notify the user
