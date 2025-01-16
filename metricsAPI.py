1   import requests
2   import json
3   from openpyxl import Workbook
4   from openpyxl.drawing.image import Image
5   from openpyxl.styles import Font
6   import pandas as pd
7   from io import BytesIO
8   import matplotlib.pyplot as plt
9   from datetime import datetime
10  from tkinter import Tk, filedialog

12  # Define thresholds for green, yellow, red
13  thresholds = {
14      "Processor": {"green": 50, "yellow": 90, "red": 100},
15      "Memory": {"green": 30, "yellow": 95, "red": 100},
16      "Average Disk Used Percentage": {"green": 60, "yellow": 85, "red": 100},
17      "Average Disk Idletime Percentage": {"green": 60, "yellow": 85, "red": 100},
18      "Disk Transfer Per Second": {"green": 60, "yellow": 85, "red": 100},
19      "Average Disk Queue Length": {"green": 60, "yellow": 85, "red": 100},
20      "Network Adapter In": {"green": 20, "yellow": 70, "red": 100},
21      "Network Adapter Out": {"green": 20, "yellow": 70, "red": 100}
22  }

24  def fetch_metrics(api_url, headers, metric, entity_filter, management_zone, start_time):
25      """
26      Fetches metrics from Dynatrace using the Metrics API.
27      """
28      url = f"{api_url}?metricSelector={metric}&from={start_time}&entitySelector={entity_filter}&mzSelector=mzName(\"{management_zone}\")"
29      print(f"Fetching data from URL: {url}")  # Debugging: Print the crafted URL
30      response = requests.get(url, headers=headers)
31      response.raise_for_status()  # Ensure the request was successful
32      return response.json()

34  def normalize_metric_data(metric_data):
35      """
36      Normalize and flatten the fetched metric data for easy writing to Excel.
37      """
38      normalized_data = []
39      for item in metric_data.get('items', []):
40          for datapoint in item.get('dataPoints', []):
41              normalized_data.append({
42                  "Time": datapoint[0],  # Timestamp
43                  "Value": datapoint[1]  # Metric value
44              })
45      return pd.DataFrame(normalized_data)

47  def create_chart(chart_data, title, metric_name):
48      """
49      Create a bar chart for a given metric and save it to a BytesIO stream.
50      Apply color coding based on thresholds.
51      """
52      colors = []
53      if metric_name in chart_data:
54          for value in chart_data[metric_name]:
55              if value <= thresholds[metric_name]["green"]:
56                  colors.append("green")
57              elif value <= thresholds[metric_name]["yellow"]:
58                  colors.append("yellow")
59              else:
60                  colors.append("red")
62      plt.figure(figsize=(8, 4))
63      plt.bar(chart_data['Time'], chart_data[metric_name], color=colors)
64      plt.title(title)
65      plt.xlabel('Time')
66      plt.ylabel(metric_name)
67      plt.xticks(rotation=45, ha='right')
69      chart_stream = BytesIO()
70      plt.tight_layout()
71      plt.savefig(chart_stream, format='png')
72      plt.close()
74      chart_stream.seek(0)
75      return chart_stream

77  def add_title_block(sheet, management_zone, start_time, metrics, num_servers):
78      """
79      Add a title block to the top of the first sheet with report details.
80      """
81      report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
82      duration = "Weekly" if "1w" in start_time else "Daily" if "1d" in start_time else "Custom"
84      title_content = [
85          f"Team Name/Management Zone: {management_zone}",
86          f"Report Time: {report_time}",
87          f"Report Duration: {start_time}",
88          f"Number of Servers: {num_servers}",
89          f"Resources: {', '.join(metrics)}",
90      ]
92      for idx, line in enumerate(title_content, start=1):
93          sheet.cell(row=idx, column=1, value=line)
94          sheet.cell(row=idx, column=1).font = Font(bold=True)  # Bold font

96  def generate_excel_report(aggregated_data, management_zone, start_time, metrics, output_filename):
97      """
98      Generate a new Excel report with a title block and charts.
99      """
100     workbook = Workbook()
101     title_sheet = workbook.active
102     title_sheet.title = "Report Summary"
104     num_servers = len(aggregated_data)
105     add_title_block(title_sheet, management_zone, start_time, metrics, num_servers)
107     for dimension, raw_data in aggregated_data.items():
108         df = normalize_metric_data(raw_data)
109         sheet = workbook.create_sheet(title=str(dimension)[:31])
110         for r_idx, row in enumerate(df.itertuples(index=False), start=1):
111             for c_idx, value in enumerate(row, start=1):
112                 sheet.cell(row=r_idx, column=c_idx, value=value)
114     workbook.save(output_filename)
115     print(f"Excel report saved to {output_filename}")

117  def main():
118      Tk().withdraw()
120      print("Enter Dynatrace API Details:")
121      api_url = input("Enter the Dynatrace Metrics API URL: ").strip()
122      api_token = input("Enter your API Token: ").strip()
123      management_zone = input("Enter the Management Zone: ").strip()
124      start_time = input("Enter the start time (e.g., now-1w): ").strip()
126      metrics = {
127          "Processor": "builtin:host.cpu.usage",
128          "Memory": "builtin:host.mem.usage",
129          "Average Disk Used Percentage": "builtin:host.disk.usedPct",
130          "Average Disk Idletime Percentage": "com.dynatrace.extension.host-observability.disk.usage.idle.percent",
131          "Disk Transfer Per Second": "com.dynatrace.extension.host-observability.disk.transfer.persec",
132          "Average Disk Queue Length": "builtin:host.disk.queueLength",
133          "Network Adapter In": "builtin:host.net.nic.trafficIn",
134          "Network Adapter Out": "builtin:host.net.nic.trafficOut"
135      }
137      headers = {
138          "Authorization": f"Api-Token {api_token}",
139          "Accept": "application/json; charset=utf-8"
140      }
142      aggregated_data = {}
143      for metric_name, metric_selector in metrics.items():
144          print(f"Fetching data for {metric_name}...")
145          metric_data = fetch_metrics(api_url, headers, metric_selector, 'type("HOST")', management_zone, start_time)
146          aggregated_data[metric_name] = metric_data
148      output_filename = "Aggregated_Dynatrace_Report.xlsx"
149      print("Generating the Excel report...")
150      generate_excel_report(aggregated_data, management_zone, start_time, metrics, output_filename)

152  if __name__ == "__main__":
153      main()
