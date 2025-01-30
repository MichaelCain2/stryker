  1 | import requests
  2 | import matplotlib.pyplot as plt
  3 | from matplotlib.dates import DateFormatter, date2num
  4 | from io import BytesIO
  5 | from reportlab.pdfgen import canvas
  6 | from reportlab.lib.pagesizes import letter
  7 | from datetime import datetime
  8 | import logging
  9 | import tempfile
 10 | import re
 11 | 
 12 | # Configure logging with timestamp in filename
 13 | log_filename = f"MetricAPI2PDF_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
 14 | logging.basicConfig(filename=log_filename, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
 15 | 
 16 | # Metrics definition
 17 | metrics = {
 18 |     "Processor": "builtin:host.cpu.usage",
 19 |     "Memory": "builtin:host.mem.usage",
 20 |     "Average Disk Used Percentage": "builtin:host.disk.usedPct",
 21 |     "Average Disk Utilization Time": "builtin:host.disk.utilTime",
 22 |     "Disk Write Time Per Second": "builtin:host.disk.writeTime",
 23 |     "Average Disk Queue Length": "builtin:host.disk.queueLength",
 24 |     "Network Adapter In": "builtin:host.net.nic.trafficIn",
 25 |     "Network Adapter Out": "builtin:host.net.nic.trafficOut"
 26 | }
 27 | 
 28 | def fetch_metrics(api_url, headers, metric, mz_selector, agg_time, resolution):
 29 |     """
 30 |     Fetch metrics from the Dynatrace API.
 31 |     """
 32 |     resolution_param = f"&resolution={resolution}" if resolution else ""
 33 |     query_url = f'{api_url}?metricSelector={metric}&from={agg_time}&entitySelector=type("HOST")&mzSelector=mzName("{mz_selector}"){resolution_param}'
 34 |     logging.debug(f"Fetching metrics with URL: {query_url}")
 35 |     response = requests.get(query_url, headers=headers)
 36 |     response.raise_for_status()
 37 |     return response.json()
 38 | 
 39 | def fetch_host_name(api_url, headers, host_id):
 40 |     """
 41 |     Fetch human-readable hostname from the Entities API.
 42 |     """
 43 |     base_url = api_url.split("metrics/query")[0]  # Remove /metrics/query from the base URL
 44 |     url = f"{base_url}/entities/{host_id}"
 45 |     try:
 46 |         response = requests.get(url, headers=headers)
 47 |         response.raise_for_status()
 48 |         entity_data = response.json()
 49 |         display_name = entity_data.get("displayName", host_id)  # Fallback to host_id if displayName is missing
 50 |         logging.debug(f"Resolved {host_id} to {display_name}")
 51 |         return display_name
 52 |     except requests.exceptions.RequestException as e:
 53 |         logging.warning(f"Error fetching display name for {host_id}: {e}")
 54 |         return host_id
 55 | 
 56 | def group_data(raw_data, api_url, headers):
 57 |     """
 58 |     Group metrics data by resolved host names and metrics.
 59 |     """
 60 |     grouped_data = {}
 61 |     host_name_cache = {}
 62 | 
 63 |     for metric_name, metric_data in raw_data.items():
 64 |         for data_point in metric_data.get('result', [])[0].get('data', []):
 65 |             host_id = data_point.get('dimensions', [None])[0]
 66 |             if not host_id:
 67 |                 logging.warning(f"Missing host ID in data point: {data_point}")
 68 |                 continue
 69 | 
 70 |             if host_id not in host_name_cache:
 71 |                 host_name_cache[host_id] = fetch_host_name(api_url, headers, host_id)
 72 | 
 73 |             resolved_name = host_name_cache.get(host_id, host_id)
 74 |             timestamps = data_point.get('timestamps', [])
 75 |             values = data_point.get('values', [])
 76 | 
 77 |             if resolved_name not in grouped_data:
 78 |                 grouped_data[resolved_name] = {}
 79 | 
 80 |             grouped_data[resolved_name][metric_name] = {"timestamps": timestamps, "values": values}
 81 | 
 82 |     logging.debug(f"Grouped Data: {grouped_data}")
 83 |     return grouped_data
 84 | 
 85 | def generate_graph(timestamps, values, metric_name):
 86 |     """
 87 |     Generate a graph for the given metric.
 88 |     """
 89 |     try:
 90 |         if not timestamps or all(v is None for v in values):
 91 |             logging.warning(f"Cannot generate graph for metric '{metric_name}': Missing or invalid data.")
 92 |             return None
 93 | 
 94 |         datetime_timestamps = [datetime.fromtimestamp(ts / 1000) for ts in timestamps]
 95 | 
 96 |         plt.figure(figsize=(8, 4))
 97 |         plt.plot(datetime_timestamps, values, label=metric_name, marker='o', color='blue')
 98 |         plt.title(metric_name)
 99 |         plt.xlabel("")
100 |         plt.ylabel("")
101 |         plt.grid(True)
102 |         plt.legend()
103 | 
104 |         ax = plt.gca()
105 |         ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
106 |         plt.xticks(rotation=0)
107 | 
108 |         buffer = BytesIO()
109 |         plt.savefig(buffer, format='png')
110 |         buffer.seek(0)
111 |         plt.close()
112 |         logging.info(f"Graph successfully generated for metric '{metric_name}'.")
113 |         return buffer
114 |     except Exception as e:
115 |         logging.error(f"Error generating graph for metric '{metric_name}': {e}")
116 |         return None
117 | 
118 | def create_pdf(grouped_data, management_zone, agg_time, output_pdf):
119 |     """
120 |     Create a PDF report organized by host, embedding the graphs for each metric.
121 |     """
122 |     c = canvas.Canvas(output_pdf, pagesize=letter)
123 |     width, height = letter
124 |     margin = 55
125 |     chart_height = 120
126 |     chart_spacing = 15
127 |     y_position = height - margin
128 | 
129 |     def start_new_page():
130 |         nonlocal y_position
131 |         c.showPage()
132 |         y_position = height - margin
133 |         c.setFont("Helvetica-Bold", 12)
134 |         c.drawString(margin, height - 50, f"Team Name/Management Zone: {management_zone}")
135 | 
136 |     # Add initial header
137 |     c.setFont("Helvetica-Bold", 12)
138 |     c.drawString(margin, height - 50, f"Team Name/Management Zone: {management_zone}")
139 |     c.drawString(margin, height - 65, f"Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
140 |     c.drawString(margin, height - 85, f"Aggregation Period: {agg_time}")
141 |     c.drawString(margin, height - 100, f"Number of Hosts/Servers: {len(grouped_data)}")
142 |     c.drawString(margin, height - 115, "Resources/Metrics:")
143 | 
144 |     y_position = height - 130
145 |     for metric_name in metrics.keys():
146 |         c.drawString(margin + 20, y_position, f"- {metric_name}")
147 |         y_position -= 15
148 | 
149 |     y_position -= 20
150 | 
151 |     # Host-Specific Sections (unchanged)
152 |     for host_name, metrics_data in grouped_data.items():
153 |         start_new_page()
154 |         c.setFont("Helvetica-Bold", 14)
155 |         y_position -= 20
156 |         c.drawString(margin, y_position, f"Host: {host_name}")
157 |         y_position -= 30
158 | 
159 |         for metric_name, data in metrics_data.items():
160 |             timestamps = data.get('timestamps', [])
161 |             values = data.get('values', [])
162 | 
163 |             if not timestamps or all(v is None for v in values):
164 |                 continue
165 | 
166 |             graph = generate_graph(timestamps, values, metric_name)
167 |             if graph is None:
168 |                 continue
169 | 
170 |             with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_image:
171 |                 temp_image.write(graph.getvalue())
172 |                 temp_image_path = temp_image.name
173 | 
174 |             if y_position - chart_height - chart_spacing < margin:
175 |                 start_new_page()
176 | 
177 |             c.drawImage(temp_image_path, margin, y_position - chart_height, width=450, height=chart_height)
178 |             y_position -= (chart_height + chart_spacing)
179 | 
180 |     c.save()
181 | 
182 | def sanitize_filename(filename):
183 |     """
184 |     Sanitize the filename by replacing specific patterns while preserving other conventions.
185 |     """
186 |     if ':' in filename:
187 |         filename = re.sub(r'\s*:\s*', '_', filename)
188 |     filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
189 |     filename = filename.strip()
190 |     return filename
191 | 
192 | if __name__ == "__main__":
193 |     API_URL = input("Enter API URL: ").strip()
194 |     API_TOKEN = input("Enter API Token: ").strip()
195 |     MZ_SELECTOR = input("Enter Management Zone Name: ").strip()
196 |     AGG_TIME = input("Enter Aggregation Time (e.g., now-1m, now-5m, now-1h, now-1d): ").strip()
197 |     RESOLUTION = input("Enter Resolution (e.g., 1m, 5m, 1h, 1d, or leave blank for default): ").strip()
198 | 
199 |     HEADERS = {"Authorization": f"Api-Token {API_TOKEN}"}
200 | 
201 |     raw_data = {}
202 |     for metric_name, metric_selector in metrics.items():
203 |         raw_data[metric_name] = fetch_metrics(API_URL, HEADERS, metric_selector, MZ_SELECTOR, AGG_TIME, RESOLUTION)
204 | 
205 |     grouped_data = group_data(raw_data, API_URL, HEADERS)
206 |     OUTPUT_PDF = f"{sanitize_filename(MZ_SELECTOR)}-Dynatrace_Metrics_Report-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
207 |     create_pdf(grouped_data, MZ_SELECTOR, AGG_TIME, OUTPUT_PDF)
208 | 
209 |     print(f"PDF report generated: {OUTPUT_PDF}")
