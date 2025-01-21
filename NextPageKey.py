import requests
import json
from tkinter import Tk, filedialog

# Function to fetch data with pagination
def fetch_data_with_pagination(api_url, headers):
    all_data = []
    next_page_key = None

    while True:
        url = api_url if not next_page_key else f"{api_url}&nextPageKey={next_page_key}"
        print(f"Fetching data from: {url}")  # Debugging URL

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if 'items' in data:
            all_data.extend(data['items'])

        next_page_key = data.get('nextPageKey')
        if not next_page_key:
            break

    return all_data

def main():
    # Suppress root Tkinter window
    Tk().withdraw()

    # Prompt user for API URL and Token
    api_url = input("Enter the Dynatrace API URL (e.g., https://<tenant>/api/v2/logs/export): ").strip()
    api_token = input("Enter your API Token: ").strip()

    # Select save location
    print("Please select a location to save the JSON file.")
    save_path = filedialog.asksaveasfilename(
        title="Save JSON Output As",
        defaultextension=".json",
        filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
    )

    if not save_path:
        print("No file selected. Exiting...")
        return

    # Set headers
    headers = {
        "Authorization": f"Api-Token {api_token}",
        "Accept": "application/json; charset=utf-8"
    }

    try:
        # Fetch data using pagination
        all_data = fetch_data_with_pagination(api_url, headers)

        # Save the data to a JSON file
        with open(save_path, 'w') as file:
            json.dump(all_data, file, indent=4)

        print(f"Data successfully saved to: {save_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
