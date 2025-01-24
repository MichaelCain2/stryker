import requests
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime

def fetch_metrics(api_url, headers, metric, entity_filter, mz_selector, agg_time):
    """
    Fetch metrics from the Dynatrace API.
    """
    query_url = f"{api_url}?metricSelector={metric}&from={agg_time}&entitySelector={entity_filter}&mzSelector={mz_selector}"
    response = requests.get(query_url, headers=headers)
    response.raise_for_status()
    return response.json()

def generate_graph(data, thresholds, title="Metrics Report"):
    """
    Generate a graph with line and scatter plots and threshold lines.
    """
    plt.figure(figsize=(10, 6))

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

def create_pdf(data, graph_images, output_pdf):
    """
    Create a PDF report embedding the graphs.
    """
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 50, "Dynatrace Metrics Report")

    # Add Graphs
    y_position = height - 150
    for img_buffer in graph_images:
        c.drawImage(img_buffer, 50, y_position, width=500, height=300)
        y_position -= 350
        if y_position < 50:  # Add new page if space is insufficient
            c.showPage()
            y_position = height - 150

    # Save PDF
    c.save()

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
    ENTITY_FILTER = input("Enter Entity Filter: ").strip()
    MZ_SELECTOR = input("Enter Management Zone Selector: ").strip()
    AGG_TIME = input("Enter Aggregation Time (e.g., now-1w): ").strip()

    HEADERS = {"Authorization": f"Api-Token {API_TOKEN}"}
    
    # Iterate through metrics
    graph_buffers = []
    for metric_name, metric_selector in metrics.items():
        raw_data = fetch_metrics(API_URL, HEADERS, metric_selector, ENTITY_FILTER, MZ_SELECTOR, AGG_TIME)
        df = pd.DataFrame(raw_data['result'][0]['data'])
        graph_buffers.append(generate_graph(df, thresholds[metric_name], title=metric_name))

    # Format output PDF filename
    friendly_agg_date = format_friendly_agg_date(AGG_TIME)
    run_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    OUTPUT_PDF = f"{MZ_SELECTOR}-{friendly_agg_date}Dynatrace_Metrics_Report-{run_date}.pdf"

    # Create PDF
    create_pdf(df, graph_buffers, output_pdf=OUTPUT_PDF)

    print(f"PDF report generated: {OUTPUT_PDF}")
