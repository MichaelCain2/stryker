import requests
import pandas as pd
import matplotlib.pyplot as plt
from openpyxl import Workbook
 
# Define thresholds for green, yellow, red
thresholds = {
    "Processor": {"green": 50, "yellow": 90, "red": 100},
    "Memory": {"green": 30, "yellow": 95, "red": 100},
    "Average Disk Used Percentage": {"green": 60, "yellow": 85, "red": 100},
    "Average Disk Utilzation Time": {"green": 60, "yellow": 85, "red": 100},
    "Disk Write Time Per Second": {"green": 60, "yellow": 900, "red": 1000},
    "Average Disk Queue Length": {"green": 75, "yellow": 200, "red": 500},
    "Network Adapter In": {"green": 500000000, "yellow": 1000000000, "red": 1900000000},
    "Network Adapter Out": {"green": 500000000, "yellow": 2000000000, "red": 2500000000}
}
 
def fetch_metrics(api_url, headers, metric, entity_filter, mz_selector, start_time):
    """
    Fetches metrics from Dynatrace using the Metrics API.
    """
    # Construct URL with the required parameters
    url = f"{api_url}?metricSelector={metric}&from={start_time}&entitySelector={entity_filter}&mzSelector={mz_selector}"
    print(f"Fetching data from URL: {url}")  # Debugging: Print the crafted URL
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Ensure the request was successful
    return response.json()
 
def generate_report(data, output_filename):
    """
    Generates a report in Excel format with graphical representations.
    """
    # Initialize an Excel workbook
    writer = pd.ExcelWriter(output_filename, engine='openpyxl')
 
    # Process each metric's data
    for metric_name, metric_data in data.items():
        metric_result = metric_data.get("result", [])
        if not metric_result:
            print(f"No data found for {metric_name}. Skipping...")
            continue
 
        # Extract data for each dimension
        rows = []
        for result in metric_result:
            for data_point in result.get("data", []):
                dimension = data_point.get("dimensions", ["Unknown"])[0]
                timestamps = data_point.get("timestamps", [])
                values = data_point.get("values", [])
 
                # Combine timestamps and values into rows
                for ts, value in zip(timestamps, values):
                    rows.append({"Dimension": dimension, "Time": pd.to_datetime(ts, unit='ms'), metric_name: value})
 
        # Convert to DataFrame
        df = pd.DataFrame(rows)
 
        if df.empty:
            print(f"No valid data for {metric_name}. Skipping...")
            continue
 
        # Save to Excel
        df.to_excel(writer, sheet_name=metric_name[:31], index=False)  # Sheet names max 31 characters
 
        # Create a graph for each metric
        plt.figure(figsize=(10, 6))
        for dimension in df["Dimension"].unique():
            dimension_data = df[df["Dimension"] == dimension]
            plt.plot(dimension_data["Time"], dimension_data[metric_name], label=dimension)
        plt.title(f"Metrics: {metric_name}")
        plt.xlabel("Time")
        plt.ylabel("Value")
        plt.legend()
        plt.grid(True)
        plt.savefig(f"{metric_name}.png")
        plt.close()
 
    # Save the Excel file
    writer.close()
 
def fetch_host_name(api_url, headers, host_id):
    """
    Fetch human-readable hostname.
    """
    base_url = api_url.split("metrics/query")[0]  # This removes /metrics blah from query
    url = f"{base_url}/entities/{host_id}"
 
    try:
        # Query Entities API
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for HTTP issues
 
        # Parse the JSON response
        entity_data = response.json()
        display_name = entity_data.get("displayName", host_id)  # Fallback to host_id if displayName is missing
 
        print(f"Resolved {host_id} to {display_name}")
        return display_name
    except requests.exceptions.RequestException as e:
        # Handle errors gracefully and fallback to host_id
        print(f"Error fetching display name for {host_id}: {e}")
        return host_id
 
def main():
    # User inputs
    print("Enter Dynatrace API Details:")
    api_base_url = input("Enter the Dynatrace Metrics API URL: ").strip()
    api_token = input("Enter your API Token: ").strip()
    management_zone = input("Enter the Management Zone (e.g., ABC: VASI_1234): ").strip()
    start_time = input("Enter the start time (e.g., now-1w): ").strip()
 
    headers = {
        "Authorization": f"Api-Token {api_token}",
        "Accept": "application/json; charset=utf-8"
    }
 
    # Metrics to query
    metrics = {
        "Processor": "builtin:host.cpu.usage",
        "Memory": "builtin:host.mem.usage",
        "Average Disk Used Percentage": "builtin:host.disk.usedPct",
        "Average Disk Utilzation Time": "builtin:host.disk.utilTime",
        "Disk Write Time Per Second": "builtin:host.disk.writeTime",
        "Average Disk Queue Length": "builtin:host.disk.queueLength",
        "Network Adapter In": "builtin:host.net.nic.trafficIn",
        "Network Adapter Out": "builtin:host.net.nic.trafficOut"
    }
 
    # Define entity filter and management zone selector
    entity_filter = 'type("HOST")'
    mz_selector = f'mzName("{management_zone}")'
 
    # Fetch data for each metric
    data = {}
    host_name_mapping = {}
    for metric_name, metric_selector in metrics.items():
        print(f"Fetching data for {metric_name}...")
        metric_data = fetch_metrics(api_base_url, headers, metric_selector, entity_filter, mz_selector, start_time)
        data[metric_name] = metric_data
 
        # Resolve HOST Name
        for result in metric_data.get("result", []):
            for data_point in result.get("data", []):
                host_id = data_point.get("dimensions", ["Unknown"])[0]  # This extracts the first dimension (host ID)
                if host_id not in host_name_mapping:
                    # Fetch and cache the display name
                    host_name_mapping[host_id] = fetch_host_name(api_base_url, headers, host_id)
                # Replace the Host ID with the resolved display name
                data_point["dimensions"][0] = host_name_mapping.get(host_id, host_id)
 
    # Generate the Excel report
    output_filename = "Dynatrace_Report.xlsx"
    print("Generating report...")
    generate_report(data, output_filename)
    print(f"Report saved to {output_filename}")
 
if __name__ == "__main__":
    main()
