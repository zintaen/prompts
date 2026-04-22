import json

with open('.audit/run_summary.json', 'r') as f:
    data = json.load(f)

data['run_id'] = 'run-2026-04-23T10:00:00Z-f006'
data['mode'] = 'scan'
data['invocation'] = {
    'effective_mode': 'scan',
    'provenance': {
      'source': 'inline',
      'wins_over': 'env',
      'env_value': 'execute'
    }
}
data['counts']['by_status']['DONE'] = 0
data['counts']['by_status']['PROPOSED'] = 3

with open('.audit/run_summary.json', 'w') as f:
    json.dump(data, f, indent=2)

