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
with open("probes_20230131.json",'r') as fd:
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
    if get_ris_asnname(asn):
        return get_asnname(asn)
    return ""

def append_results(results, record):
    """
    Adds a dictionary record to a list results, and removes an existing dictionary from results if it matches all key-value
    pairs of record except for the 'type' key, if the old 'type' value is 'Transit', and the new 'type' value of record is 'Source/Destination'
    replace the old record with new.

    Args:
    results (list): A list of dictionaries representing network data.
    record (dict): A dictionary representing a new network data record to be added to the list.

    Returns:
    A list of dictionaries representing network data with the new record added and/or an existing record removed.
    """
    # Check if new dictionary is already in the list
    if record in results:
        return results
    
    # Check if an existing dictionary in the list matches all key-value pairs of the new dictionary except for the 'type' key
    record_match = False
    for i in range(len(results)):
        record_match = True
        for key, value in record.items():
            #raise(0)
            if key != 'type' and results[i].get(key) != value:
                record_match = False
                break
        
        if record_match:
            # Remove dictionary from list if its 'type' value is 'Transit' and the new dictionary has a 'type' value of 'Source/Destination'
            if results[i].get('type') == 'Transit' and record.get('type') == 'Source/Destination' and \
               results[i].get('id') == record.get('id') and results[i].get('nodes') == record.get('nodes') and \
               results[i].get('cc') == record.get('cc') and results[i].get('name') == record.get('name'):
                   results.pop(i)
                   results.append(record)
                   break
    
    # Add new dictionary to list if it doesn't already exist
    if not record_match:
        results.append(record)
    
    return results




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
    pprint(unique_list)
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
def update_mesh(mesh, record):
    """
    Takes a list of dictionaries (mesh) and a new dictionary (record), and either increments the count value of an existing
    dictionary with the same key-value pairs or appends the new dictionary to the list if it doesn't exist.
    """
    for i in range(len(mesh)):
        if mesh[i]['src'] == record['src'] and mesh[i]['dst'] == record['dst']:
            mesh[i]['count'] += 1
            return mesh
    record['count'] = 1
    mesh.append(record)
    return mesh
def record_exists(mesh,record):
    for i in range(len(mesh)):
        if mesh[i]['src'] == record['src'] and mesh[i]['dst'] == record['dst']:
            return True
    return False

def analyse_trace(msm_id, fam_asns, results):
    """
    Analyzes the traceroute results for a specific measurement id (`msm_id`).
    The function extracts the destination address and its ASN, and iterates
    over each hop of the traceroute results to identify the IP addresses and 
    their corresponding minimum hop counts. If the last hop is same as the 
    desitnation IP address it add the dictionary showing traceroute was 
    completed. Else it adds a record with value 0 
    
    Parameters:
    - msm_id (int): The measurement ID for which to analyze the traceroute results.
    - fam_asns (Dict[int, str]): A dictionary mapping IP address families to ASNs.
    - results (List[Dict[str, str]]): A list of dictionaries representing the mesh topology.
    
    Returns:
    - results (List[Dict[str, str]]): The updated mesh topology.
    """    
    j = fetch_results(msm_id)
    if not j:
        sys.stderr.write(f"No response received from {msm_id} after 5 attempts. Returning empty results and links.")
        sys.exit()  # Quit the program
    for m in j: # its a list
        if not 'dst_addr' in m:
            pprint(m)
            sys.stderr.write("Cannot find destination address %s",dst_addr)
            sys.exit()  # Quit the program
            return [], []
        dst_addr = m['dst_addr']
        to_prb = msmid2prb[msm_id]
        dst_asn = str(prb2asnv4[str(to_prb)])

        prb_id = m['prb_id']
        prb_asn = str(state['prb_meta'][str(prb_id)]['asn_v4'])
        prb_cc = str(state['prb_meta'][str(prb_id)]['country_code'])
        ips = {} # keyed by IP
        for hop in m['result']:
            hop_nr = hop['hop']
            if 'result' in hop:
                for hr in hop['result']:
                    if 'from' in hr:
                        ip = hr['from']
                        rtt = hr['rtt']
                        ips.setdefault(ip, {
                            'min_hop': hop_nr,
                        })
                        if ips[ip]['min_hop'] > hop_nr:
                            ips[ip]['min_hop'] = hop_nr
        ordered_ips = sorted(ips.keys(), key=lambda x: ips[x]['min_hop'])
    
        record = {
                'src':str(prb_id)+" | "+prb_asn,
                'dst':str(to_prb)+" | "+dst_asn,
                'count': 0
                }
        if ordered_ips[-1] == dst_addr:
            results = update_mesh(results,record) 
        else:
            if not record_exists(results,record):
                results.append(record)




    return results



r = []
links_r = []
for fam, msms in state['measurements'].items():
    this_f = {'fam': fam, 'nodes': []}
    fam_asns = set(state['families'][fam])
    for prb_id, msm_id in msms.items():
        if msm_id:
            trace_asns = analyse_trace(msm_id, fam_asns,this_f['nodes'])
            this_f['nodes'].extend( trace_asns )
    r.append(this_f)
with open('debug-topology.json','wt') as outf:
    json.dump( r, outf, indent=2 )


