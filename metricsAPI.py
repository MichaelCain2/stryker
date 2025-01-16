import requests  # 1
import json  # 2
from openpyxl import Workbook  # 3
from openpyxl.drawing.image import Image  # 4
from openpyxl.styles import Font  # 5
import pandas as pd  # 6
from io import BytesIO  # 7
import matplotlib.pyplot as plt  # 8
from datetime import datetime  # 9
from tkinter import Tk, filedialog  # 10

# Define thresholds for green, yellow, red  # 12
thresholds = {  # 13
    "Processor": {"green": 50, "yellow": 90, "red": 100},  # 14
    "Memory": {"green": 30, "yellow": 95, "red": 100},  # 15
    "Average Disk Used Percentage": {"green": 60, "yellow": 85, "red": 100},  # 16
    "Average Disk Idletime Percentage": {"green": 60, "yellow": 85, "red": 100},  # 17
    "Disk Transfer Per Second": {"green": 60, "yellow": 85, "red": 100},  # 18
    "Average Disk Queue Length": {"green": 60, "yellow": 85, "red": 100},  # 19
    "Network Adapter In": {"green": 20, "yellow": 70, "red": 100},  # 20
    "Network Adapter Out": {"green": 20, "yellow": 70, "red": 100}  # 21
}  # 22

def fetch_metrics(api_url, headers, metric, entity_filter, management_zone, start_time):  # 24
    """Fetches metrics from Dynatrace using the Metrics API."""  # 25
    url = f"{api_url}?metricSelector={metric}&from={start_time}&entitySelector={entity_filter}&mzSelector=mzName(\"{management_zone}\")"  # 28
    print(f"Fetching data from URL: {url}")  # Debugging: Print the crafted URL  # 29
    response = requests.get(url, headers=headers)  # 30
    response.raise_for_status()  # Ensure the request was successful  # 31
    return response.json()  # 32

def normalize_metric_data(metric_data):  # 34
    """Normalize and flatten the fetched metric data for easy writing to Excel."""  # 35
    normalized_data = []  # 38
    for item in metric_data.get('items', []):  # 39
        for datapoint in item.get('dataPoints', []):  # 40
            normalized_data.append({  # 41
                "Time": datapoint[0],  # Timestamp  # 42
                "Value": datapoint[1]  # Metric value  # 43
            })  # 44
    return pd.DataFrame(normalized_data)  # 45

def create_chart(chart_data, title, metric_name):  # 47
    """Create a bar chart for a given metric and save it to a BytesIO stream. Apply color coding based on thresholds."""  # 48
    colors = []  # 52
    if metric_name in chart_data:  # 53
        for value in chart_data[metric_name]:  # 54
            if value <= thresholds[metric_name]["green"]:  # 55
                colors.append("green")  # 56
            elif value <= thresholds[metric_name]["yellow"]:  # 57
                colors.append("yellow")  # 58
            else:  # 59
                colors.append("red")  # 60
    plt.figure(figsize=(8, 4))  # 62
    plt.bar(chart_data['Time'], chart_data[metric_name], color=colors)  # 63
    plt.title(title)  # 64
    plt.xlabel('Time')  # 65
    plt.ylabel(metric_name)  # 66
    plt.xticks(rotation=45, ha='right')  # 67
    chart_stream = BytesIO()  # 69
    plt.tight_layout()  # 70
    plt.savefig(chart_stream, format='png')  # 71
    plt.close()  # 72
    chart_stream.seek(0)  # 74
    return chart_stream  # 75

def add_title_block(sheet, management_zone, start_time, metrics, num_servers):  # 77
    """Add a title block to the top of the first sheet with report details."""  # 78
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 81
    duration = "Weekly" if "1w" in start_time else "Daily" if "1d" in start_time else "Custom"  # 82
    title_content = [  # 84
        f"Team Name/Management Zone: {management_zone}",  # 85
        f"Report Time: {report_time}",  # 86
        f"Report Duration: {start_time}",  # 87
        f"Number of Servers: {num_servers}",  # 88
        f"Resources: {', '.join(metrics)}",  # 89
    ]  # 90
    for idx, line in enumerate(title_content, start=1):  # 92
        sheet.cell(row=idx, column=1, value=line)  # 93
        sheet.cell(row=idx, column=1).font = Font(bold=True)  # Bold font  # 94

def generate_excel_report(aggregated_data, management_zone, start_time, metrics, output_filename):  # 96
    """Generate a new Excel report with a title block and charts."""  # 97
    workbook = Workbook()  # 100
    title_sheet = workbook.active  # 101
    title_sheet.title = "Report Summary"  # 102
    num_servers = len(aggregated_data)  # 104
    add_title_block(title_sheet, management_zone, start_time, metrics, num_servers)  # 105
    for dimension, raw_data in aggregated_data.items():  # 107
        df = normalize_metric_data(raw_data)  # 108
        sheet = workbook.create_sheet(title=str(dimension)[:31])  # 109
        for r_idx, row in enumerate(df.itertuples(index=False), start=1):  # 110
            for c_idx, value in enumerate(row, start=1):  # 111
                sheet.cell(row=r_idx, column=c_idx, value=value)  # 112
    workbook.save(output_filename)  # 114
    print(f"Excel report saved to {output_filename}")  # 115

def main():  # 117
    Tk().withdraw()  # 118
    print("Enter Dynatrace API Details:")  # 120
    api_url = input("Enter the Dynatrace Metrics API URL: ").strip()  # 121
    api_token = input("Enter your API Token: ").strip()  # 122
    management_zone = input("Enter the Management Zone: ").strip()  # 123
    start_time = input("Enter the start time (e.g., now-1w): ").strip()  # 124
    metrics = {  # 126
        "Processor": "builtin:host.cpu.usage",  # 127
        "Memory": "builtin:host.mem.usage",  # 128
        "Average Disk Used Percentage": "builtin:host.disk.usedPct",  # 129
        "Average Disk Idletime Percentage": "com.dynatrace.extension.host-observability.disk.usage.idle.percent",  # 130
        "Disk Transfer Per Second": "com.dynatrace.extension.host-observability.disk.transfer.persec",  # 131
        "Average Disk Queue Length": "builtin:host.disk.queueLength",  # 132
        "Network Adapter In": "builtin:host.net.nic.trafficIn",  # 133
        "Network Adapter Out": "builtin:host.net.nic.trafficOut"  # 134
    }  # 135
    headers = {  # 137
        "Authorization": f"Api-Token {api_token}",  # 138
        "Accept": "application/json; charset=utf-8"  # 139
    }  # 140
    aggregated_data = {}  # 142
    for metric_name, metric_selector in metrics.items():  # 143
        print(f"Fetching data for {metric_name}...")  # 144
        metric_data = fetch_metrics(api_url, headers, metric_selector, 'type("HOST")', management_zone, start_time)  # 145
        aggregated_data[metric_name] = metric_data  # 146
    output_filename = "Aggregated_Dynatrace_Report.xlsx"  # 148
    print("Generating the Excel report...")  # 149
    generate_excel_report(aggregated_data, management_zone, start_time, metrics, output_filename)  # 150

if __name__ == "__main__":  # 152
    main()  # 153
