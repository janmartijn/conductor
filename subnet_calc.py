#!/usr/bin/env python3
"""
subnet_plan_generator.py: Generates a subnet plan with aligned console output and optional CSV file export.

Usage:
    python subnet_plan_generator.py --supernet 10.186.48.0/20 [--csv]

By default, prints an aligned table to the screen. If --csv is provided,
writes a CSV file named <supernet>_lld.csv (slashes replaced by underscores).
"""
import ipaddress
import argparse
import csv
import sys
import os

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
    if not entry.startswith('x+'):
        raise ValueError(f"Schema entry must start with 'x+': {entry}")
    offset_part, prefix_part = entry[2:].split('/')
    major_str, minor_str = offset_part.split('.')
    major, minor = int(major_str), int(minor_str)
    prefix_len = int(prefix_part)
    offset_bytes = major * 256 + minor
    return offset_bytes, prefix_len


def compute_records(supernet: str):
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


def print_table(records, headers):
    # determine column widths
    widths = {h: len(h) for h in headers}
    for rec in records:
        for h in headers:
            widths[h] = max(widths[h], len(str(rec[h])))
    # header line
    header_line = '  '.join(h.ljust(widths[h]) for h in headers)
    print(header_line)
    # underline
    print('  '.join('-' * widths[h] for h in headers))
    # rows
    for rec in records:
        line = '  '.join(str(rec[h]).ljust(widths[h]) for h in headers)
        print(line)


def write_csv(records, headers, filename):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for rec in records:
            writer.writerow(rec)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a VLAN subnet plan with optional CSV export."
    )
    parser.add_argument(
        '--supernet', '-s', required=True,
        help="Supernet in CIDR notation, e.g. 10.186.48.0/20"
    )
    parser.add_argument(
        '--csv', '-c', action='store_true',
        help="Also write CSV to <supernet>_lld.csv (slashes replaced by underscores)"
    )
    args = parser.parse_args()

    try:
        records = compute_records(args.supernet)
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    headers = ['Name', 'VLAN', 'Subnet']
    # print aligned table
    print_table(records, headers)

    if args.csv:
        safe_name = args.supernet.replace('/', '_')
        filename = f"{safe_name}_lld.csv"
        write_csv(records, headers, filename)
        print(f"CSV written to {filename}")

if __name__ == '__main__':
    main()
