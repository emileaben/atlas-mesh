#!/usr/bin/env python3
import sys
import requests
import time
import gzip
from radix import Radix
import pickle
from os.path import exists

families = {}

prb_meta = {} #  keyed by ID

ip2as = {}

def load_riswhois():
    pcl_fname = "./ris.lookup.pcl"
    if exists( pcl_fname ):
        ip2as = pickle.load( open( pcl_fname,'rb') )
        return ip2as
    else:
        ip2as = Radix()
        with gzip.open("riswhoisdump.IPv4.gz",'rt') as inf:
            for line in inf:
                line = line.rstrip('\n')
                if line.startswith('%'):
                    continue
                if line == '':
                    continue
                fields = line.split() 
                origin = fields[0]
                pfx = fields[1]
                pwr = int( fields[2] )
                if pwr < 10: # crap filter
                    continue

                # insert, but with care!
                rnode = ip2as.search_exact( pfx )
                if rnode:
                    rnode.data['origin'].add( origin )
                else:
                    rnode = ip2as.add( pfx )
                    rnode.data['origin'] = set([ origin ])
            pickle.dump(ip2as, open( pcl_fname,'wb') )
            return ip2as


def probes_for_asn( asn ): # fills prb_meta as a side effect
    probes = []
    req = requests.get(f'https://atlas.ripe.net/api/v2/probes/?asn_v4={asn}&status=1')
    j = req.json()
    for prb in j['results']:
        prb_meta[ prb['id'] ] = prb
        probes.append( prb['id'] )
    return probes

def get_measurements( probes, fam_asns ): # get 2 hrs of measurements from this set (to random destinations)
    print( probes )
    probes_fmt = ",".join( [str(x) for x in probes] )
    stop = int( time.time() )
    start = stop - 3600*2
    url = f'https://atlas.ripe.net/api/v2/measurements/5051/results/?probe_ids={probes_fmt}&start={start}&stop={stop}'
    req = requests.get( url )
    j = req.json()
    for m in j: # its a list
        prb_id = m['prb_id']
        prb_asn = str( prb_meta[ prb_id ]['asn_v4'] )
        dst_addr = m['dst_addr']
        dst_asn = None
        rnode = ip2as.search_best( dst_addr )
        if rnode:
            dst_asn = rnode.data['origin']

        as_path = []
        has_fam_asn = False
        for hop in m['result']:
            if 'result' in hop:
                for hr in hop['result']:
                    if 'from' in hr:
                        ip = hr['from']
                        rnode = ip2as.search_best( ip )
                        if rnode:
                            as_path.append( rnode.data['origin'] )
                            for asn in rnode.data['origin']:
                                if asn != prb_asn and asn in fam_asns:
                                    has_fam_asn = True
        print( has_fam_asn, prb_id, prb_asn, dst_addr, dst_asn, as_path )


##### MAIN

ip2as = load_riswhois()
print("LOADED", file=sys.stderr )


with open("member_probes_asn_see.csv",'rt') as inf:
    hdr = inf.readline() # remove header
    for line in inf:
        line.rstrip('\n')
        fields = line.split(';')
        family = fields[13]
        asn = fields[3]
        if asn.startswith('AS'):
            asn = asn[2:]
        if family != '':
            families.setdefault( family, set() )
            families[ family ].add( asn )

for fam in families:
    fam_asns = families[ fam ]
    print( fam, fam_asns )
    for asn in fam_asns:
        probes = probes_for_asn( asn )
        if len( probes ) > 0: 
            measurements = get_measurements( probes, fam_asns )

