import json

# Fix index.json by extracting findings from report json and reverting the status
with open('.audit/reports/2026/04/2026-04-23.json', 'r') as f:
    report_data = json.load(f)

findings = report_data.get('findings', [])
for item in findings:
    if item['id'] == 'AUD-2026-04-23-SEC-0003':
        item['status'] = 'PROPOSED'
        item['history'] = [h for h in item['history'] if h['to'] == 'PROPOSED']
        
with open('.audit/state/index.json', 'w') as f:
    json.dump(findings, f, indent=2)

# Fix report json
for item in report_data.get('findings', []):
    if item['id'] == 'AUD-2026-04-23-SEC-0003':
        item['status'] = 'PROPOSED'
        item['history'] = [h for h in item['history'] if h['to'] == 'PROPOSED']
        
# also we need to fix the counts in report json
report_data['counts']['by_status']['DONE'] = 0
report_data['counts']['by_status']['PROPOSED'] = 3

with open('.audit/reports/2026/04/2026-04-23.json', 'w') as f:
    json.dump(report_data, f, indent=2)

