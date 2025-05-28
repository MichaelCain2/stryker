
import requests
import csv
import logging
import os
from datetime import datetime

# Prompt for user inputs
base_url = input("Enter the Dynatrace base API URL (e.g., https://yourenv.live.dynatrace.com/api/v2/auditlogs): ").strip()
api_token = input("Enter your API token: ").strip()
from_time = input("Enter the 'from' time (e.g., now-1h, now-1d, etc.): ").strip()

# Construct full API URL with query parameters
full_url = f"{base_url}?from={from_time}&sort=-timestamp"

# Generate incrementing log filename
log_index = 1
while os.path.exists(f"CSV_{log_index}.log"):
    log_index += 1
log_filename = f"CSV_{log_index}.log"

# Set up logging
logging.basicConfig(
    filename=log_filename,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info("Script started")

# Set up headers
headers = {
    "Authorization": f"Api-Token {api_token}"
}

# Perform request
try:
    response = requests.get(full_url, headers=headers)
    response.raise_for_status()
    data = response.json()
    logging.info("API request successful.")
except requests.exceptions.RequestException as e:
    logging.error(f"API request failed: {e}")
    print(f"API request failed: {e}")
    exit(1)

# Prepare CSV output
csv_filename = f"auditlog_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
try:
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "EventType", "User", "EntityId", "Description"])

        for entry in data.get("auditLogs", []):
            writer.writerow([
                entry.get("timestamp"),
                entry.get("eventType"),
                entry.get("user"),
                entry.get("entityId", "N/A"),
                entry.get("description", "N/A")
            ])
    logging.info(f"CSV file created: {csv_filename}")
    print(f"CSV export completed: {csv_filename}")
except Exception as e:
    logging.error(f"Failed to write CSV file: {e}")
    print(f"Failed to write CSV file: {e}")
