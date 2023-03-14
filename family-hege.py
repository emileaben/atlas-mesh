#!/usr/bin/env python3
import requests
import json

families = {}

DATE='2023-01-01'

as2name = {}

def find_hege_deps( asn, fam_asns ):
    deps = []
    fmt = DATE + 'T00%3A00%3A00.000Z'
    url = f"https://ihr.iijlab.net/ihr/api/hegemony/?format=json&af=4&timebin={fmt}&originasn={asn}"
    req = requests.get( url )
    d = req.json()
    if d['next'] != None:
        raise("didn't implement paging parsing!")
    for entry in d['results']:
        upstream_asn = str( entry['asn'] )
        if upstream_asn == asn:
            continue
        print( asn, entry['asn'], entry['hege'] )
        down_str = f"{asn} | {entry['originasn_name']}"
        up_str = f"{upstream_asn} | {entry['asn_name']}"
        deps.append({
            'downstream_asn': down_str,
            'upstream_asn': up_str,
            'dependency_pct': 100* entry['hege']
        })
    return deps

with open("member_probes_asn_see.csv",'rt') as inf:
    hdr = inf.readline() # remove header
    for line in inf:
        line.rstrip('\n')
        fields = line.split(';')
        family = fields[13]
        asn = fields[3]
        if asn.startswith('AS'):
            asn = asn[2:]
        asn = asn
        as2name[ asn ] = fields[4]
        if family != '':
            families.setdefault( family, set() )
            families[ family ].add( asn )

out = []
for fam in families:
    fam_asns = families[ fam ]
    deps = []
    for asn in fam_asns:
        deps.extend( find_hege_deps( asn, fam_asns ) )
    out.append({
        'name': fam,
        'asns': list( fam_asns ),
        'deps': deps
    })

with open('family-hegemony.json','wt') as outf:
    json.dump( out, outf, indent=2 )
