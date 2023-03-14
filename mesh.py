#!/usr/bin/env python3
import sys
import requests
import time
import gzip
import json
from os.path import exists
import random


MAX_PROBES=2

families = {}

prb_meta = {} #  keyed by ID

measurements = {} # keyed by family

as2name = {}

with open("/Users/eaben/.atlas/auth",'rt') as inf:
    KEY = inf.readline()
    KEY = KEY.rstrip('\n')

def probes_for_asn( asn ): # fills prb_meta as a side effect
    probes = []
    req = requests.get(f'https://atlas.ripe.net/api/v2/probes/?asn_v4={asn}&status=1')
    j = req.json()
    for prb in j['results']:
        prb_meta[ prb['id'] ] = prb
        if 'address_v4' in prb and prb['address_v4'] != None:
            print( prb['address_v4'] )
            probes.append( prb['id'] )
    return probes

def do_traceroute( other_probes, dst_ip, desc ):
    spec = {
        "definitions": [
            {
                "target": dst_ip,
                "af": 4,
                "description": desc,
                "protocol": "ICMP",
                "type": "traceroute"
            }
        ],
        "probes": [
            {
                "value": ",".join( [str(x) for x in other_probes ] ),
                "type": "probes",
                "requested": len( other_probes )
            }
        ],
        "is_oneoff": True,
    } 
    print( other_probes, spec )
    req = requests.post(f"https://atlas.ripe.net/api/v2/measurements//?key={KEY}",
        data=json.dumps( spec ),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    )
    msm_id = None
    j = req.json()
    print( j )
    if 'measurements' in j: 
        msm_id = j['measurements'][0]
    return msm_id

##### MAIN


with open("member_probes_asn_see.csv",'rt') as inf:
    hdr = inf.readline() # remove header
    for line in inf:
        line.rstrip('\n')
        fields = line.split(';')
        family = fields[13]
        asn = fields[3]
        if asn.startswith('AS'):
            asn = asn[2:]
        as2name[ asn ] = fields[4]
        if family != '':
            families.setdefault( family, set() )
            families[ family ].add( asn )

a2p = {} # ASN to probes. keyed by asn

for fam in families:
    families[ fam ] = list( families[ fam ] ) # this is for later json generation (was a set)
    measurements.setdefault(fam, {})
    print(f"measuring fam: {fam}")
    fam_asns = families[ fam ]
    for asn in fam_asns:
        a2p[ asn ] = probes_for_asn( asn )
        if len( a2p[ asn ] ) > MAX_PROBES:
            random.shuffle( a2p[ asn ] )
            a2p[ asn ] = a2p[ asn ][0:1]

    # now take probes as targets
    for asn in fam_asns:
        # select probes for all other ASNs
        other_probes = []
        for other_asn in fam_asns:
            if other_asn != asn:
                for prb_id in a2p[ other_asn ]:
                    other_probes.append( prb_id )
        print( other_probes )
        for prb_id in a2p[ asn ]:
            dst_ip = prb_meta[ prb_id ]['address_v4']
            print( dst_ip )
            msm_id = do_traceroute( other_probes, dst_ip, f"dst:{prb_id} fam:{fam}" )
            measurements[ fam ][ prb_id ] = msm_id

state = {
    'families': families,
    'a2p': a2p,
    'as2name': as2name,
    'prb_meta': prb_meta,
    'measurements': measurements
}

with open("msm_state.json",'wt') as outf:
    json.dump( state, outf, indent=2 )
