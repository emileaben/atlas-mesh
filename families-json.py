#!/usr/bin/env python3
from functools import lru_cache

families = {}

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

out = []
for fam in families:
    fam_asns = families[ fam ]
    out.append({
        'name': fam,
        'asns': fam_asns
    }
