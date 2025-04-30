#!/usr/bin/env python3
"""
subnet_plan_generator.py: Generates a CSV subnet plan with Name, VLAN and Subnet columns
based on a given supernet and fixed schema.

Usage:
    python subnet_plan_generator.py --supernet 10.186.48.0/20 > subnets.csv

Example output (CSV):
    Name,VLAN,Subnet
    workstation-wired,400,10.186.48.0/23
    Reserved,xxx,10.186.50.0/23
    ...
"""
import ipaddress
import argparse
import csv
import sys

# Hardcoded schema entries: (Name, VLAN, relative offset/prefix)
SCHEMA = [
    ('workstation-wired', '400', 'x+0.0/23'),
    ('Reserved', 'xxx', 'x+2.0/23'),
    ('printer', '450', 'x+4.0/24'),
    ('Servers', '480-488', 'x+5.0/24'),
    ('server_1', '480', 'x+5.0/27'),
    ('workstation-wireless', '460', 'x+6.0/23'),
    ('internal_DMZ (can be accessed from internal network)', '100', 'x+8.0/24'),
    ('external_DMZ (only external connectivity)', '110', 'x+9.0/24'),
    ('IOT networks', '120-130', 'x+10.0/23'),
    ('cctv', '120', 'x+10.0/27'),
    ('access_control', '130', 'x+11.0/27'),
    ('voip', '200', 'x+12.0/24'),
    ('Reserved', 'xxx', 'x+13.0/24'),
    ('Reserved', 'xxx', 'x+14.0/24'),
    ('net_mgmt', '900', 'x+15.0/24'),
]

def parse_schema_entry(entry: str):
    """
    Parses a schema entry of the form 'x+<major>.<minor>/<prefix_len>'.
    Returns a tuple (offset_bytes, prefix_len).
    """
    if not entry.startswith('x+'):
        raise ValueError(f"Schema entry must start with 'x+': {entry}")
    offset_part, prefix_part = entry[2:].split('/')
    major_str, minor_str = offset_part.split('.')
    major, minor = int(major_str), int(minor_str)
    prefix_len = int(prefix_part)
    offset_bytes = major * 256 + minor
    return offset_bytes, prefix_len


def compute_records(supernet: str):
    """
    Computes a list of records with Name, VLAN, and Subnet for CSV output.
    """
    base_net = ipaddress.IPv4Network(supernet)
    records = []
    for name, vlan, entry in SCHEMA:
        offset_bytes, prefix_len = parse_schema_entry(entry)
        net_addr_int = int(base_net.network_address) + offset_bytes
        net = ipaddress.IPv4Network((net_addr_int, prefix_len))
        records.append({
            'Name': name,
            'VLAN': vlan,
            'Subnet': net.with_prefixlen,
        })
    return records


def main():
    parser = argparse.ArgumentParser(
        description="Generate a CSV with Name, VLAN, and Subnet from a supernet."
    )
    parser.add_argument(
        '--supernet', '-s', required=True,
        help="Supernet in CIDR notation, e.g. 10.186.48.0/20"
    )
    args = parser.parse_args()

    try:
        records = compute_records(args.supernet)
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    fieldnames = ['Name', 'VLAN', 'Subnet']
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    for rec in records:
        writer.writerow(rec)

if __name__ == '__main__':
    main()
