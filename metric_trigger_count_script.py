
from datetime import datetime
import requests
import csv
import logging

# Setup logging with incremented file naming
def setup_logger():
    log_number = 1
    while True:
        log_filename = f"MetricAuditCSV_{log_number}.log"
        try:
            with open(log_filename, 'x'):
                break
        except FileExistsError:
            log_number += 1
    logging.basicConfig(filename=log_filename, level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    return log_filename

# Get user inputs
def get_user_inputs():
    api_url = input("Enter Dynatrace API base URL (e.g., https://your-domain.com/api/v2): ").strip()
    api_token = input("Enter your Dynatrace API token: ").strip()
    timeframe = input("Enter timeframe (e.g., now-1h, now-1d): ").strip()
    return api_url, api_token, timeframe

# Fetch metric usage
def fetch_metric_usage(api_url, api_token, timeframe):
    metric_usage = {}
    endpoint = f"{api_url}/metrics"
    headers = {
        "Authorization": f"Api-Token {api_token}"
    }

    params = {
        "pageSize": 1000
    }

    try:
        while endpoint:
            response = requests.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            for metric in data.get('metrics', []):
                selector = metric.get('metricId')
                usage_endpoint = f"{api_url}/metrics/{selector}/data?from={timeframe}&to=now"
                usage_response = requests.get(usage_endpoint, headers=headers)
                if usage_response.status_code == 200:
                    points = usage_response.json().get('data', [])
                    metric_usage[selector] = len(points)
                else:
                    logging.warning(f"Failed to get data for {selector}: {usage_response.status_code}")
            endpoint = data.get('nextPageKey')
            if endpoint:
                endpoint = f"{api_url}/metrics?nextPageKey={endpoint}"
    except Exception as e:
        logging.error(f"Error fetching metric usage: {e}")
        print(f"Error occurred: {e}")
    return metric_usage

# Save to CSV
def save_to_csv(metric_usage):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file_name = f"MetricUsage_{timestamp}.csv"
    with open(csv_file_name, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Metric Selector", "Usage Count"])
        for metric, count in metric_usage.items():
            writer.writerow([metric, count])
    print(f"Results written to {csv_file_name}")

# Main flow
def main():
    setup_logger()
    api_url, api_token, timeframe = get_user_inputs()
    usage_data = fetch_metric_usage(api_url, api_token, timeframe)
    save_to_csv(usage_data)

if __name__ == "__main__":
    main()
