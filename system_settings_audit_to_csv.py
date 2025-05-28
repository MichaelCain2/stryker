
import csv
import requests
import logging
from datetime import datetime

# Setup logging
log_filename = f"SystemChangesAudit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Prompt for inputs
api_url = input("Enter your Dynatrace API base URL (e.g., https://your-domain/api/v2/auditlogs): ").strip()
api_token = input("Enter your Dynatrace API token: ").strip()
start_date = input("Enter the start date (YYYY-MM-DD): ").strip()

# Prepare headers and parameters
headers = {
    "Authorization": f"Api-Token {api_token}"
}
params = {
    "from": f"{start_date}T00:00:00Z",
    "pageSize": 500
}

# Perform request
try:
    logging.info("Querying Dynatrace API for system-level settings changes")
    response = requests.get(api_url, headers=headers, params=params)
    response.raise_for_status()
    audit_data = response.json()
    events = audit_data.get("auditLogs", [])

    # Write to CSV
    csv_filename = f"System_Changes_Audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "User", "Action", "Entity", "Description"])
        for event in events:
            writer.writerow([
                event.get("timestamp"),
                event.get("user"),
                event.get("action"),
                event.get("entityName"),
                event.get("description")
            ])

    print(f"Audit log saved to: {csv_filename}")
    logging.info(f"Audit log successfully written to {csv_filename}")

except requests.exceptions.RequestException as e:
    logging.error(f"Request failed: {e}")
    print(f"Request failed: {e}")
except Exception as e:
    logging.error(f"Unexpected error: {e}")
    print(f"Unexpected error: {e}")
