import requests
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
import logging
import re
import tempfile

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

def parse_data(raw_data):
    """
    Parse the raw data to group metrics by host.
    """
    grouped_data = {}
    try:
        for data in raw_data['result'][0]['data']:
            host_name = data['dimensionMap'].get('hostName', 'Unknown')
            metric_id = raw_data['result'][0]['metricId']
            timestamps = data['timestamps']
            values = data['values']

            if host_name not in grouped_data:
                grouped_data[host_name] = {}
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

def create_title_block(c, management_zone, report_time, start_time, duration, num_servers, metrics):
    """
    Create the title block at the top of the PDF.
    """
    styles = getSampleStyleSheet()
    text_style = styles['Normal']

    title_block = [
        Paragraph(f"<b>Team Name/Management Zone:</b> {management_zone}", text_style),
        Paragraph(f"<b>Report Time:</b> {report_time}", text_style),
        Paragraph(f"<b>Report Duration:</b> {start_time}", text_style),
        Paragraph(f"<b>Data Aggregation:</b> {duration}", text_style),
        Paragraph(f"<b>Number of Servers:</b> {num_servers}", text_style),
        Paragraph(f"<b>Resources:</b> {', '.join(metrics)}", text_style),
        Spacer(1, 24)
    ]

    y_position = 750
    for element in title_block:
        text = element.getPlainText()
        c.drawString(50, y_position, text)
        y_position -= 20

def create_pdf(grouped_data, management_zone, agg_time, output_pdf):
    """
    Create a PDF report with a title block and host-specific sections.
    """
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter

    # Title Block
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_time = agg_time
    duration = "Custom Aggregation Period"  # Example; adjust based on agg_time
    num_servers = len(grouped_data)
    metrics = list(grouped_data[next(iter(grouped_data))].keys())  # Example metrics list
    create_title_block(c, management_zone, report_time, start_time, duration, num_servers, metrics)

    y_position = height - 200

    # Host-Specific Sections
    for host_name, metrics in grouped_data.items():
        if y_position < 150:
            c.showPage()
            y_position = height - 100

        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_position, f"Host: {host_name}")
        y_position -= 30

        for metric_name, data in metrics.items():
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
                y_position = height - 100

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

    metrics = [
        "builtin:host.cpu.usage",
        "builtin:host.mem.usage",
        "builtin:host.disk.usedPct",
        "builtin:host.net.nic.trafficIn"
    ]

    grouped_data = {}
    for metric in metrics:
        raw_data = fetch_metrics(API_URL, HEADERS, metric, MZ_SELECTOR, AGG_TIME)
        grouped_data.update(parse_data(raw_data))

    OUTPUT_PDF = f"{MZ_SELECTOR}-Dynatrace_Metrics_Report-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
    OUTPUT_PDF = sanitize_filename(OUTPUT_PDF)
    create_pdf(grouped_data, MZ_SELECTOR, AGG_TIME, OUTPUT_PDF)

    print(f"PDF report generated: {OUTPUT_PDF}")
