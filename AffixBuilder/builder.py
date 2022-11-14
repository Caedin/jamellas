import pandas as pd
import copy

df = pd.read_csv('affix_inputs.txt', delimiter='\t')
records = df.to_dict(orient='records')

lvlbreaks = [1] + list(range(5, 70, 5)) + list(range(70, 90, 2)) + list(range(90, 100, 1))

grouping_keys = [
    'Name',
    'version',
    'spawnable',
    'rare',
    'level',
    'maxlevel',
    'levelreq',
    'classspecific',
    'class',
    'classlevelreq',
    'frequency',
    'group',
    'mod1code',
    'mod1param',
    'mod1min',
    'mod1max',
    "mod2code",
    "mod2param",
    "mod2min",
    "mod2max",
    "mod3code",
    "mod3param",
    "mod3min",
    "mod3max",
    "transformcolor"
]

addon_columns = [
    "itype6",
    "itype7",
    "etype1",
    "etype2",
    "etype3",
    "etype4",
    "etype5",
    "multiply",
    "add"
]

template_row = {
    "Name"  : "emptyString",
    "version"  : 100,
    "spawnable"  : 1,
    "rare"  : 1,
    "level"  : "",
    "maxlevel"  : "",
    "levelreq"  : "",
    "classspecific"  : "",
    "class"  : "",
    "classlevelreq"  : "",
    "frequency"  : 1,
    "group"  : "",
    "mod1code"  : "",
    "mod1param"  : "",
    "mod1min"  : "",
    "mod1max"  : "",
    "mod2code"  : "",
    "mod2param"  : "",
    "mod2min"  : "",
    "mod2max"  : "",
    "mod3code"  : "",
    "mod3param"  : "",
    "mod3min"  : "",
    "mod3max"  : "",
    "transformcolor"  : "",
    "itype1"  : "",
    "itype2"  : "",
    "itype3"  : "",
    "itype4"  : "",
    "itype5"  : "",
    "itype6"  : "",
    "itype7"  : "",
    "etype1"  : "",
    "etype2"  : "",
    "etype3"  : "",
    "etype4"  : "",
    "etype5"  : "",
    "multiply"  : 0,
    "add"  : 0
}

def iteratevalue(prev, range_key, value_key, scaler_key, r):
    if prev:
        mid = (prev[1] + prev[0]) / 2
        rng = prev[1] - prev[0]
        scaler = (1 + int(r[scaler_key]) / 100)
        v = (mid, mid + rng * scaler) 
    else:
        o = r[range_key] / 2
        v = (r[value_key] - o, r[value_key] + o)
    return v

def genrow(lvl, grp, vals, r, itype, name):
    row = copy.copy(template_row)
    row["Name"] = row["Name"]
    row["level"] = lvl
    row["group"] = grp
    row["mod1code"] = r['code']
    row["mod1min"] = int(vals[0]) 
    row["mod1max"] = int(vals[1])
    if itype == 'p':
        row["itype1"] = r['primary']
    elif itype == 's':
        row["itype1"] = 'armo' if r['primary'] == 'weap' else 'weap'
    elif itype == 'j':
        row['itype1'] = 'ring'
        row['itype2'] = 'amul'
    elif itype == 'sc':
        row['itype1'] = 'jewl'
    return row


files = ['prefix', 'suffix']
grps = [1, 100]

class NamedLookup():
    def __init__(self):
        self.namedLookups = {}
        self.keybase = 'j'
        self.keyc = 0
        
    def getNamedLookup(self, name):
        if name not in self.namedLookups:
            self.namedLookups[name] = f'{self.keybase}{self.keyc:03d}'
            self.keyc += 1
        return self.namedLookups[name]

def compressDF(df, grouping_keys, addon_columns):
    compressionDict = {}
    keys = df.groupby(grouping_keys)

    items = keys['itype1'].apply(lambda x: [a for a in x if a != '']).reset_index(name='itype1')
    items['itype2'] = keys['itype2'].apply(lambda x: [a for a in x if a != '']).tolist()
    items['items'] = items['itype1'] + items['itype2']
    itypes = pd.DataFrame(items['items'].tolist(), index= items.index, columns=['itype1', 'itype2', 'itype3', 'itype4', 'itype5'])

    compressed = pd.DataFrame(keys.groups.keys(), columns = grouping_keys)
    compressed = compressed.join(itypes)
    for k in addon_columns:
        if k == 'multiply' or k == 'add':
            compressed[k] = 0
        else:
            compressed[k] = ''

    compressed = compressed.sort_values(['mod1code', 'level'])
    return compressed

lookup = NamedLookup()
for i in range(2):
    f = files[i]
    grp = grps[i]
    results = []

    for r in records:
        grp += 1
        prev = { 'p' : None, 's' : None, 'j' : None, 'sc' : None}

        for idx, lvl in enumerate(lvlbreaks):
            if lvl < r['minlvl']:
                continue
            else:
                item_types = ['p', 's', 'j', 'sc']
                for i in item_types:
                    val = iteratevalue(prev[i], f'{i}range', f'{i}value', 'lvlscalefactor', r)
                    
                    # Skip if value and range are 0
                    if val[0] == val[1] and val[0] == 0:
                        continue

                    # If range == 0, only run once
                    if (val[1] - val[0]) == 0:
                        if prev[i] is not None:
                            continue

                    name = r['prefix_name'] if f == 'prefix' else r['suffix_name']
                    key = lookup.getNamedLookup(name)
                    row = genrow(lvl, grp, val, r, i, key)

                    if r['lvlscalefactor'] != 'static':
                        row['maxlevel'] = lvlbreaks[idx+3] if idx+3 < len(lvlbreaks) else lvlbreaks[-1]

                    results += [row]
                    prev[i] = val

                if r['lvlscalefactor'] == 'static':
                    break

    df = pd.DataFrame(results)
    df = compressDF(df, grouping_keys, addon_columns)
    df.to_csv(f'magic{f}.txt', index=False, sep='\t')




# stringIndexStart = 27368
# string_json_template = {
#     "id": stringIndexStart,
#     "Key": "emptyString",
#     "enUS": ""
# }

# newStrings = []
# for idx, s in enumerate(lookup.namedLookups):
#     r = copy.copy(string_json_template)
#     r['id'] = stringIndexStart + idx
#     r["Key"] = lookup.namedLookups[s]
#     r["enUS"] = s if s != 'emptyString' else ''
#     newStrings.append(r)

# with open('item-nameaffixes.json', 'w') as ofile:
#     import json
#     ofile.writelines(json.dumps(newStrings, indent=4))

