import requests
import logging
import json
import time
import getpass

# Configureer logging
task_logger = logging.getLogger()
log_handler = logging.FileHandler('script-log.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
log_handler.setFormatter(formatter)
task_logger.setLevel(logging.INFO)
task_logger.addHandler(log_handler)

# Globale request session voor performance
def create_session(token=None):
    session = requests.Session()
    session.verify = False  # Bij voorkeur: CA-certificaat configureren
    if token:
        session.headers.update({'Authorization': f'Bearer {token}'})
    session.headers.update({'Accept': 'application/json', 'Content-Type': 'application/json'})
    return session

# API-wrappers
def get_bearer_token(fqdn, username, password, session_noauth):
    url = f"https://{fqdn}/api/v1/login"
    payload = {"username": username, "password": password}
    resp = session_noauth.post(url, json=payload)
    resp.raise_for_status()
    token = resp.json().get('token')
    task_logger.info("Login successful for %s", username)
    return token


def api_get(path, session):
    url = f"https://{fqdn_or_ip}{path}"
    resp = session.get(url)
    resp.raise_for_status()
    task_logger.info("GET %s returned %s", path, resp.status_code)
    return resp.json()


def api_post(path, session, payload=None):
    url = f"https://{fqdn_or_ip}{path}"
    resp = session.post(url, json=payload or {})
    resp.raise_for_status()
    task_logger.info("POST %s payload=%s returned %s", path, payload, resp.status_code)
    return resp

# Use-case 1: Clone neighborhood op hub
def clone_on_hub(session):
    hub = input("Enter the hub router name: ").strip()
    nodes = api_get(f"/api/v1/config/candidate/authority/router/{hub}/node", session)
    all_nbh = {}
    for node in nodes:
        node_name = node['name']
        devs = api_get(f"/api/v1/config/candidate/authority/router/{hub}/node/{node_name}/device-interface", session)
        for dev in devs:
            dev_name = dev['name']
            nets = api_get(
                f"/api/v1/config/candidate/authority/router/{hub}/node/{node_name}/device-interface/{dev_name}/network-interface",
                session
            )
            for net in nets:
                net_name = net['name']
                nbhs = api_get(
                    f"/api/v1/config/candidate/authority/router/{hub}/node/{node_name}/device-interface/{dev_name}/network-interface/{net_name}/neighborhood",
                    session
                )
                for nbh in nbhs:
                    all_nbh[nbh['name']] = (node_name, dev_name, net_name)
    print("Available neighborhoods to clone:")
    for i, name in enumerate(all_nbh, 1):
        print(f"{i}. {name}")
    choice = int(input("Select number: ")) - 1
    src_nbh = list(all_nbh)[choice]
    dest_nbh = input("Enter the new neighborhood name: ").strip()
    node_name, dev_name, net_name = all_nbh[src_nbh]
    if input(f"Clone '{src_nbh}' to '{dest_nbh}'? (yes/no): ").strip().lower() != 'yes':
        print("Aborted.")
        return
    api_post(
        f"/api/v1/config/candidate/authority/router/{hub}/node/{node_name}/device-interface/{dev_name}/network-interface/{net_name}/neighborhood/{src_nbh}/clone",
        session,
        {"name": dest_nbh}
    )
    print("Cloning... wacht 5s")
    time.sleep(5)
    print("Clone ready.")

# Use-case 2: Generate router-list voor referentie-neighborhood
def generate_router_list(session):
    routers = api_get("/api/v1/config/candidate/authority/router", session)
    router_nbh_map = {}
    all_nbh = set()
    for r in routers:
        rname = r['name']
        nbh_set = set()
        nodes = api_get(f"/api/v1/config/candidate/authority/router/{rname}/node", session)
        for node in nodes:
            node_name = node['name']
            devs = api_get(
                f"/api/v1/config/candidate/authority/router/{rname}/node/{node_name}/device-interface",
                session
            )
            for dev in devs:
                dev_name = dev['name']
                nets = api_get(
                    f"/api/v1/config/candidate/authority/router/{rname}/node/{node_name}/device-interface/{dev_name}/network-interface",
                    session
                )
                for net in nets:
                    nbhs = api_get(
                        f"/api/v1/config/candidate/authority/router/{rname}/node/{node_name}/device-interface/{dev_name}/network-interface/{net['name']}/neighborhood",
                        session
                    )
                    for nbh in nbhs:
                        nbh_set.add(nbh['name'])
                        all_nbh.add(nbh['name'])
        if nbh_set:
            router_nbh_map[rname] = nbh_set
    sorted_nbh = sorted(all_nbh)
    print("Beschikbare reference neighborhoods:")
    for i, name in enumerate(sorted_nbh, 1):
        print(f"{i}. {name}")
    ref_choice = int(input("Selecteer referentie-neighborhood (nummer): ")) - 1
    ref_nbh = sorted_nbh[ref_choice]
    target_routers = [r for r, nbhs in router_nbh_map.items() if ref_nbh in nbhs]
    print(f"Routers met neighborhood '{ref_nbh}': {len(target_routers)}")
    for r in target_routers:
        print(f"- {r}")
    filename = input("Enter filename to save router list [router_list.txt]: ").strip() or 'router_list.txt'
    with open(filename, 'w') as f:
        for r in target_routers:
            f.write(r + '\n')
    print(f"Router list saved to {filename}. Je kunt dit bestand nu bewerken.")

# Use-case 3: Add neighborhood to spokes via bewerkte router-list met error handling
def add_via_router_list(session):
    filename = input("Enter router list filename [router_list.txt]: ").strip() or 'router_list.txt'
    try:
        with open(filename) as f:
            routers = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Fout bij lezen van {filename}: {e}")
        return
    if not routers:
        print("Geen routers gevonden in lijst.")
        return
    print(f"Loaded {len(routers)} routers from {filename}.")
    all_nbh = set()
    for rname in routers:
        nodes = api_get(f"/api/v1/config/candidate/authority/router/{rname}/node", session)
        for node in nodes:
            node_name = node['name']
            devs = api_get(
                f"/api/v1/config/candidate/authority/router/{rname}/node/{node_name}/device-interface",
                session
            )
            for dev in devs:
                dev_name = dev['name']
                nets = api_get(
                    f"/api/v1/config/candidate/authority/router/{rname}/node/{node_name}/device-interface/{dev_name}/network-interface",
                    session
                )
                for net in nets:
                    nbhs = api_get(
                        f"/api/v1/config/candidate/authority/router/{rname}/node/{node_name}/device-interface/{dev_name}/network-interface/{net['name']}/neighborhood",
                        session
                    )
                    for nbh in nbhs:
                        all_nbh.add(nbh['name'])
    sorted_nbh = sorted(all_nbh)
    print("Beschikbare neighborhoods om toe te voegen:")
    for i, name in enumerate(sorted_nbh, 1):
        print(f"{i}. {name}")
    choice = int(input("Selecteer neighborhood om toe te voegen (nummer): ")) - 1
    new_nbh = sorted_nbh[choice]
    if input(f"Add '{new_nbh}' to these routers on their WAN interfaces? (yes/no): ").strip().lower() != 'yes':
        print("Aborted.")
        return
    # Iterate en handle errors
    for rname in routers:
        nodes = api_get(f"/api/v1/config/candidate/authority/router/{rname}/node", session)
        for node in nodes:
            node_name = node['name']
            devs = api_get(
                f"/api/v1/config/candidate/authority/router/{rname}/node/{node_name}/device-interface",
                session
            )
            for dev in devs:
                dev_name = dev['name']
                nets = api_get(
                    f"/api/v1/config/candidate/authority/router/{rname}/node/{node_name}/device-interface/{dev_name}/network-interface",
                    session
                )
                for net in nets:
                    if 'wan' in net['name'].lower():
                        path = (
                            f"/api/v1/config/candidate/authority/router/{rname}"
                            f"/node/{node_name}/device-interface/{dev_name}"
                            f"/network-interface/{net['name']}/neighborhood"
                        )
                        try:
                            existing = [n['name'] for n in api_get(path, session)]
                            if new_nbh in existing:
                                print(f"{new_nbh} already exists on {rname}/{node_name}/{dev_name}/{net['name']}, skipping.")
                                continue
                            api_post(path, session, {"name": new_nbh})
                            print(f"Added {new_nbh} to {rname}/{node_name}/{dev_name}/{net['name']}")
                        except requests.exceptions.HTTPError as e:
                            print(f"Error adding to {rname}/{node_name}/{dev_name}/{net['name']}: {e}")
    print("Done.")

if __name__ == '__main__':
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    fqdn_or_ip = input("Conductor FQDN/IP: ").strip()
    user = input("Username: ").strip()
    pwd = getpass.getpass("Password: ").strip()
    sess_noauth = create_session()
    token = get_bearer_token(fqdn_or_ip, user, pwd, sess_noauth)
    sess = create_session(token)

    while True:
        print("\nMenu:")
        print("1) Clone neighborhood op hub")
        print("2) Generate router-list voor reference neighborhood")
        print("3) Add neighborhood to spokes via router-list")
        print("4) Exit")
        opt = input("Kies optie: ").strip()
        if opt == '1':
            clone_on_hub(sess)
        elif opt == '2':
            generate_router_list(sess)
        elif opt == '3':
            add_via_router_list(sess)
        elif opt == '4':
            print("Tot ziens!")
            break
        else:
            print("Ongeldige keuze, probeer opnieuw.")
