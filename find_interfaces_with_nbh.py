#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import argparse
import getpass
import requests
import urllib3

# Suppress only the single InsecureRequestWarning from urllib3 needed.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def configure_logging(logfile='script.log'):
    """
    Zet logging op naar bestand en console.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # File handler
    fh = logging.FileHandler(logfile)
    fh.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger

def create_session(token=None):
    """
    Maak een requests.Session aan met JSON headers en (optioneel) Bearer token.
    """
    sess = requests.Session()
    sess.verify = False  # Bij voorkeur: geef hier True en configureer certs
    headers = {
        'Accept':       'application/json',
        'Content-Type': 'application/json',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    sess.headers.update(headers)
    return sess

def get_bearer_token(fqdn, username, password, sess):
    """
    Haal een JWT token op van de Conductor via /api/v1/login.
    """
    url = f"https://{fqdn}/api/v1/login"
    payload = {'username': username, 'password': password}
    resp = sess.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    token = data.get('token')
    if not token:
        raise RuntimeError("Geen token ontvangen van login endpoint")
    return token

def api_get(fqdn, path, sess):
    """
    Doe een GET-request naar https://{fqdn}{path} en return JSON-body.
    """
    url = f"https://{fqdn}{path}"
    resp = sess.get(url)
    resp.raise_for_status()
    return resp.json()

def find_device_interfaces_with_neighborhood(fqdn, sess, neighborhood):
    """
    Navigeer door routers → nodes → device-interfaces → network-interfaces → neighborhoods
    en verzamel alleen die interfaces waar de gegeven neighborhood aanwezig is.
    Return een lijst van dicts met velden:
      router, node, device_interface, network_interface
    """
    results = []
    routers = api_get(fqdn, "/api/v1/config/candidate/authority/router", sess)
    for r in routers:
        rname = r.get('name')
        nodes = api_get(fqdn, f"/api/v1/config/candidate/authority/router/{rname}/node", sess)
        for n in nodes:
            nname = n.get('name')
            devs = api_get(
                fqdn,
                f"/api/v1/config/candidate/authority/router/{rname}/node/{nname}/device-interface",
                sess
            )
            for d in devs:
                dname = d.get('name')
                nets = api_get(
                    fqdn,
                    f"/api/v1/config/candidate/authority/router/{rname}/node/{nname}"
                    f"/device-interface/{dname}/network-interface",
                    sess
                )
                for net in nets:
                    netname = net.get('name')
                    # haal neighborhoods van deze network-interface
                    nbhs = api_get(
                        fqdn,
                        f"/api/v1/config/candidate/authority/router/{rname}/node/{nname}"
                        f"/device-interface/{dname}/network-interface/{netname}/neighborhood",
                        sess
                    )
                    for nb in nbhs:
                        if nb.get('name') == neighborhood:
                            results.append({
                                'router':            rname,
                                'node':              nname,
                                'device_interface':  dname,
                                'network_interface': netname
                            })
                            # stop na eerste match op deze network-interface
                            break
    return results

def write_output(records, output_path=None):
    """
    Print resultaten naar stdout of schrijf naar CSV/JSON bestand.
    """
    if not records:
        print("Geen device-interfaces gevonden.")
        return

    if not output_path:
        for rec in records:
            print(f"{rec['router']}/{rec['node']}/"
                  f"{rec['device_interface']}/{rec['network_interface']}")
    else:
        ext = output_path.rsplit('.', 1)[-1].lower()
        if ext == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2)
        else:
            import csv
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)
        print(f"Resultaat geschreven naar {output_path}")

def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Lijst device-interfaces met een opgegeven neighborhood")
    parser.add_argument('--fqdn',         required=True,
                        help="Conductor FQDN of IP-adres")
    parser.add_argument('--username',     required=True,
                        help="Gebruikersnaam voor login")
    parser.add_argument('--neighborhood', required=True,
                        help="Naam van de neighborhood om op te filteren")
    parser.add_argument('--output',       required=False,
                        help="Pad voor output (bijv. results.csv of .json)")
    return parser.parse_args()

def main():
    args = parse_args()
    logger = configure_logging()
    password = getpass.getpass("Password: ")

    logger.info("Authenticatie bij %s als %s", args.fqdn, args.username)
    sess_noauth = create_session()
    try:
        token = get_bearer_token(args.fqdn, args.username, password, sess_noauth)
    except Exception as e:
        logger.error("Login mislukte: %s", e)
        return

    sess = create_session(token)
    logger.info("Zoek device-interfaces met neighborhood '%s'", args.neighborhood)
    try:
        records = find_device_interfaces_with_neighborhood(
            args.fqdn, sess, args.neighborhood
        )
    except Exception as e:
        logger.error("Fout tijdens ophalen data: %s", e)
        return

    logger.info("Gevonden %d interfaces", len(records))
    write_output(records, args.output)

if __name__ == '__main__':
    main()
