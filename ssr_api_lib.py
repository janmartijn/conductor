import requests
import logging

# Configureer logging
logging.basicConfig(filename='script-log.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

def disable_warnings():
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
