import requests
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, date2num
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
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

def create_pdf(grouped_data, management_zone, agg_time, output_pdf):
    """
    Create a PDF report organized by host, embedding the graphs for each metric.
    """
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter
    margin = 50
    styles = getSampleStyleSheet()
    text_style = styles["Normal"]
    
    # Generate the updated title block
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    duration = "Weekly" if "1w" in agg_time else "Daily" if "1d" in agg_time else "Custom"
    num_servers = len(grouped_data)
    
    title_block = [
        Paragraph(f"<b>Report Time:</b> {report_time}", text_style),
        Spacer(1, 10),
        Paragraph(f"<b>Report Duration:</b> {agg_time}", text_style),
        Spacer(1, 10),
        Paragraph(f"<b>Data Aggregation:</b> {duration}", text_style),
        Spacer(1, 10),
        Paragraph(f"<b>Number of Servers:</b> {num_servers}", text_style),
        Spacer(1, 10),
        Paragraph(f"<b>Resources:</b> {', '.join(metrics)}", text_style),
        Spacer(1, 24)
    ]

    y_position = height - margin - 100  # Adjust for header space
    for element in title_block:
        if isinstance(element, Paragraph):
            element.wrapOn(c, width - 2 * margin, height)
            element.drawOn(c, margin, y_position)
            y_position -= 20  # Adjust spacing
        elif isinstance(element, Spacer):
            y_position -= element.height
    
    # Continue with existing logic for host data and metrics
    for host_name, metrics_data in grouped_data.items():
        c.showPage()
        y_position = height - margin  # Reset y_position for new page
        c.setFont("Helvetica-Bold", 14)
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

            c.drawImage(temp_image_path, margin, y_position - 120, width=450, height=120)
            y_position -= 140
    
    c.save()

if __name__ == "__main__":
    API_URL = input("Enter API URL: ").strip()
    API_TOKEN = input("Enter API Token: ").strip()
    MZ_SELECTOR = input("Enter Management Zone Name: ").strip()
    AGG_TIME = input("Enter Aggregation Time (e.g., now-1m, now-5m, now-1h, now-1d): ").strip()
    RESOLUTION = input("Enter Resolution (e.g., 1m, 5m, 1h, 1d, or leave blank for default): ").strip()

    HEADERS = {"Authorization": f"Api-Token {API_TOKEN}"}

    # Fetch and group data
    raw_data = {}
    for metric_name, metric_selector in metrics.items():
        raw_data[metric_name] = fetch_metrics(API_URL, HEADERS, metric_selector, MZ_SELECTOR, AGG_TIME, RESOLUTION)
    
    grouped_data = group_data(raw_data, API_URL, HEADERS)
    
    OUTPUT_PDF = f"{MZ_SELECTOR.replace(':', '_')}-Dynatrace_Metrics_Report-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
    create_pdf(grouped_data, MZ_SELECTOR, AGG_TIME, OUTPUT_PDF)

    print(f"PDF report generated: {OUTPUT_PDF}")
