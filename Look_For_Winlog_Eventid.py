import json
import csv
from collections import Counter
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename

def extract_event_ids(data):
    """
    Extracts numerical values from 'winlog.event id': ['<value>'] in the JSON data.
    """
    event_ids = []

    def search(obj):
        if isinstance(obj, dict):
            # Look for the key 'winlog.event id'
            if 'winlog.event id' in obj:
                value = obj['winlog.event id']
                # Ensure it's a list and extract the first numerical value
                if isinstance(value, list) and value:
                    event_ids.extend(int(item) for item in value if item.isdigit())
            # Recursively check nested dictionaries
            for key, value in obj.items():
                search(value)
        elif isinstance(obj, list):
            for item in obj:
                search(item)

    search(data)
    return event_ids

def main():
    # Open file dialog to select the input JSON file
    Tk().withdraw()  # Suppress root Tkinter window
    input_file = askopenfilename(
        title="Select JSON File to Parse",
        filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
    )

    if not input_file:
        print("No file selected. Exiting...")
        return

    # Open file dialog to select the output CSV file
    output_file = asksaveasfilename(
        title="Save CSV Output As",
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
    )

    if not output_file:
        print("No output file selected. Exiting...")
        return

    try:
        # Load JSON data from the selected file
        with open(input_file, 'r') as file:
            data = json.load(file)

        # Extract and count occurrences of 'winlog.event id'
        event_ids = extract_event_ids(data)
        event_id_counts = Counter(event_ids)

        # Write counts to the selected CSV file
        with open(output_file, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['Event ID', 'Count'])
            for event_id, count in event_id_counts.items():
                writer.writerow([event_id, count])

        print(f"CSV output successfully saved to: {output_file}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
