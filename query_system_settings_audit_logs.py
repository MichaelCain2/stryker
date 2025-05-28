
import requests
import json
from datetime import datetime
import sys

def prompt_user_input():
    api_url = input("Enter Dynatrace API base URL (e.g., https://your.domain.com/api): ").strip().rstrip("/")
    api_token = input("Enter your API Token (with settings.audit.read permission): ").strip()
    from_date = input("Enter the starting date (e.g., 2025-04-01): ").strip()
    return api_url, api_token, from_date

def build_headers(api_token):
    return {
        "Authorization": f"Api-Token {api_token}",
        "Content-Type": "application/json"
    }

def fetch_audit_logs(api_url, headers, from_date):
    endpoint = f"{api_url}/v2/settings/audit"
    params = {
        "from": f"{from_date}T00:00:00Z",
        "pageSize": 100
    }

    all_changes = []
    while endpoint:
        response = requests.get(endpoint, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Error fetching data: {response.status_code} - {response.text}")
            sys.exit(1)

        data = response.json()
        all_changes.extend(data.get("auditLogs", []))

        next_page_key = data.get("nextPageKey")
        if next_page_key:
            endpoint = f"{api_url}/v2/settings/audit?nextPageKey={next_page_key}"
            params = None  # only need params on first call
        else:
            endpoint = None

    return all_changes

def display_audit_changes(changes):
    if not changes:
        print("No changes found for specified date range.")
        return
    print(f"Found {len(changes)} changes:")
    for entry in changes:
        timestamp = entry.get("timestamp")
        user = entry.get("user")
        action = entry.get("action")
        setting_name = entry.get("objectId", "N/A")
        print(f"[{timestamp}] {user} performed {action} on {setting_name}")

if __name__ == "__main__":
    api_url, api_token, from_date = prompt_user_input()
    headers = build_headers(api_token)
    changes = fetch_audit_logs(api_url, headers, from_date)
    display_audit_changes(changes)
