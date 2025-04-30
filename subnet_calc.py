#!/usr/bin/env python3
"""
subnet_plan_generator.py: Generates a detailed subnet plan based on a given supernet and a fixed schema.

Usage:
    python subnet_plan_generator.py --supernet 10.186.48.0/20

Example output:
    10.186.48.0/23
    10.186.50.0/23
    10.186.52.0/24
    ...
"""
import ipaddress
import argparse
import sys

# Hardcoded schema entries: relative offsets and prefix lengths
SCHEMA_ENTRIES = [
    'x+0.0/23',
    'x+2.0/23',
    'x+4.0/24',
    'x+5.0/24',
    'x+5.0/27',
    'x+6.0/23',
    'x+8.0/24',
    'x+9.0/24',
    'x+10.0/23',
    'x+10.0/27',
    'x+11.0/27',
    'x+12.0/24',
    'x+13.0/24',
    'x+14.0/24',
    'x+15.0/24',
]

def parse_schema_entry(entry: str):
    """
    Parses a schema entry of the form 'x+<major>.<minor>/<prefix_len>'.
    Returns a tuple (offset_bytes, prefix_len).
    """
    if not entry.startswith('x+'):
        raise ValueError(f"Schema entry must start with 'x+': {entry}")
    try:
        offset_part, prefix_part = entry[2:].split('/')
        major_str, minor_str = offset_part.split('.')
        major = int(major_str)
        minor = int(minor_str)
        prefix_len = int(prefix_part)
    except Exception:
        raise ValueError(f"Invalid schema entry format: {entry}")

    # Each 'major' step moves by 256 addresses (one /24 block)
    offset_bytes = major * 256 + minor
    return offset_bytes, prefix_len


def compute_subnets(supernet: str):
    """
    Given a supernet CIDR (e.g. '10.186.48.0/20'), computes subnets
    based on the hardcoded SCHEMA_ENTRIES.
    Returns a list of IPv4Network objects.
    """
    base_net = ipaddress.IPv4Network(supernet)
    results = []
    for entry in SCHEMA_ENTRIES:
        offset_bytes, prefix_len = parse_schema_entry(entry)
        new_net_addr_int = int(base_net.network_address) + offset_bytes
        try:
            new_net = ipaddress.IPv4Network((new_net_addr_int, prefix_len))
        except Exception:
            raise ValueError(f"Calculated network invalid for entry {entry}")
        results.append(new_net)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Generate an explicit subnet plan from a supernet and the fixed schema."
    )
    parser.add_argument(
        '--supernet', '-s', required=True,
        help="Supernet in CIDR notation, e.g. 10.186.48.0/20"
    )
    args = parser.parse_args()

    try:
        subnets = compute_subnets(args.supernet)
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    for net in subnets:
        print(net.with_prefixlen)

if __name__ == '__main__':
    main()
