import requests  # This is the internets errand boy. It is used to fetch stuff from URLs and we are using it in part to query the API URL
import matplotlib.pyplot as plt  # This is the artist. We are using it to draw the charts ref -https://matplotlib.org/-
from matplotlib.dates import DateFormatter, date2num  # Helps make time stuff readable converts this format like 17377632000, to 9/3/2520, 8:00:00 PM
from io import BytesIO  # Digital notepad for storing datas
from reportlab.pdfgen import canvas  # This is the PDF Architect
from reportlab.lib.pagesizes import letter  # Manages Page Size and specific standards
from matplotlib.ticker import FormatStrFormatter #Used to work with scientific numbering issues
from datetime import datetime  # Official TIme Keeper. In case some date/time issues still need working on, this is the gladiator
import logging  # Every good engineer needs logging. And so I included it
import tempfile  # To pull, read, manipulate the datas from where we get them to where they go, this is that temp space
import re  # My "Bounder" Kicks out unwanted characters EX: ABC: BVCX_1234 kicks out that : and puts in an _ in its place

# NEW: Import sys and time for progress indicator and timing logic
import sys  # NOTES: Used for outputting progress in the same line.
import time  # NOTES: Used for timing and ETA calculation.

# Configure logging with timestamp in filename
log_filename = f"MetricAPI2PDF_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Metrics definition that gets pulled via the API. These can be edited to pull mostly any of the 10,000 plus available metrics. Just save yourself a
# copy and edit. I have another version that asks for these but that is assuming the operator know them and understands the format to insert them.
# Even I am a little unsure at times so stick with these to start with and adjust as
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

#Needed Library for Y Lable as many are different
y_label_map = {
    "Processor": "Percentage across all CPUs",
    "Memory": "Percentage",
    "Average Disk Used Percentage": "Percentage",
    "Average Disk Utilization Time": "milli/micro second",
    "Disk Write Time Per Second": "MiB per Second",
    "Average Disk Queue Length": "> 1(one) is of Concern",
    "Network Adapter In": "MB per sec",
    "Network Adapter Out": "MB per sec"
}

# NEW: Define a progress indicator helper function using only built-in modules. Al and I wanted a timer. Without some additional crazy coding, this is the best I can currently provide
def print_progress(current, total, start_time, prefix='Progress'):
    """
    Prints a progress bar with percentage complete, elapsed time, and estimated time remaining.
    #NOTES: This function is added to provide visual timing feedback to the user.
    """
    elapsed = time.time() - start_time
    progress = current / total
    eta = (elapsed / progress - elapsed) if progress > 0 else 0

    bar_length = 30  # adjust the length of the progress bar as needed
    filled_length = int(round(bar_length * progress))
    bar = '=' * filled_length + '-' * (bar_length - filled_length)

    sys.stdout.write(f'\r{prefix}: |{bar}| {progress*100:5.1f}% Elapsed: {elapsed:5.1f}s ETA: {eta:5.1f}s')
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write('\n')

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

# Dynatrace stores entities, like HOST-xxxxxxx so to convert that to hostname1234, we need to get the entity and go query entities API to get the answer.
# That is what is happening here. Just getting the data. Not yet do the majick
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

# Here is where we take all that data from the API, that comes out in JSON, and turns it in to a usable format for simpler use when creating the charts in the PDF
def group_data(raw_data, api_url, headers):
    """
    Group metrics data by resolved host names and metrics.
    """
    grouped_data = {}
    host_name_cache = {}

    for metric_name, metric_data in raw_data.items():
        for data_point in metric_data.get('result', [])[0].get('data', []):
            host_id = data_point.get('dimensions', [None])[0]
            if not host_id:
                logging.warning(f"Missing host ID in data point: {data_point}")
                continue

            if host_id not in host_name_cache:
                host_name_cache[host_id] = fetch_host_name(api_url, headers, host_id)

            resolved_name = host_name_cache.get(host_id, host_id)
            timestamps = data_point.get('timestamps', [])
            values = data_point.get('values', [])

            if resolved_name not in grouped_data:
                grouped_data[resolved_name] = {}

            grouped_data[resolved_name][metric_name] = {"timestamps": timestamps, "values": values}

    logging.debug(f"Grouped Data: {grouped_data}")
    return grouped_data

# This is the majick part of the journey. Here it starts to use the datas from the hostname part and the groups data part into a chart that can be put into the PDF in a human readable way. I
# do not pretend to understand this wizardry completely but spending enough time on the matplotlib site and asking other pY wizards for suggestions, it did provide enough instruction
def generate_graph(timestamps, values, metric_name):
    """
    Generate a graph for the given metric, applying necessary scaling adjustments.
    """
    try:
        if not timestamps or all(v is None for v in values):
            logging.warning(f"Cannot generate graph for metric '{metric_name}': Missing or invalid data.")  # You will see this in the logs if you look or like
            #I do tail - f the .log but in most cases does not cause issues
            return None

        datetime_timestamps = [datetime.fromtimestamp(ts / 1000) for ts in timestamps]  # Clocky stuff because HAL or Enterprises COmputer are not reading the output. Just us humans

        # Apply scaling for Processor metric P.S. I might need to adjust some others but stopped here for now
        if metric_name == "Processor":
            values = [v * 100 for v in values]  # Convert to percentage (1-6 -> 100-600)
        elif metric_name == "Average Disk Used Percentage":
            values = [v * 1000 for v in values] # Change to x1000 percentage
        elif metric_name == "Disk Write Time Per Second":
            values = [v * 10 for v in values]
        elif metric_name in ["Network Adapter In", "Network Adapter Out"]:
            #NEW: Converting bits per second to something more palatible
            # If you need a somewhat different output, adjust the 1e6 divsor to what makes sense to you
            values = [v /1024 for v in values]

        plt.figure(figsize=(8, 4))  # Original chart dimensions restored. This is the chart size on the PDF page. Not to be confused with otther sizes
        plt.plot(datetime_timestamps, values, label=metric_name, marker='o', color='blue')
        plt.title(metric_name)
        plt.xlabel("")
        plt.ylabel(y_label_map.get(metric_name, "millisecond"))  # Same as above. Might want to adjust others but for now I am happy with current MVP output.
                   
        plt.grid(True)  # Turn grid off and on

        # Adjusted legend size and spacing. This is the little legend window. Still not sure it is useful but sems others in the FAQs are so for now, I left it
        plt.legend(
            loc="upper right",
            fontsize="medium",  # Increased font size
            borderaxespad=1.5,  # Added padding around the legend box
            labelspacing=1.0  # Increased spacing between legend entries
        )

        ax = plt.gca()  # -adjusting from time to date
        ax.xaxis.set_major_formatter(DateFormatter("%d-%b-%y"))  # -adjusting from time to date. Time be like %H:%M and depending on the aggregation time, you may want to adjust tis. For my now-1w timeframe I want date
        plt.xticks(rotation=15)  # Adjusting rotation to fit chart in such a way as to still be readable

# New Work with Network Metrics when scientificate symbols happen
        if metric_name in ["Network Adapter In", "Network Adapter Out"]:
            ax.ticklabel_format(style='plain', axis='y') #Disables the Scientific Notation 1e6, 1e8, etc
            ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))

        buffer = BytesIO()  # Some of that wizardry I am slowly wrapping my head around but am not the SME
        plt.savefig(buffer, format='png')  # The charts on the PDF pages are png's
        buffer.seek(0)
        plt.close()
        logging.info(f"Graph successfully generated for metric '{metric_name}'.")
        return buffer
    except Exception as e:
        logging.error(f"Error generating graph for metric '{metric_name}': {e}")
        return None

# The file name is created based on initial inputs and as such make an ugly file name, so I cleaned it up
def sanitize_filename(filename):
    """
    Sanitize the filename by replacing specific patterns while preserving other conventions.
    """
    if ':' in filename:
        filename = re.sub(r'\s*:\s*', '_', filename)  # Replace colon and surrounding spaces with _
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)  # Remove invalid characters
    filename = filename.strip()  # Strip leading/trailing spaces
    return filename

# THE MAJICK
def create_pdf(grouped_data, management_zone, agg_time, output_pdf):
    """
    Create a PDF report organized by host, embedding the graphs for each metric.
    """
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter
    margin = 55
    chart_height = 135
    chart_spacing = 15
    y_position = height - margin

    def start_new_page():
        nonlocal y_position
        c.showPage()
        y_position = height - margin
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, height - 50, f"Team Name/Management Zone: {management_zone}")

    # Add initial header
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, height - 50, f"Team Name/Management Zone: {management_zone}")
    c.drawString(margin, height - 65, f"Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(margin, height - 80, f"Aggregation Period: {agg_time}")
    c.drawString(margin, height - 95, f"Number of Hosts/Servers: {len(grouped_data)}")
    c.drawString(margin, height - 110, "Resources/Metrics:")

    y_position = height - 130
    for metric_name in metrics.keys():
        c.drawString(margin + 20, y_position, f"- {metric_name}")
        y_position -= 15

    y_position -= 20

    # NEW: Wrap host processing loop with progress indicator.
    total_hosts = len(grouped_data)  # NOTES: Total number of hosts for progress.
    host_start_time = time.time()  # NOTES: Start time for host processing. Al and I wanted a timer. Without some additional crazy coding, this is the best I can currently provide
    for idx, (host_name, metrics_data) in enumerate(grouped_data.items(), start=1):
        start_new_page()
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
                start_new_page()

            c.drawImage(temp_image_path, margin, y_position - chart_height, width=450, height=chart_height)
            y_position -= (chart_height + chart_spacing)

        # Update progress for host processing
        print_progress(idx, total_hosts, host_start_time, prefix='Processing hosts')  # NOTES: Shows progress for each host processed. Al and I wanted a timer. Without some additional crazy coding, this is the best I can currently provide

    c.save()

if __name__ == "__main__":
    # NEW: Record overall start time for the script.
    overall_start = time.time()  # NOTES: Overall script timer start. Al and I wanted a timer. Without some additional crazy coding, this is the best I can currently provide

    API_URL = input("Enter API URL: ").strip()
    API_TOKEN = input("Enter API Token: ").strip()
    MZ_SELECTOR = input("Enter Management Zone Name: ").strip()
    AGG_TIME = input("Enter Aggregation Time: ").strip()
    RESOLUTION = input("Enter Resolution: ").strip()

    HEADERS = {"Authorization": f"Api-Token {API_TOKEN}"}

    # NEW: Replace dictionary comprehension with a loop that includes a progress indicator for fetching metrics.
    raw_data = {}
    fetch_start_time = time.time()  # NOTES: Start time for fetching metrics.
    total_metrics = len(metrics)  # NOTES: Total number of metrics for progress.
    for idx, (metric_name, metric_selector) in enumerate(metrics.items(), start=1):
        raw_data[metric_name] = fetch_metrics(API_URL, HEADERS, metric_selector, MZ_SELECTOR, AGG_TIME, RESOLUTION)
        print_progress(idx, total_metrics, fetch_start_time, prefix='Fetching metrics')  # NOTES: Shows progress for each metric fetched.

    grouped_data = group_data(raw_data, API_URL, HEADERS)
    OUTPUT_PDF = f"{sanitize_filename(MZ_SELECTOR)}-Dynatrace_Metrics_Report-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"

    # NEW: Logic around create_pdf. Only generate PDF if there is grouped data.
    if grouped_data:
        print("Starting PDF generation...")  # NOTES: Indicate start of PDF generation.
        pdf_start_time = time.time()  # NOTES: Start time for PDF generation.
        create_pdf(grouped_data, MZ_SELECTOR, AGG_TIME, OUTPUT_PDF)
        pdf_end_time = time.time()  # NOTES: End time for PDF generation.
        pdf_generation_time = pdf_end_time - pdf_start_time
        print(f"PDF generation took: {pdf_generation_time:.2f} seconds")  # NOTES: Print PDF generation time.
        print(f"PDF report generated: {OUTPUT_PDF}")
    else:
        print("No data available to generate PDF.")  # NOTES: Handle the case where no grouped data was returned.

    # NEW: Record overall end time and print total running time.
    overall_end = time.time()  # NOTES: Overall script timer end.
    total_running_time = overall_end - overall_start
    print(f"Total running time: {total_running_time:.2f} seconds")  # NOTES: Display total script running time.

    # THE END OF THE MAJICK
