import json

files = ['.audit/state/index.json', '.audit/reports/2026/04/2026-04-23.json']

for file in files:
    with open(file, 'r') as f:
        data = json.load(f)
    
    for item in data:
        if 'history' in item:
            # deduplicate history
            new_hist = []
            seen = set()
            for h in item['history']:
                # create a tuple of all values to check uniqueness
                h_tuple = tuple(sorted(h.items()))
                if h_tuple not in seen:
                    seen.add(h_tuple)
                    new_hist.append(h)
            item['history'] = new_hist
            
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

