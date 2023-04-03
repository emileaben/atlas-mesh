# Mesh Analysis Tool
This repository contains scripts to generate JSON files that provide insights into network topologies and hegemony among Autonomous Systems (ASes). The input for the scripts is a CSV file with family relations between organizations.

### Scripts
- families-json.py: This script creates a family JSON file from the given CSV. Note that this script is not used for anything at the moment.
- mesh.py: This script performs mesh measurements from the given CSV and outputs msm_state.json.
- analyse-mesh.py: This script analyzes msm_state.json and produces family-ties.json.
- doit.py: This script is used for debugging.
- family-hege.py: This script takes the CSV as input and outputs family-hegemony.json, which can be visualized in Observable.
- create-asns-topology.py: This script takes msm_state.json and produces a family-asn-topology.json file, which represents ASNs as nodes and shows their connectivity with links. Note that connectivity between ASes does not necessarily indicate peer-to-peer connectivity; an AS may be upstream to another AS
- debug-mesh.py : This script takes msm_stat.json and traverses all the traceroutes between source probe and destination probe. It generates debug-topology.json file which has a count of number of completed traceroutes between probes

### Output
The output JSON files can be attached to an ObservableHQ notebook for further analysis.
- family-ties.json (see: https://observablehq.com/d/2384281116321c32) 
- family-hegemony.json (see: https://observablehq.com/@emileaben/family-hegemony)
- family-asn-topology.json (see: https://observablehq.com/d/73ca0d3f2b393aa9)
- debug-topology.json (see: https://observablehq.com/d/19ab15bdf3c008cf) **Note: This file size is large and may cause slow loading times in the browser.**
