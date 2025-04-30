#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import json
import logging
import argparse
import getpass
import requests
import urllib3

# ——————————————————————————————————————————————————————————
# Suppress InsecureRequestWarning (if self-signed certs used)
# ——————————————————————————————————————————————————————————
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ——————————————————————————————————————————————————————————
# Logging configuration
# ——————————————————————————————————————————————————————————
def configure_logging(logfile='script.log'):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    fh = logging.FileHandler(logfile)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger

# ——————————————————————————————————————————————————————————
# REST-API wrappers
# ——————————————————————————————————————————————————————————

def create_session(token=None):
    sess = requests.Session()
    sess.verify = False
    headers = {
        'Accept':       'application/json',
        'Content-Type': 'application/json',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    sess.headers.update(headers)
    return sess


def get_bearer_token(fqdn, username, password, sess):
    url = f"https://{fqdn}/api/v1/login"
    payload = {'username': username, 'password': password}
    resp = sess.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    token = data.get('token')
    if not token:
        raise RuntimeError("Geen token ontvangen van login endpoint")
    return token


def api_post(fqdn, path, sess, payload):
    url = f"https://{fqdn}{path}"
    resp = sess.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()

# ——————————————————————————————————————————————————————————
# Business logic: CSV input and apply new neighborhood
# ——————————————————————————————————————————————————————————

def set_neighborhood_from_csv(fqdn, sess, csv_path, new_neighborhood):
    """
    Reads CSV and adds the given neighborhood to each network-interface.
    CSV columns: router,node,device_interface,network_interface
    """
    results = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            r = row['router']
            n = row['node']
            d = row['device_interface']
            net = row['network_interface']

            path = (
                f"/api/v1/config/candidate/authority/router/{r}"
                f"/node/{n}"
                f"/device-interface/{d}"
                f"/network-interface/{net}/neighborhood"
            )
            payload = {'name': new_neighborhood}

            try:
                api_post(fqdn, path, sess, payload)
                logging.info(
                    "Added neighborhood '%s' to %s/%s/%s/%s",
                    new_neighborhood, r, n, d, net
                )
                results.append((r, n, d, net, True, "OK"))
            except Exception as e:
                logging.error(
                    "Failed to add neighborhood to %s/%s/%s/%s: %s",
                    r, n, d, net, e
                )
                results.append((r, n, d, net, False, str(e)))
    return results

# ——————————————————————————————————————————————————————————
# CLI argument parsing
# ——————————————————————————————————————————————————————————

def parse_args():
    parser = argparse.ArgumentParser(
        description="Lees CSV en zet een nieuwe neighborhood op network-interfaces"
    )
    parser.add_argument('--fqdn',         required=True,
                        help="Conductor FQDN of IP-adres")
    parser.add_argument('--username',     required=True,
                        help="Gebruikersnaam voor login")
    parser.add_argument('--input-csv',    required=True,
                        help="Pad naar input CSV (kolommen: router,node,device_interface,network_interface)")
    parser.add_argument('--new-neighborhood', required=True,
                        help="Naam van de nieuwe neighborhood om te zetten")
    parser.add_argument('--output-log',   default='script.log',
                        help="Pad naar logfile (default: script.log)")
    return parser.parse_args()

# ——————————————————————————————————————————————————————————
# Main flow
# ——————————————————————————————————————————————————————————

def main():
    args = parse_args()
    logger = configure_logging(args.output_log)
    password = getpass.getpass("Password: ")

    # Authentication
    logger.info("Authenticatie bij %s als %s", args.fqdn, args.username)
    sess_noauth = create_session()
    try:
        token = get_bearer_token(args.fqdn, args.username, password, sess_noauth)
    except Exception as e:
        logger.error("Login mislukt: %s", e)
        return
    sess = create_session(token)

    # Apply new neighborhood
    logger.info(
        "Lezen CSV '%s' en toevoegen neighborhood '%s'",
        args.input_csv, args.new_neighborhood
    )
    results = set_neighborhood_from_csv(
        args.fqdn, sess,
        args.input_csv, args.new_neighborhood
    )

    # Summary
    success = sum(1 for r in results if r[4])
    failed  = len(results) - success
    print(f"Klaar: {success} successen, {failed} fouten. Zie logfile voor details.")

if __name__ == '__main__':
    main()
