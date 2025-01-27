import requests
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
import logging
import tempfile
import re

# Configure logging
logging.basicConfig(filename="MetricAPI2PDF_debug.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

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

ddef parse_data(raw_data):
    """
    Parse the raw data to extract 'timestamps', 'values', and 'entityId' from dimensionMap.
    """
    try:
        result = []
        for data in raw_data['result'][0]['data']:
            # Ensure data contains dimensionMap, timestamps, and values
            if isinstance(data, dict) and 'dimensionMap' in data and 'timestamps' in data and 'values' in data:
                entity_id = data['dimensionMap'].get('entityId', 'Unknown')
                timestamps = data['timestamps']
                values = data['values']

                # Pair each timestamp with its corresponding value
                for timestamp, value in zip(timestamps, values):
                    result.append({
                        "entityId": entity_id,
                        "time": timestamp,
                        "value": value
                    })
            else:
                logging.warning(f"Unexpected data structure: {data}")
        logging.debug(f"Parsed data: {result}")
        return pd.DataFrame(result)
    except (KeyError, IndexError, AttributeError, TypeError) as e:
        logging.error(f"Error parsing data: {e}")
        logging.debug(f"Raw data structure: {raw_data}")
        raise ValueError("Unexpected data structure in API response.")
def generate_graph(data, thresholds, title="Metrics Report"):
    """
    Generate a graph with line and scatter plots and threshold lines.
    """
    plt.figure(figsize=(8, 4))

    # Check for empty data
    if data.empty:
        logging.warning(f"No data available for graph '{title}'")
        return None

    # Line plot
    plt.plot(data['time'], data['value'], label='Metric Value', color='blue', marker='o')

    # Thresholds
    plt.axhline(y=thresholds['green'], color='green', linestyle='--', label='Green Threshold')
    plt.axhline(y=thresholds['yellow'], color='yellow', linestyle='--', label='Yellow Threshold')
    plt.axhline(y=thresholds['red'], color='red', linestyle='--', label='Red Threshold')

    # Formatting
    plt.title(title)
    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.legend()
    plt.grid(True)

    # Save to BytesIO
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    return buffer

def create_pdf(host_data, output_pdf):
    """
    Create a PDF report organized by host, embedding the graphs for each metric.
    """
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter

    for host, metrics in host_data.items():
        # Host section title
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 50, f"Host: {host}")
        y_position = height - 100

        for metric_name, graph_image in metrics.items():
            if graph_image is not None:  # Skip empty graphs
                # Metric title
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, y_position, f"Metric: {metric_name}")
                y_position -= 20

                # Write the BytesIO buffer to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_image:
                    temp_image.write(graph_image.getvalue())
                    temp_image_path = temp_image.name

                # Use the temporary file in drawImage
                c.drawImage(temp_image_path, 50, y_position, width=450, height=150)
                y_position -= 180

                if y_position < 100:  # Add new page if space is insufficient
                    c.showPage()
                    y_position = height - 100

    # Save PDF
    c.save()

def sanitize_filename(filename):
    """
    Remove or replace invalid characters in a filename.
    """
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def sanitize_mz_for_filename(mz_selector):
    """
    Sanitize the Management Zone name for use in the PDF filename.
    Replace special characters like colons with spaces.
    """
    return re.sub(r'[:]', ' ', mz_selector)

def format_friendly_agg_date(agg_date):
    """
    Convert aggDate into a user-friendly format for filenames.
    """
    if "now-" in agg_date:
        if "1w" in agg_date:
            return "Last_Week"
        elif "1d" in agg_date:
            return "Yesterday"
        elif "1h" in agg_date:
            return "Last_Hour"
        else:
            return agg_date.replace("now-", "").capitalize()  # Default for other ranges
    elif "-" in agg_date and "T" in agg_date:  # Explicit date range
        start_date, end_date = agg_date.split("-")
        start = datetime.fromisoformat(start_date).strftime("%Y-%m-%d")
        end = datetime.fromisoformat(end_date).strftime("%Y-%m-%d")
        return f"{start}_to_{end}"
    else:
        return agg_date  # Fallback for unknown formats

if __name__ == "__main__":
    # Predefined Metrics and Thresholds
    metrics = {
        "Processor": "builtin:host.cpu.usage",
        "Memory": "builtin:host.mem.usage",
        "Average Disk Used Percentage": "builtin:host.disk.usedPct",
        "Average Disk Idletime Percentage": "com.dynatrace.extension.host-observability.disk.usage.idle.percent",
        "Disk Transfer Per Second": "com.dynatrace.extension.host-observability.disk.transfer.persec",
        "Average Disk Queue Length": "builtin:host.disk.queueLength",
        "Network Adapter In": "builtin:host.net.nic.trafficIn",
        "Network Adapter Out": "builtin:host.net.nic.trafficOut"
    }

    thresholds = {
        "Processor": {"green": 50, "yellow": 90, "red": 100},
        "Memory": {"green": 30, "yellow": 95, "red": 100},
        "Average Disk Used Percentage": {"green": 60, "yellow": 85, "red": 100},
        "Average Disk Idletime Percentage": {"green": 60, "yellow": 85, "red": 100},
        "Disk Transfer Per Second": {"green": 60, "yellow": 85, "red": 100},
        "Average Disk Queue Length": {"green": 60, "yellow": 85, "red": 100},
        "Network Adapter In": {"green": 20, "yellow": 70, "red": 100},
        "Network Adapter Out": {"green": 20, "yellow": 70, "red": 100}
    }

    # Input parameters
    API_URL = input("Enter API URL: ").strip()
    API_TOKEN = input("Enter API Token: ").strip()
    MZ_SELECTOR = input("Enter Management Zone Name: ").strip()  # Keep unchanged for query
    AGG_TIME = input("Enter Aggregation Time (e.g., now-1w): ").strip()

    HEADERS = {"Authorization": f"Api-Token {API_TOKEN}"}

    # Group metrics by host
    host_data = {}
    for metric_name, metric_selector in metrics.items():
        try:
            raw_data = fetch_metrics(API_URL, HEADERS, metric_selector, MZ_SELECTOR, AGG_TIME)
            df = parse_data(raw_data)
            for host, data in df.groupby("entityId"):
                if host not in host_data:
                    host_data[host] = {}
                host_data[host][metric_name] = generate_graph(data, thresholds[metric_name], title=metric_name)
        except Exception as e:
            logging.error(f"Failed to process metric '{metric_name}': {e}")

    # Format output PDF filename
    sanitized_mz = sanitize_mz_for_filename(MZ_SELECTOR)  # Sanitize for filename only
    friendly_agg_date = format_friendly_agg_date(AGG_TIME)
    run_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    OUTPUT_PDF = f"{sanitized_mz}-{friendly_agg_date}Dynatrace_Metrics_Report-{run_date}.pdf"
    OUTPUT_PDF = sanitize_filename(OUTPUT_PDF)  # Final sanitization

    # Create PDF
    create_pdf(host_data, output_pdf=OUTPUT_PDF)

    print(f"PDF report generated: {OUTPUT_PDF}")
