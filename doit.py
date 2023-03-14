#!/usr/bin/env python3
from functools import lru_cache
import sys
import requests
import time
import gzip
from radix import Radix
import pickle
from os.path import exists

families = {}

prb_meta = {} #  keyed by ID

as2name = {}

@lru_cache
def ip2as( ip ):
    asn = None
    try:
        d = requests.get( "https://stat.ripe.net/data/prefix-overview/data.json?max_related=0&resource=%s" % ( ip ) )
        asnjson = d.json()
        if len( asnjson['data']['asns'] ) > 0:
            asn = str( asnjson['data']['asns'][0]['asn'] )
        else:
            asn = None
    except:
        sys.stderr.write( "eeps: problem in ASN for ip: %s\n" %  (ip ) )
        return None ## todo proper error handling
    return asn



def probes_for_asn( asn ): # fills prb_meta as a side effect
    probes = []
    req = requests.get(f'https://atlas.ripe.net/api/v2/probes/?asn_v4={asn}&status=1')
    j = req.json()
    for prb in j['results']:
        prb_meta[ prb['id'] ] = prb
        probes.append( prb['id'] )
    return probes

def get_measurements( probes, fam_asns ): # get 2 hrs of measurements from this set (to random destinations)
    probes_fmt = ",".join( [str(x) for x in probes] )
    stop = int( time.time() )
    start = stop - 3600*2
    url = f'https://atlas.ripe.net/api/v2/measurements/5051/results/?probe_ids={probes_fmt}&start={start}&stop={stop}'
    req = requests.get( url )
    j = req.json()
    for m in j: # its a list
        if not 'dst_addr' in m:
            continue
        dst_addr = m['dst_addr']
        dst_asn = ip2as( dst_addr )

        prb_id = m['prb_id']
        prb_asn = str( prb_meta[ prb_id ]['asn_v4'] )

        as_path = []
        has_fam_asn = False
        fam_seen = set()
        for hop in m['result']:
            if 'result' in hop:
                for hr in hop['result']:
                    if 'from' in hr:
                        ip = hr['from']
                        asn = ip2as( ip )
                        as_path.append( asn )
                        if asn != prb_asn and asn in fam_asns:
                            has_fam_asn = True
                            fam_seen.add( asn )
        print( has_fam_asn, prb_asn, dst_asn, fam_asns, as_path )
        if has_fam_asn:
            print(f"#PRB ASN: {prb_asn} { as2name[ prb_asn ] }")
            print(f"#FAM ASN: {fam_seen} { [as2name[x] for x in fam_seen] }")


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

for fam in families:
    fam_asns = families[ fam ]
    #print( fam, fam_asns )
    for asn in fam_asns:
        probes = probes_for_asn( asn )
        if len( probes ) > 0: 
            measurements = get_measurements( probes, fam_asns )

