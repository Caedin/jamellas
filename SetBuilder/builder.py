import pandas as pd
import copy
from collections import deque
import random
import json
import numpy as np
from copy import copy
import math

sets = pd.read_csv('set_inputs.txt', delimiter='\t')
affixes = pd.read_csv('set_item_affixes.txt', delimiter='\t')
weapons = pd.read_csv('weapons.txt', delimiter='\t')
armor = pd.read_csv('armor.txt', delimiter='\t')
jewelry = pd.read_csv('jewelry.txt', delimiter='\t')

weapons = weapons.query('spawnable == 1')
weapons = weapons.query('type != "tpot"')


armor = armor.query('spawnable == 1')
jewelry = jewelry.query('spawnable == 1')

weapons['itemclass'] = 'weap'
armor['itemclass'] = 'armo'

# Load template file
with open('itemtemplate.json', 'r') as tfile:
    template = json.load(tfile)


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

def search_property(root, lvl, iclass, itype, etype, hlevel, used_prop_codes, forceClass = None):
    # level filter
    minlvls = list(root.keys())
    minlvls = sorted(minlvls, reverse=True)
    for m in minlvls:
        if m > lvl:
            continue
        else:
            break
    mlvl = m

    def query(root, iclass, itype, etype, hlevel):
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

        # select
        skills = set(['bar', 'ama', 'nec', 'sor', 'allskills', 'ass', 'dru', 'pal'])
        used_prop_set = set(used_prop_codes)
        skillFound = len(skills.intersection(used_prop_set)) > 0
        prop_codes = []
        for propertyCode in r3['propCodes']:
            if skillFound:
                if propertyCode in skills:
                    continue
            else:
                # If force class is applied, skip non matching skills
                if propertyCode in skills and forceClass is not None:
                    if propertyCode not in {forceClass, 'allskills'}:
                        continue

                # Don't add class non assassin class skills to assassin weapons
                if itype in ['h2h', 'h2h2'] and propertyCode in skills and propertyCode != 'ass':
                    continue

                # Don't add class non amazon class skills to amazon weapons
                if itype in ['abow', 'ajav', 'aspe'] and propertyCode in skills and propertyCode != 'ama':
                    continue

                # Don't add class non druid class skills to druid pelts
                if itype in ['pelt'] and propertyCode in skills and propertyCode != 'dru':
                    continue
                
                # Don't add class non barb class skills to barb helms
                if itype in ['phlm'] and propertyCode in skills and propertyCode != 'bar':
                    continue
                
                # Don't add class non pally class skills to pally shields
                if itype in ['ashd'] and propertyCode in skills and propertyCode != 'pal':
                    continue

                # Don't add class non necro class skills to necro heads
                if itype in ['head'] and propertyCode in skills and propertyCode != 'nec':
                    continue


            if propertyCode not in used_prop_set:
                prop_codes.append(propertyCode)

        if len(prop_codes) == 0:
            return query(root, iclass, itype, etype, ((hlevel+1) % 3) + 1)

        pc = random.sample(prop_codes, 1)[0]
        p = r3['prop'].query(f'Property == "{pc}"').sample()
        return p

    return query(root[mlvl], iclass, itype, etype, hlevel)

def fetch_random_item(type_exclusions, type_restrictions = [], minlvl = 0, handsAvail = 2, allowHybrid = False):
    if handsAvail <= 0:
        type_exclusions.append('shie')
        df = pd.concat([armor, jewelry])
    else:
        w = weapons
        if len(type_restrictions) > 0:
            w = w.query(f'type in @type_restrictions')

        if handsAvail == 1 and allowHybrid:
            w = w[(w['2handed'] != 1) | (w['1or2handed'] == 1)]
        elif handsAvail == 1 and ~allowHybrid:
            w = pd.DataFrame()

        df = pd.concat([w, armor, jewelry])
    
    if minlvl > 0:
        df = df.query(f'level > {minlvl-6} and level <= {minlvl+6}')
    if len(type_exclusions) > 0:
        df = df.query(f'type not in @type_exclusions')

    sample = df.sample()
    return sample

def update_exclusion_types(exclusion_list, itemtype):
    exclusion_list.append(itemtype)
    if itemtype == 'helm':
        exclusion_list.append('circ')
    elif itemtype == 'circ':
        exclusion_list.append('helm')

num_items = np.random.normal(4, 2, sets.shape[0])
sets['NumberOfItems'] = num_items.astype(int)
sets['NumberOfItems'] = np.minimum(6, sets['NumberOfItems'])
sets['NumberOfItems'] = np.maximum(2, sets['NumberOfItems'])

sets = list(sets.values)
q = deque(sets)

idx = 0

type_exclusions_by_class = {
    'ama' : ['wand', 'scep', 'knif', 'swor', 'axe', 'mace', 'club', 'hamm', 'tkni', 'taxe', 'staf', 'h2h', 'h2h2', 'orb', 'pelt', 'phlm', 'ashd', 'head'],
    'bar' : ['wand', 'scep', 'knif', 'staf', 'h2h', 'h2h2', 'orb', 'pelt', 'ashd', 'ajav', 'aspe', 'abow', 'head', 'bow', 'xbow'],
    'sor' : ['h2h', 'h2h2', 'pelt', 'ashd', 'ajav', 'aspe', 'abow', 'tkni', 'taxe', 'head','bow', 'xbow', 'jave'],
    'dru' : ['wand', 'scep', 'knif', 'tkni', 'taxe', 'staf', 'h2h', 'h2h2', 'orb', 'phlm', 'ashd', 'ajav', 'aspe', 'abow', 'head','bow', 'xbow', 'jave'],
    'ass' : ['wand', 'scep', 'knif', 'swor', 'axe', 'club', 'hamm', 'tkni', 'taxe', 'staf', 'orb', 'pelt', 'phlm', 'ashd', 'ajav', 'aspe', 'abow', 'head','bow', 'xbow', 'jave'],
    'nec' : ['scep', 'tkni', 'taxe', 'staf', 'h2h', 'h2h2', 'orb', 'pelt', 'phlm', 'ashd', 'ajav', 'aspe', 'abow','bow', 'xbow', 'jave'],
    'pal' : ['wand', 'knif', 'tkni', 'taxe', 'staf', 'h2h', 'h2h2', 'orb', 'pelt', 'phlm', 'ajav', 'aspe', 'abow', 'head', 'bow', 'xbow', 'jave']
}


def getNameComponents():
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
    return first, second

def generateItemName(first, second):
    f, s = random.sample(first, 1)[0], random.sample(second, 1)[0]
    newname = ' '.join([f, s])
    return newname

def create_items(firstNames, secondNames):
    global idx
    sets = []
    while q:
        skill, id, charclass, element, minilvl, type_restrictions, numitems = q.popleft()

        # Randomly uplevel the set
        level = random.randint(minilvl, 80)

        # Get Set Name
        setName = generateItemName(firstNames, secondNames)
        firstName = setName.split(' ')[0:1]

        print(skill, id, charclass, element, minilvl, level, numitems)

        exclusion_list = copy(type_exclusions_by_class[charclass])
        restriction_list = type_restrictions.split(',') if type(type_restrictions) == type('') else []

        items = []
        rings = 0
        hands = 2
        auraSet = False
        oskillSet = False
        exclusion_list.append('shie')

        while len(items) < numitems:
            item = fetch_random_item(exclusion_list, type_restrictions = restriction_list, minlvl = level, handsAvail = hands, allowHybrid = True if charclass == 'bar' else False)
            item['level'] = level

            itemtype = item['type'].values[0]
            itemclass = item['itemclass'].values[0]

            if itemtype == 'shie':
                hands -= 1
                update_exclusion_types(exclusion_list, itemtype)
            elif itemclass == 'weap':
                hands -= 1
                if item['2handed'].values[0] == 1:
                    hands -= 1
                
                if item['1or2handed'].values[0] == 1 and charclass == 'bar':
                    hands += 1
                
                if hands == 1:
                    exclusion_list.remove('shie')
            elif itemtype == 'ring':
                rings += 1
                if rings >= 2:
                    exclusion_list.append(itemtype)
            else:
                update_exclusion_types(exclusion_list, itemtype)
            
            # Sanitize level 0 -> level 1
            level = max(level, 1)
            # Sanitize level > 100 -> level 99
            level = min(level, 99)

            propertyCodes = []
            properties = []

            if auraSet: 
                propertyCodes.append('aura')
            if oskillSet:
                propertyCodes.append('oskill')

            # Number of properties
            minprop, maxprop = int(np.log(level) * 1), int(np.log(level) * 1.5)
            minprop, maxprop = max(minprop, 2), max(min(maxprop, 6), 3)
            numprop = random.randint(minprop, maxprop)

            # Select elemental type
            etype = element

            outitem = copy(template)
            outitem['index'] = generateItemName(firstName, secondNames)
            outitem['*ID'] = idx+407
            outitem['set'] = setName
            outitem['lvl'] = int(level)
            outitem['item'] = item['code'].values[0]
            outitem['*ItemName'] = item['name'].values[0]

            c = 0
            hlevel = 1
            while c < numprop:
                prop = search_property(root, level, itemclass, itemtype, etype, hlevel, propertyCodes, forceClass = charclass)
                propertyCodes.append(prop['Property'].values[0])
                properties.append(prop)

                if prop['Property'].values[0] == 'aura':
                    auraSet = True
                elif prop['Property'].values[0] == 'oskill':
                    oskillSet = True

                if hlevel == 1:
                    hlevel = random.randint(1, 2)
                elif hlevel == 2:
                    hlevel = random.sample([2, 2, 3], 1)[0]
                elif hlevel == 3:
                    hlevel = random.sample([3, 3, 3, 1], 1)[0]


                param = prop['Param'].values[0]
                if type(param) == type('str') and param.isnumeric() == False:
                    param = random.sample(param.split(','), 1)[0]
                
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
                outitem[f'prop{c+1}'] = prop['Property'].values[0]
                outitem[f'par{c+1}'] = '' if pd.isna(param) else param  
                outitem[f'min{c+1}'] = int(minval)
                outitem[f'max{c+1}'] = int(maxval)

                c += 1
            idx += 1
            items.append(outitem)
            sets.append(outitem)
        
    df = pd.DataFrame(sets)
    df.to_csv('set_test.txt', index=False, sep='\t')


firstNames, secondNames = getNameComponents()
create_items(firstNames, secondNames)