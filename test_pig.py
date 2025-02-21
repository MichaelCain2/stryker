import requests
import json
import logging
import sys
from datetime import datetime

# Configure logging to file and console
log_filename = f"simple_api_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    filename=log_filename,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

def main():
    # Prompt for input parameters
    api_url = input("Enter API URL: ").strip()
    api_token = input("Enter API Token: ").strip()
    management_zone = input("Enter Management Zone: ").strip()
    agg_time = input("Enter Aggregation Time: ").strip()
    resolution = input("Enter Resolution (leave empty if not applicable): ").strip()

    headers = {"Authorization": f"Api-Token {api_token}"}

    # Build the Metrics API URL using exact quoting (critical to avoid 400 errors)
    # Only append &resolution= if a resolution value is provided.
    metric = 'builtin:host.disk.usedPct:splitBy("dt.entity.disk")'
    resolution_param = f"&resolution={resolution}" if resolution else ""
    metric_url = (f'{api_url}?metricSelector={metric}'
                  f'&from={agg_time}'
                  f'&entitySelector=type("HOST")'
                  f'&mzSelector=mzName("{management_zone}")'
                  f'{resolution_param}')
    
    logging.info("Querying Metrics API...")
    logging.debug(f"Metrics URL: {metric_url}")
    response = requests.get(metric_url, headers=headers)
    logging.info(f"Metrics API status code: {response.status_code}")
    
    if response.status_code != 200:
        logging.error("Error connecting to Metrics API. Response: " + response.text)
        print("Error connecting to Metrics API")
        return

    data = response.json()
    logging.debug("Metrics API returned keys: " + str(list(data.keys())))
    
    results = data.get("result", [])
    if not results:
        logging.error("No results returned from Metrics API.")
        return

    # Extract the first disk entity ID from the first result's dimensions
    first_result = results[0]
    dims = first_result.get("dimensions", [])
    if not dims:
        logging.error("No dimensions found in first result.")
        return

    disk_id = dims[0]
    logging.info(f"Extracted disk entity ID: {disk_id}")

    # Construct the Entities API URL for the disk
    base_url = api_url.split("metrics/query")[0]
    entity_url = f"{base_url}/entities/{disk_id}"
    
    logging.info("Querying Entities API for disk entity...")
    logging.debug(f"Entities URL: {entity_url}")
    ent_response = requests.get(entity_url, headers=headers)
    logging.info(f"Entities API status code: {ent_response.status_code}")
    
    if ent_response.status_code != 200:
        logging.error("Error connecting to Entities API for disk entity. Response: " + ent_response.text)
        print("Error connecting to Entities API for disk entity.")
        return

    ent_data = ent_response.json()
    logging.debug("Entities API returned keys: " + str(list(ent_data.keys())))
    
    # Check for the disk-to-host relationship (commonly under "fromRelationships" with key "isDiskOf")
    from_rels = ent_data.get("fromRelationships", {})
    if "isDiskOf" in from_rels:
        logging.info(f"Disk is associated with host(s): {from_rels['isDiskOf']}")
    else:
        logging.info("No 'isDiskOf' relationship found for this disk.")

if __name__ == "__main__":
    main()
