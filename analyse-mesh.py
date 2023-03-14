#!/usr/bin/env python3
import json
import sys
import requests
from functools import lru_cache
import socket

state = None
with open("msm_state.json",'rt') as inf:
    state = json.load( inf )

msmid2prb = {}
for fam in state['measurements'].keys():
    for prb_id in state['measurements'][ fam ]:
        msm_id = state['measurements'][ fam ][ prb_id ]
        msmid2prb[ msm_id ] = str( prb_id )

'''
ip2prb = {}
for prb_id in state['prb_meta'].keys():
    ip = state['prb_meta'][ prb_id ]['address_v4']
    if ip in ip2prb:
        # one IP with multiple probes behind it. brrrr
        print("multiple probes behind single IP", prb_id, ip2prb[ ip ], ip)
        sys.exit()
    ip2prb[ ip ] = str( prb_id )
'''

def ip2hostname( ip ):
    host = None
    ans = socket.getnameinfo(( ip, 0), 0)
    ans = ans[0]
    if ans != ip:
        host = ans
    return host

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

def ip2name( ip ):
    host = None

def analyse_trace( msm_id, fam_asns ):
    results = []
    url = f'https://atlas.ripe.net/api/v2/measurements/{msm_id}/results/'
    req = requests.get( url )
    j = req.json()
    for m in j: # its a list
        if not 'dst_addr' in m:
            continue
        dst_addr = m['dst_addr']
        dst_asn = ip2as( dst_addr )

        prb_id = m['prb_id']
        prb_asn = str( state['prb_meta'][ str( prb_id ) ]['asn_v4'] )

        ips = {} # keyed by IP
        for hop in m['result']:
            hop_nr = hop['hop']
            if 'result' in hop:
                for hr in hop['result']:
                    if 'from' in hr:
                        ip = hr['from']
                        rtt = hr['rtt']
                        ips.setdefault( ip, {
                            'min_hop': hop_nr,
                            'min_rtt': rtt,
                            'asn': ip2as( ip ),
                            'host': ip2hostname( ip )
                        })
                        if ips[ ip ]['min_hop'] > hop_nr:
                            ips[ ip ]['min_hop'] = hop_nr
                        if ips[ ip ]['min_rtt'] > rtt:
                            ips[ ip ]['min_rtt'] = rtt
        ordered_ips = sorted( ips.keys() , key=lambda x: ips[ x ]['min_hop'] )
        print(f"# msm_id:{msm_id} from_prb:{prb_id} from_asn:{prb_asn} to_prb:{msmid2prb[ msm_id ]} to_asn:{dst_asn}")
        path_asns = []
        for ip in ordered_ips:
            asn = ips[ ip ]['asn']
            print( ips[ ip ]['min_hop'], ip, ips[ ip ]['host'], asn, ips[ ip ]['min_rtt'] )
            if asn != None and asn not in path_asns:
                path_asns.append( asn )
        print( path_asns )     
        print( json.dumps( m['result'] ) )

        all_asns_in_fam = True
        onpath_fam_asns_seen = False
        only_src_dst_asn = True

        for asn in path_asns:
            if not asn in fam_asns:
                all_asns_in_fam = False
            if asn in fam_asns and asn != prb_asn and asn != dst_asn:
                onpath_fam_asns_seen = True
            if asn != prb_asn and asn != dst_asn:
                only_src_dst_asn = False
        print(f"all_asns_in_fam:{all_asns_in_fam}, onpath_fam_asns_seen:{onpath_fam_asns_seen} only_src_dst_asn:{only_src_dst_asn}")
        results.append({
            'src_prb': prb_id,
            'dst_prb': msmid2prb[ msm_id ],
            'all_asns_in_fam': all_asns_in_fam,
            'onpath_fam_asns_seen': onpath_fam_asns_seen,
            'only_src_dst_asn': only_src_dst_asn
        })
    return results
        

r = []
for fam in state['measurements'].keys():
    this_f = {'fam': fam, 'results': []}
    fam_asns = set( state['families'][ fam ] )
    msms = state['measurements'][ fam ]
    for prb_id in msms.keys():
        msm_id = msms[ prb_id ]
        if msm_id:
            trace_results = analyse_trace( msm_id, fam_asns )
            this_f['results'].extend( trace_results )
    r.append( this_f )

with open('family-ties.json','wt') as outf:
    json.dump( r, outf, indent=2 ) 
    
