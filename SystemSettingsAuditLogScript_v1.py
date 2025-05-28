import requests
import logging
from datetime import datetime

# Configure logging
log_filename = "SystemSettingsAuditLog_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def fetch_audit_log(base_url, token, from_date):
    headers = {
        "Authorization": f"Api-Token {token}"
    }
    params = {
        "from": from_date,
        "pageSize": 500
    }
    url = f"{base_url}/api/v2/auditlogs"
    logging.debug(f"Querying URL: {url} with params: {params}")
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    base_url = input("Enter Dynatrace API base URL (e.g., https://yourdomain.com): ").strip()
    token = input("Enter API token: ").strip()
    from_date = input("Enter start date (ISO 8601 format, e.g., 2024-01-01T00:00:00Z): ").strip()

    try:
        data = fetch_audit_log(base_url, token, from_date)
        for entry in data.get("auditLogs", []):
            logging.info(f"Timestamp: {entry.get('timestamp')} | User: {entry.get('user')} | Action: {entry.get('action')} | Entity: {entry.get('entityName')}")
            print(f"Timestamp: {entry.get('timestamp')} | User: {entry.get('user')} | Action: {entry.get('action')} | Entity: {entry.get('entityName')}")
    except Exception as e:
        logging.error(f"Failed to fetch audit logs: {str(e)}")
        print("An error occurred. Check the log file for details.")
