
import csv
import logging
import requests
from datetime import datetime

# Configure logging with timestamp in filename
log_filename = f"AuditLog_to_CSV_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Prompt user for API details
api_url = input("Enter your Dynatrace API base URL (e.g., https://your-domain/api/v2/auditlogs): ").strip()
api_token = input("Enter your Dynatrace API token: ").strip()
relative_time = input("Enter the relative start time (e.g., now-1m, now-1h, now-1d): ").strip()

headers = {
    "Authorization": f"Api-Token {{api_token}}",
    "Accept": "application/json"
}

params = {
    "from": relative_time,
    "sort": "-timestamp",
    "pageSize": 500
}

results = []
more_data = True
page_count = 1

while more_data:
    logging.info(f"Fetching page {{page_count}} from API...")
    response = requests.get(api_url, headers=headers, params=params)
    if response.status_code != 200:
        logging.error(f"Failed to fetch data: {{response.status_code}} - {{response.text}}")
        print(f"Error: {{response.status_code}}. Check the log file for details.")
        break

    data = response.json()
    entries = data.get("auditLogs", [])
    results.extend(entries)
    logging.info(f"Retrieved {{len(entries)}} entries on page {{page_count}}")

    # Pagination: update the cursor for the next page if available
    if "nextPageKey" in data:
        params["nextPageKey"] = data["nextPageKey"]
        page_count += 1
    else:
        more_data = False

# Output to CSV
if results:
    csv_filename = f"auditlogs_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}.csv"
    with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        # Write header
        headers_written = False
        for entry in results:
            if not headers_written:
                writer.writerow(entry.keys())
                headers_written = True
            writer.writerow(entry.values())

    print(f"CSV file created: {{csv_filename}}")
    logging.info(f"CSV file successfully created: {{csv_filename}}")
else:
    print("No audit log data was returned.")
    logging.info("No audit log data was returned.")
