import requests
import json

def main():
    # Prompt for required parameters
    api_url = input("Enter API URL: ").strip()
    api_token = input("Enter API Token: ").strip()
    management_zone = input("Enter Management Zone: ").strip()
    agg_time = input("Enter Aggregation Time: ").strip()
    resolution = input("Enter Resolution: ").strip()

    headers = {"Authorization": f"Api-Token {api_token}"}
    
    # Query the Metrics API using the disk metric (splitBy for dt.entity.disk)
    metric = 'builtin:host.disk.usedPct:splitBy("dt.entity.disk")'
    metrics_url = f"{api_url}?metricSelector={metric}&from={agg_time}&entitySelector=type(\"HOST\")&mzSelector=mzName(\"{management_zone}\")&resolution={resolution}"
    
    print("Querying Metrics API...")
    response = requests.get(metrics_url, headers=headers)
    print("Metrics API status code:", response.status_code)
    
    if response.status_code != 200:
        print("Error connecting to Metrics API.")
        return

    data = response.json()
    print("Metrics API returned keys:", list(data.keys()))
    
    # Check if the disk metric returned any results
    if "result" not in data or len(data["result"]) == 0:
        print("No results returned from Metrics API for the disk metric.")
        return

    # Try to extract a disk entity ID from the first result's dimensions
    first_result = data["result"][0]
    dimensions = first_result.get("dimensions", [])
    if not dimensions:
        print("No dimensions found in the first metric result.")
        return
    disk_id = dimensions[0]
    print("Found disk entity ID:", disk_id)

    # Now query the Entities API for the disk entity
    # Determine the base URL by removing the "metrics/query" part from the API URL.
    base_url = api_url.split("metrics/query")[0]
    entities_url = f"{base_url}/entities/{disk_id}"
    
    print("Querying Entities API for disk entity...")
    entity_response = requests.get(entities_url, headers=headers)
    print("Entities API status code:", entity_response.status_code)
    
    if entity_response.status_code != 200:
        print("Error connecting to Entities API for disk entity.")
        return

    entity_data = entity_response.json()
    print("Entities API returned keys:", list(entity_data.keys()))
    
    # Check for the relationship (typically under "fromRelationships" with key "isDiskOf")
    from_relationships = entity_data.get("fromRelationships", {})
    if "isDiskOf" in from_relationships:
        print("Disk is associated with host(s):", from_relationships["isDiskOf"])
    else:
        print("No 'isDiskOf' relationship found for disk entity.")

if __name__ == "__main__":
    main()
