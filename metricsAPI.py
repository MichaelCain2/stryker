import requests
import json
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Font
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
from datetime import datetime
from tkinter import Tk, filedialog

# Define thresholds for green, yellow, red
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

def fetch_metrics(api_url, headers, metric, entity_filter, management_zone, start_time):
    """
    Fetches metrics from Dynatrace using the Metrics API.
    """
    url = f"{api_url}?metricSelector={metric}&from={start_time}&entitySelector={entity_filter}&mzSelector=mzName(\"{management_zone}\")"
    print(f"Fetching data from URL: {url}")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def normalize_metric_data(metric_data):
    """
    Normalize and flatten the fetched metric data for easy writing to Excel.
    """
    normalized_data = []
    for item in metric_data.get('items', []):
        for datapoint in item.get('dataPoints', []):
            normalized_data.append({
                "Time": datapoint[0],
                "Value": datapoint[1]
            })
    return pd.DataFrame(normalized_data)

def create_chart(chart_data, title, metric_name):
    """
    Create a bar chart for a given metric and save it to a BytesIO stream.
    Apply color coding based on thresholds.
    """
    colors = []
    if metric_name in chart_data:
        for value in chart_data[metric_name]:
            if value <= thresholds[metric_name]["green"]:
                colors.append("green")
            elif value <= thresholds[metric_name]["yellow"]:
                colors.append("yellow")
            else:
                colors.append("red")
    plt.figure(figsize=(8, 4))
    plt.bar(chart_data['Time'], chart_data[metric_name], color=colors)
    plt.title(title)
    plt.xlabel('Time')
    plt.ylabel(metric_name)
    plt.xticks(rotation=45, ha='right')
    chart_stream = BytesIO()
    plt.tight_layout()
    plt.savefig(chart_stream, format='png')
    plt.close()
    chart_stream.seek(0)
    return chart_stream

def add_title_block(sheet, management_zone, start_time, metrics, num_servers):
    """
    Add a title block to the top of the first sheet with report details.
    """
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    duration = "Weekly" if "1w" in start_time else "Daily" if "1d" in start_time else "Custom"
    title_content = [
        f"Team Name/Management Zone: {management_zone}",
        f"Report Time: {report_time}",
        f"Report Duration: {start_time}",
        f"Number of Servers: {num_servers}",
        f"Resources: {', '.join(metrics)}",
    ]
    for idx, line in enumerate(title_content, start=1):
        sheet.cell(row=idx, column=1, value=line)
        sheet.cell(row=idx, column=1).font = Font(bold=True)

def generate_excel_report(aggregated_data, management_zone, start_time, metrics, output_filename):
    """
    Generate a new Excel report with a title block and charts.
    """
    workbook = Workbook()
    title_sheet = workbook.active
    title_sheet.title = "Report Summary"
    num_servers = len(aggregated_data)
    add_title_block(title_sheet, management_zone, start_time, metrics, num_servers)
    for dimension, raw_data in aggregated_data.items():
        df = normalize_metric_data(raw_data)
        sheet = workbook.create_sheet(title=str(dimension)[:31])
        for r_idx, row in enumerate(df.itertuples(index=False), start=1):
            for c_idx, value in enumerate(row, start=1):
                sheet.cell(row=r_idx, column=c_idx, value=value)
    workbook.save(output_filename)
    print(f"Excel report saved to {output_filename}")

def main():
    Tk().withdraw()
    print("Enter Dynatrace API Details:")
    api_url = input("Enter the Dynatrace Metrics API URL: ").strip()
    api_token = input("Enter your API Token: ").strip()
    management_zone = input("Enter the Management Zone: ").strip()
    start_time = input("Enter the start time (e.g., now-1w): ").strip()
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
    headers = {
        "Authorization": f"Api-Token {api_token}",
        "Accept": "application/json; charset=utf-8"
    }
    aggregated_data = {}
    for metric_name, metric_selector in metrics.items():
        print(f"Fetching data for {metric_name}...")
        metric_data = fetch_metrics(api_url, headers, metric_selector, 'type("HOST")', management_zone, start_time)
        aggregated_data[metric_name] = metric_data
    output_filename = "Aggregated_Dynatrace_Report.xlsx"
    print("Generating the Excel report...")
    generate_excel_report(aggregated_data, management_zone, start_time, metrics, output_filename)

if __name__ == "__main__":
    main()
