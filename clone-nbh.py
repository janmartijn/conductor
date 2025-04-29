import requests
import logging
import json
import time
import getpass

# Configureer logging
logging.basicConfig(filename='script-log.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

def get_bearer_token(fqdn_or_ip, username, password):
    url = f"https://{fqdn_or_ip}/api/v1/login"
    payload = {"username": username, "password": password}
    try:
        response = requests.post(url, json=payload, verify=False)
        response.raise_for_status()
        logging.info("Login successful: SECRET")
        return response.json().get('token')
    except Exception as e:
        logging.error(f"Login failed: {e}")
        raise

def get_nodes(fqdn_or_ip, hub, bearer):
    url = f"https://{fqdn_or_ip}/api/v1/config/candidate/authority/router/{hub}/node"
    headers = {"Authorization": f"Bearer {bearer}"}
    response = requests.get(url, headers=headers, verify=False)
    logging.info(f"Nodes fetched: {response.text}")
    return response.json()

def get_device_interfaces(fqdn_or_ip, hub, node, bearer):
    url = f"https://{fqdn_or_ip}/api/v1/config/candidate/authority/router/{hub}/node/{node}/device-interface"
    headers = {"Authorization": f"Bearer {bearer}"}
    response = requests.get(url, headers=headers, verify=False)
    logging.info(f"Device Interfaces for node {node}: {response.text}")
    return response.json()

def get_network_interfaces(fqdn_or_ip, hub, node, device_interface, bearer):
    url = f"https://{fqdn_or_ip}/api/v1/config/candidate/authority/router/{hub}/node/{node}/device-interface/{device_interface}/network-interface"
    headers = {"Authorization": f"Bearer {bearer}"}
    response = requests.get(url, headers=headers, verify=False)
    logging.info(f"Network Interfaces for device-interface {device_interface}: {response.text}")
    return response.json()

def get_neighborhoods(fqdn_or_ip, hub, node, device_interface, network_interface, bearer):
    url = f"https://{fqdn_or_ip}/api/v1/config/candidate/authority/router/{hub}/node/{node}/device-interface/{device_interface}/network-interface/{network_interface}/neighborhood"
    headers = {"Authorization": f"Bearer {bearer}"}
    response = requests.get(url, headers=headers, verify=False)
    logging.info(f"Neighborhoods for network-interface {network_interface}: {response.text}")
    return response.json()

def clone_neighborhood(fqdn_or_ip, hub, node, device_interface, network_interface, neighborhood_existing, neighborhood_new, bearer):
    url = f"https://{fqdn_or_ip}/api/v1/config/candidate/authority/router/{hub}/node/{node}/device-interface/{device_interface}/network-interface/{network_interface}/neighborhood/{neighborhood_existing}/clone"
    headers = {
        "Authorization": f"Bearer {bearer}",
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {"name": neighborhood_new}
    response = requests.post(url, headers=headers, json=payload, verify=False)
    logging.info(f"Clone neighborhood response: {response.text}")
    return response.status_code in [200, 201, 202, 204]

def add_neighborhood(fqdn_or_ip, router, node, device_interface, network_interface, neighborhood_new, bearer):
    url = f"https://{fqdn_or_ip}/api/v1/config/candidate/authority/router/{router}/node/{node}/device-interface/{device_interface}/network-interface/{network_interface}/neighborhood"
    headers = {
        "Authorization": f"Bearer {bearer}",
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {"name": neighborhood_new}
    response = requests.post(url, headers=headers, json=payload, verify=False)
    logging.info(f"Add neighborhood to spoke response: {response.text}")
    return response.status_code in [200, 201, 202, 204]

def main():
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    fqdn_or_ip = input("Enter the FQDN or IP of the conductor: ").strip()
    username = input("Enter your username: ").strip()
    password = getpass.getpass("Enter your password: ").strip()

    bearer = get_bearer_token(fqdn_or_ip, username, password)

    hub = input("Enter the hub router name: ").strip()
    nodes = get_nodes(fqdn_or_ip, hub, bearer)

    node_names = [node['name'] for node in nodes]
    print(f"Nodes found: {node_names}")

    all_neighborhoods = {}

    for node in node_names:
        device_interfaces = get_device_interfaces(fqdn_or_ip, hub, node, bearer)
        for dev_if in device_interfaces:
            dev_if_name = dev_if['name']
            network_interfaces = get_network_interfaces(fqdn_or_ip, hub, node, dev_if_name, bearer)
            for net_if in network_interfaces:
                net_if_name = net_if['name']
                neighborhoods = get_neighborhoods(fqdn_or_ip, hub, node, dev_if_name, net_if_name, bearer)
                for nbh in neighborhoods:
                    nbh_name = nbh['name']
                    full_path = {
                        'node': node,
                        'device_interface': dev_if_name,
                        'network_interface': net_if_name,
                        'neighborhood': nbh_name
                    }
                    all_neighborhoods[nbh_name] = full_path

    print("Available neighborhoods:")
    for idx, nbh_name in enumerate(all_neighborhoods.keys(), start=1):
        print(f"{idx}. {nbh_name}")

    choice_idx = int(input("Select a neighborhood to clone (number): ")) - 1
    chosen_nbh_name = list(all_neighborhoods.keys())[choice_idx]
    new_nbh_name = input("Enter the new neighborhood name: ").strip()

    chosen_nbh = all_neighborhoods[chosen_nbh_name]

    print(f"Neighborhood to clone: {chosen_nbh_name}")
    print(f"New neighborhood name: {new_nbh_name}")

    confirmation = input(f"Are you sure you want to clone '{chosen_nbh_name}' to '{new_nbh_name}'? (yes/no): ").strip().lower()
    if confirmation != 'yes':
        print("Operation cancelled.")
        return

    clone_neighborhood(
        fqdn_or_ip, hub,
        chosen_nbh['node'],
        chosen_nbh['device_interface'],
        chosen_nbh['network_interface'],
        chosen_nbh['neighborhood'],
        new_nbh_name,
        bearer
    )

    print("Waiting 5 seconds for system to synchronize...")
    time.sleep(5)

    neighborhoods = get_neighborhoods(fqdn_or_ip, hub, chosen_nbh['node'], chosen_nbh['device_interface'], chosen_nbh['network_interface'], bearer)
    nbh_names = [nbh['name'] for nbh in neighborhoods]
    if new_nbh_name in nbh_names:
        print(f"Verification successful: New neighborhood '{new_nbh_name}' exists.")
    else:
        print(f"Verification failed: New neighborhood '{new_nbh_name}' not found.")
        return

    proceed_spokes = input("Do you want to add this new neighborhood to spoke routers? (yes/no): ").strip().lower()
    if proceed_spokes != 'yes':
        print("Spoke operation skipped.")
        return

    prefix = input("Enter the spoke router name prefix: ").strip()

    url = f"https://{fqdn_or_ip}/api/v1/config/candidate/authority/router"
    headers = {"Authorization": f"Bearer {bearer}"}
    response = requests.get(url, headers=headers, verify=False)
    routers = response.json()

    spoke_routers = [router for router in routers if router['name'].startswith(prefix)]

    print(f"Spoke routers found ({len(spoke_routers)}):")

    interfaces_to_update = []

    for router in spoke_routers:
        router_name = router['name']
        nodes = get_nodes(fqdn_or_ip, router_name, bearer)
        for node in nodes:
            node_name = node['name']
            device_interfaces = get_device_interfaces(fqdn_or_ip, router_name, node_name, bearer)
            for dev_if in device_interfaces:
                dev_if_name = dev_if['name']
                network_interfaces = get_network_interfaces(fqdn_or_ip, router_name, node_name, dev_if_name, bearer)
                for net_if in network_interfaces:
                    net_if_name = net_if['name']
                    if 'wan' in net_if_name.lower():
                        interfaces_to_update.append((router_name, node_name, dev_if_name, net_if_name))

    for entry in interfaces_to_update:
        print(f"Router: {entry[0]}, Node: {entry[1]}, Device-Interface: {entry[2]}, Network-Interface: {entry[3]}")

    confirm_update = input(f"Proceed to add new neighborhood '{new_nbh_name}' to these interfaces? (yes/no): ").strip().lower()
    if confirm_update != 'yes':
        print("Operation cancelled.")
        return

    for router_name, node_name, dev_if_name, net_if_name in interfaces_to_update:
        add_neighborhood(fqdn_or_ip, router_name, node_name, dev_if_name, net_if_name, new_nbh_name, bearer)

    print("Neighborhood added to selected WAN interfaces on all spoke routers.")

if __name__ == "__main__":
    main()
