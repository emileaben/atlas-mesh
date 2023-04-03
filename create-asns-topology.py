#!/usr/bin/env python3
import json
import sys
import requests
from functools import lru_cache
from pprint import pprint
import socket
from itertools import count
import urllib.request
state = None
import time

with open("msm_state.json",'rt') as inf:
    state = json.load( inf )

asn2cc ={}
prb2asnv4 = {}
with open("probes_20230130.json",'r') as fd:
    prb_info = json.load(fd)
    for obj in prb_info['objects']:
        prb2asnv4[str(obj['id'])] = obj['asn_v4']
        asn2cc[str(obj['asn_v4'])] = obj['country_code']


msmid2prb = {}
for fam in state['measurements'].keys():
    for prb_id in state['measurements'][ fam ]:
        msm_id = state['measurements'][ fam ][ prb_id ]
        msmid2prb[ msm_id ] = str( prb_id )


asn_name = {}
with open("asnames/asnames.txt", "r") as f:
    for line in f:
        asn, name = line.strip().split(" ")
        asn_name[asn] = name

def asn2name(asn):
    """
    First tries to find if the shortned named exists in our mapping
    If it does not exist get the name from ripstate
    """
    if asn in asn_name:
        return asn_name[asn]
    if get_asnname(asn):
        return get_asnname(asn)
    return ""

def append_results(nodes_list, new_node):
    # loop through the nodes in the list
    for i in range(len(nodes_list)):
        # if the id matches and src_dst is 0
        if nodes_list[i]['id'] == new_node['id'] and nodes_list[i]['src_dst'] == 0:
            # replace the node with the new one
            nodes_list[i] = new_node
            # return the updated list
            return nodes_list
        # if the id matches and src_dst is 10, do not append the new node
        elif nodes_list[i]['id'] == new_node['id'] and nodes_list[i]['src_dst'] == 10:
            # return the original list
            return nodes_list
    # if the new node does not exist in the list, append it
    nodes_list.append(new_node)
    # return the updated list
    return nodes_list



def create_trace(msm_id, from_prb, from_asn, to_prb, to_asn, hops_str):
    hops_list = hops_str.strip().split('\n')
    hops = []
    for hop in hops_list:
        hop_parts = hop.split()
        hop_num = int(hop_parts[0])
        ip_address = hop_parts[1]
        hostname = hop_parts[2]
        asn = hop_parts[3]
        rtt = hop_parts[4]
        hop_dict = {
            "hop_num": hop_num,
            "ip_address": ip_address,
            "hostname": hostname,
            "asn": asn,
            "rtt": rtt
        }
        hops.append(hop_dict)

    trace = {
        "msm_id": msm_id,
        "from_prb": from_prb,
        "from_asn": from_asn,
        "to_prb": to_prb,
        "to_asn": to_asn,
        "hops": hops
    }

    with open('traces.json', 'a') as f:
        json.dump(trace, f)
        f.write('\n')


def is_asn_in_list(asn_list, asn):
    """
    Returns True if the given ASN exists in the list of dictionaries, False otherwise.
    
    Args:
        asn_list (list): A list of dictionaries representing ASNs.
        asn (int): The ASN to search for.

    Returns:
        bool: True if the ASN exists in the list of dictionaries, False otherwise.
    """
    for d in asn_list:
        if d.get('asn') == asn:
            return True
    return False


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

def ip2loc(ip):
    try:
        d = requests.get( "https://ipmap-api.ripe.net/v1/locate/all/?resources=%s" % ( ip ) ).json()
        if d['data']:
            return d['data'][ip]['countryCodeAlpha2']
        sys.stderr.write("no country mapping for ip address %s\n" %(ip))
        return "--"
    except:
        sys.stderr.write("issue accessing ipmap-service for %s\n" %(ip))
        return None

def get_asnname(asn):
    try:
        d = requests.get( "https://stat.ripe.net/data/as-names/data.json?resource=%s" % ( asn) ).json()
        if d['data']:
            if  'names' in d['data']:
                return d['data']['names'][asn]
            return None
    except:
        sys.stderr.write("no asn name for asn %s\n" %(asn))


def asn2loc(asn):
    if str(asn) in asn2cc:
        return asn2cc[str(asn)]
    url = f"https://stat.ripe.net/data/rir/data.json?resource={asn}&lod=2"
    with urllib.request.urlopen(url) as url:
        data = json.loads(url.read().decode())
    for rir in data['data']['rirs']:
        if rir['resource'] == asn:
            return rir.get('country')
    return None

def link_exists(links, link):
    """
    Check if a dictionary exists in a list of dictionaries.

    Args:
        links (list): A list of dictionaries to search in.
        link (dict): The dictionary to search for.

    Returns:
        bool: True if link is in links, False otherwise.
    """
    for l in links:
        if l == link:
            return True
    return False

# def find_asn_id(asn, asn_list):
#     """
#     Given an ASN and a list of dictionaries containing mapping between
#     ASNs and ASN IDs, return the corresponding ASN ID for the given ASN.
#     If the given ASN is not found in the list, return None.
# 
#     Args:
#         asn (str): The ASN to search for.
#         asn_list (list): A list of dictionaries containing mapping between
#             ASNs and ASN IDs.
# 
#     Returns:
#         int or None: The ASN ID for the given ASN if found, otherwise None.
#     """
# 
#     for item in asn_list:
#         if item.get('asn') == asn:
#             return item.get('id')
#     return None

def add_data(prev_results, new_results):
    """
    Combines two lists of dictionaries into a single list of unique dictionaries.

    Args:
        prev_results (list): The previous list of dictionaries.
        new_results (list): The new list of dictionaries to add to the previous results.

    Returns:
        list: A new list of unique dictionaries containing all the dictionaries from prev_results and new_results.
    """
    combined_list = prev_results + new_results
    
    unique_list = []
    for dict in combined_list:
        if dict not in unique_list:
            unique_list.append(dict)
    return unique_list




def fetch_results(msm_id):
    """
    Fetches the results for a given measurement ID from the RIPE Atlas API.
    
    The function will try to fetch the results up to 5 times before giving up. If it
    fails to get a response after 5 attempts, an empty list will be returned.
    
    Parameters:
    msm_id (int): The measurement ID for which to fetch the results.
    
    Returns:
    list: A list of dictionaries containing the measurement results, or an empty list
    if the function fails to get a response after 5 attempts.
    """
    url = f'https://atlas.ripe.net/api/v2/measurements/{msm_id}/results/'
    
    for i in range(5):
        try:
            req = requests.get(url)
            req.raise_for_status()
            return req.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"Error fetching data from {url}: {e}. Retrying ({i+1}/5)...")
            time.sleep(1)
    
    return []


asn_ids ={}



def analyse_trace( msm_id,to_prb,results,links ):
    j = fetch_results(msm_id)
    if not j:
        url = f'https://atlas.ripe.net/api/v2/measurements/{msm_id}/results/'
        print(f"No response received from {url} after 5 attempts. Returning empty results and links.")
        raise(0)
        return [], []
    for m in j: # its a list
        dst_addr = m['dst_addr']
        #dst_asn = ip2as( dst_addr )
        #to_prb = msmid2prb[ msm_id ]
        dst_asn = str(prb2asnv4[str(to_prb)])
        if dst_asn:
            dst_cc = asn2loc(dst_asn)
            #dst_cc = ip2loc(dst_addr)
            dst_asn_name = asn2name(dst_asn)

        prb_id = m['prb_id']
        prb_asn = str( state['prb_meta'][ str( prb_id ) ]['asn_v4'] )
        prb_cc = str(state['prb_meta'][str(prb_id)]['country_code'])
        
        print(f"# msm_id:{msm_id} from_prb:{prb_id} from_asn:{prb_asn} to_prb:{msmid2prb[ msm_id ]} to_asn:{dst_asn}")
        if dst_asn=='5483' or prb_asn =='5483':# Ignoring MAGYAR wrong classified in 4iG
            continue

        prev_asn = prb_asn
        next_asn =''
#         if msm_id == 49282290:
#             pprint(m)
#             pprint(j)
#             print(prb_asn)
#             print(dst_asn)
#             raise(0)


        if not  is_asn_in_list(results, prb_asn):
            results= append_results(results,{
                'id':int(prb_asn),
                'nodes': int(prb_asn),
                'cc': prb_cc,
                'name':asn2name(prb_asn),
                'src_dst':10
                })
        ips = {} # keyed by IP
        for hop in m['result']:
            hop_nr = hop['hop']
            if 'result' in hop:
                for hr in hop['result']:
                    if 'from' in hr:
                        ip = hr['from']
                        rtt = hr['rtt']
                        asn = ip2as(ip)
                        ips.setdefault( ip, {
                            'min_hop': hop_nr,
                            'min_rtt': rtt,
                            'asn': asn,
                            'host': ip2hostname( ip ),
                            #'cc':ip2loc(ip),
                            'asn_name':asn2name(asn)
                        })
                        if ips[ ip ]['min_hop'] > hop_nr:
                            ips[ ip ]['min_hop'] = hop_nr
                        if ips[ ip ]['min_rtt'] > rtt:
                            ips[ ip ]['min_rtt'] = rtt
        ordered_ips = sorted( ips.keys() , key=lambda x: ips[ x ]['min_hop'] )
        #pprint(ordered_ips)
        #raise(0)

        print(f"# msm_id:{msm_id} from_prb:{prb_id} from_asn:{prb_asn} to_prb:{msmid2prb[ msm_id ]} to_asn:{dst_asn}")
        path_asns = [prb_asn]



        for ip in ordered_ips:
            asn = ips[ ip ]['asn']
            #cc = ips[ip]['cc']
            asn_name = ips[ip]['asn_name']
            print( ips[ ip ]['min_hop'], ip, ips[ ip ]['host'], asn, ips[ ip ]['min_rtt'] )

            if asn != None and asn not in path_asns:
                path_asns.append( asn )
                if not  is_asn_in_list(results, asn):
                    results = append_results(results,{
                        'id':int(asn),
                        'nodes': int(asn),
                        'cc':'Transit',
                        #'cc': asn2loc(asn)
                        'name':asn2name(asn),
                        'src_dst':0,
                        })
            if asn !=None and asn!=prev_asn:
               #src_id = find_asn_id(str(prev_asn),results) 
               #target = find_asn_id(str(asn),results)
               link = {
                       'source':int(prev_asn),
                       'target':int(asn)
                       }
               if prev_asn != asn:
                   prev_asn = asn
                   if not link_exists(links,link):
                       links.append(link)


        if not is_asn_in_list(results, dst_asn):
            results = append_results(results,{
                'id':int(dst_asn),
                'nodes': int(dst_asn),
                'cc': dst_cc,
                'name':dst_asn_name,
                'src_dst':10
                })

    return results,links
#    return results,links
r = []
links_r = []
#asn_id = count(0)
counter = 0
for fam, msms in state['measurements'].items():
    this_f = {'fam': fam, 'nodes': [], 'links': []}
    fam_asns = set(state['families'][fam])

    for prb_id, msm_id in msms.items():
        if msm_id:
            trace_asns, links = analyse_trace(msm_id, prb_id,this_f['nodes'],this_f['links'])
            if trace_asns and links:
                this_f['nodes']=add_data(this_f['nodes'],trace_asns)
                this_f['links']=add_data(this_f['links'],links)
    r.append(this_f)
with open('family-asn-topology.json','wt') as outf:
    json.dump( r, outf, indent=2 )


