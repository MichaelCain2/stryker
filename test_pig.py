import requests
import json

def main():
    # Prompt for input parameters
    api_url = input("Enter API URL: ").strip()
    api_token = input("Enter API Token: ").strip()
    management_zone = input("Enter Management Zone: ").strip()
    agg_time = input("Enter Aggregation Time: ").strip()
    resolution = input("Enter Resolution: ").strip()
    
    headers = {"Authorization": f"Api-Token {api_token}"}

    # Construct the Metrics API URL.
    # Note: We use exact quoting so that entitySelector=type("HOST") and mzSelector=mzName("{management_zone}")
    metric = 'builtin:host.disk.usedPct:splitBy("dt.entity.disk")'
    metric_url = f'{api_url}?metricSelector={metric}&from={agg_time}&entitySelector=type("HOST")&mzSelector=mzName("{management_zone}")&resolution={resolution}'
    
    print("Querying Metrics API...")
    resp = requests.get(metric_url, headers=headers)
    print("Metrics API status code:", resp.status_code)
    
    if resp.status_code != 200:
        print("Error connecting to Metrics API")
        return

    data = resp.json()
    print("Metrics API returned keys:", list(data.keys()))
    
    results = data.get("result", [])
    if not results:
        print("No results returned from Metrics API.")
        return

    # Extract a disk entity ID from the first result's dimensions.
    first_result = results[0]
    dims = first_result.get("dimensions", [])
    if not dims:
        print("No dimensions found in first result.")
        return

    disk_id = dims[0]
    print("Extracted disk entity ID:", disk_id)

    # Construct the Entities API URL for the disk.
    base_url = api_url.split("metrics/query")[0]
    entity_url = f"{base_url}/entities/{disk_id}"
    
    print("Querying Entities API for disk entity...")
    ent_resp = requests.get(entity_url, headers=headers)
    print("Entities API status code:", ent_resp.status_code)
    
    if ent_resp.status_code != 200:
        print("Error connecting to Entities API for disk entity.")
        return

    ent_data = ent_resp.json()
    print("Entities API returned keys:", list(ent_data.keys()))
    
    # Check for the disk-to-host relationship (typically under "fromRelationships" with key "isDiskOf")
    from_rels = ent_data.get("fromRelationships", {})
    if "isDiskOf" in from_rels:
        print("Disk is associated with host(s):", from_rels["isDiskOf"])
    else:
        print("No 'isDiskOf' relationship found for this disk.")

if __name__ == "__main__":
    main()
