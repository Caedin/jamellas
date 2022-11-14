import pandas as pd
import copy
from collections import deque
import random
import json
import numpy as np
from copy import copy
import math

affixes = pd.read_csv('unique_inputs.txt', delimiter='\t')
weapons = pd.read_csv('weapons.txt', delimiter='\t')
armor = pd.read_csv('armor.txt', delimiter='\t')
jewelry = pd.read_csv('jewelry.txt', delimiter='\t')

weapons = weapons.query('spawnable == 1')
weapons = weapons.query('type != "tpot"')

armor = armor.query('spawnable == 1')
jewelry = jewelry.query('spawnable == 1')

weapons['itemclass'] = 'weap'
armor['itemclass'] = 'armo'

magic_weapon_types = set(['wand', 'staf', 'orb'])

w = list(weapons[['code', 'level', 'itemclass', 'type']].values)
a = list(armor[['code', 'level', 'itemclass', 'type']].values)
j = list(jewelry[['code', 'level', 'itemclass', 'type']].values)

q = deque(w + a + j)

# Load template file
with open('uniqueitemtemplate.json', 'r') as tfile:
    template = json.load(tfile)

uniques = []

def build_property_search_tree(affixes):
    root = {}
    minlvls = set(affixes['MinLvl'].values)
    for l in minlvls:
        itypeTable = affixes.query(f'MinLvl <= {l}')
        itypes = itypeTable['ItemType'].str.split(',')
        itypeset = set()
        for i in itypes:
            itypeset = itypeset.union(set([x.strip() for x in i]))

        root[l] = {}
        for i in itypeset:
            if i == 'shie':
                elemTypeTable = itypeTable[itypeTable['ItemType'].str.contains(i) | itypeTable['ItemType'].str.contains('armo')]
            else:
                elemTypeTable = itypeTable[itypeTable['ItemType'].str.contains(i)]

            elemType = set(elemTypeTable['Type'].values) - set(['all', 'magic'])
            root[l][i] = {}
            for e in elemType:
                if e in ['fire','lightning','poison','cold']:
                    hlevelTable = elemTypeTable[(elemTypeTable['Type'] == e) | (elemTypeTable['Type'] == 'magic')  | (elemTypeTable['Type'] == 'all')]
                else:
                    hlevelTable = elemTypeTable[(elemTypeTable['Type'] == e) | (elemTypeTable['Type'] == 'all')]
                h = [1,2,3]
                root[l][i][e] = {}
                for hlevel in h:
                    hTable = hlevelTable[hlevelTable['Hierarchy'] == hlevel]
                    
                    propCodes = list(set(hTable['Property'].values))

                    # double sample elemental prop codes
                    propCodes = propCodes + list(set(hTable[(hTable['Type'] == e)]['Property'].values)) 

                    # double sample prop codes with an exact item type match
                    propCodes = propCodes + list(set(hTable[(hTable['ItemType'] == i)]['Property'].values)) 

                    prop = hTable
                    root[l][i][e][hlevel] = { 'prop' : prop, 'propCodes' : propCodes }
    
    return root

root = build_property_search_tree(affixes)

def search_property(root, lvl, iclass, itype, etype, hlevel, used_prop_codes):
    # level filter
    minlvls = list(root.keys())
    minlvls = sorted(minlvls, reverse=True)
    for m in minlvls:
        if m > lvl:
            continue
        else:
            break
    mlvl = m

    def query(root, iclass, itype, etype, hlevel, strict = True):
        try:
            r1 = root[itype]
        except KeyError:
            r1 = root[iclass]
        
        r2 = r1[etype]

        try:
            r3 = r2[hlevel]
        except KeyError:
            if hlevel < 3:
                return query(root, iclass, itype, etype, hlevel+1)
            else:
                raise

        with pd.option_context('display.max_rows', None,
                       'display.max_columns', None,
                       'display.precision', 3,
                       ):
            # select
            used_prop_set = set(used_prop_codes)
            if strict == True:
                options = r3['prop']
                # Filter out invalid etypes
                options = options[~options["eTypeExclusions"].str.contains(etype).fillna(False)]

                # Filter out invalid itypes
                options = options[~options["iTypeExclusions"].str.contains(itype).fillna(False)]

                # Filter out unavailable props
                for p in used_prop_set:
                    options = options[~options["PropertyExclusions"].str.contains(p).fillna(False)]
                prop_codes = set(options['Property'].values) - used_prop_set
            else:
                prop_codes = set(r3['propCodes']) - used_prop_set

            if len(prop_codes) == 0:
                return query(root, iclass, itype, etype, ((hlevel+1) % 3) + 1)

            pc = random.sample(list(prop_codes), 1)[0]
            p = r3['prop'].query(f'Property == "{pc}"').sample()
            return p

    return query(root[mlvl], iclass, itype, etype, hlevel)


idx = 0
items = []
names = []
while q:
    code, level, iclass, itype = q.popleft()

    # Randomly uplevel the item
    level = level * (random.random() / 3 + 0.9)
    level = int(level)

    # Sanitize level 0 -> level 1
    level = max(level, 1)
    # Sanitize level > 100 -> level 99
    level = min(level, 99)

    # Extra chance to generate another unique of this type (carries forward upleveling)
    if random.randint(0, 2) == 0:
        q.append([code, level, iclass, itype])

    propertyCodes = []
    properties = []

    # Number of properties
    minprop, maxprop = int(np.log(level) * 1.5), int(np.log(level) * 3)
    minprop, maxprop = max(minprop, 3), max(min(maxprop, 12), 3)
    numprop = random.randint(minprop, maxprop)

    # Select elemental type
    if itype in magic_weapon_types:
        etype = random.sample(['cold', 'lightning', 'fire', 'poison'], 1)[0]
    else:
        etype = random.sample(['cold', 'lightning', 'fire', 'poison', 'normal', 'normal'], 1)[0]
    
    print(code, level, iclass, itype, f'etype = {etype}')

    names.append(f'jamellasunique{idx+407}')
    item = copy(template)
    item['index'] = f'jamellasunique{idx+407}'
    item['*ID'] = idx+407
    item['lvl'] = int(level)
    item['code'] = code

    c = 0
    hlevel = 1
    while c < numprop:
        prop = search_property(root, level, iclass, itype, etype, hlevel, propertyCodes)
        propertyCodes.append(prop['Property'].values[0])
        properties.append(prop)

        if hlevel == 1:
            hlevel = random.randint(1, 2)
        elif hlevel == 2:
            hlevel = random.sample([2, 2, 3], 1)[0]
        elif hlevel == 3:
            hlevel = random.sample([3, 3, 3, 1], 1)[0]


        param = prop['Param'].values[0]
        if type(param) == type('str') and param.isnumeric() == False:
            param = random.sample(param.split(','), 1)[0]
            param = param.strip()
        
        func = prop['LvlFunc'].values[0]
        minval = prop['MinValue'].values[0]
        maxval = prop['MaxValue'].values[0]

        try:
            if func != '':

                if func == 'linear':
                    minval = str(minval).replace('x', str(level))
                    maxval = str(maxval).replace('x', str(level))       
                    minval, maxval = math.floor(eval(minval)), math.ceil(eval(maxval))
                elif func == 'ln':
                    x = np.log(level)

                    minval = str(minval).replace('x', str(x))
                    maxval = str(maxval).replace('x', str(x))   
                    minval, maxval = math.floor(eval(minval)), math.ceil(eval(maxval))

                minval, maxval = float(minval), float(maxval)
        except SyntaxError:
            print('ERROR')
            print(prop, func, minval, maxval)
            raise
        except ValueError:
            print('ERROR')
            print(prop, func, minval, maxval)
            raise

        maxval = max(maxval, minval)
        item[f'prop{c+1}'] = prop['Property'].values[0]
        item[f'par{c+1}'] = '' if pd.isna(param) else param  
        item[f'min{c+1}'] = int(minval)
        item[f'max{c+1}'] = int(maxval)

        # Make ethereal a group property that includes indestruct. No support for group properties yet, so hard coding this one in for now. If ethereal is the last property on 12 property item, it might end up without indestruct. This is ok.
        if prop['Property'].values[0] == 'ethereal' and c+1 <= 12:
            c += 1
            item[f'prop{c+1}'] = 'indestruct'
            item[f'par{c+1}'] = ''
            item[f'min{c+1}'] = 1
            item[f'max{c+1}'] = 1

        c += 1
        
    idx += 1
    items.append(item)
    
original_uniques = pd.read_csv('original_uniques.txt', delimiter='\t', dtype = str)
df = pd.DataFrame(items)
df = pd.concat([original_uniques, df])
df.to_csv('uniqueitems.txt', index=False, sep='\t')

newnames = pd.read_csv('names.txt', delimiter = '\t', header=None)
newnames = set(newnames[0].values)
components = set()
for n in newnames:
    parts = n.split(' ')
    components = components.union(set(parts))

first = []
second = []
for k in components:
    if k in ['of', 'the']:
        continue
    first.append(k)
    if '\'' not in k and 'ing' not in k:
        second.append(k)


id = 273740
jsons = []
for n in names:
    while True:
        f, s = random.sample(first, 1)[0], random.sample(second, 1)[0]
        numparts = random.randint(1, 2)
        newname = s if numparts == 1 else ' '.join([f, s])
        if newname not in newnames:
            newnames.add(newname)
            break
    
    jsons.append(
        {
            "id": id,
            "Key": n,
            "enUS": newname
        }
    )
    id += 1

with open('names.json', 'w') as ofile:
    json.dump(jsons, ofile, indent=4)