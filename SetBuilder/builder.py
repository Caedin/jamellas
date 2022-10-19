import pandas as pd
import copy
from collections import deque
import random
import json
import numpy as np
from copy import copy
import math

from property_selector import PropertySelector
from property_selector import SetPropertySelector

sets = pd.read_csv('set_inputs.txt', delimiter='\t')
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
    itemtemplate = json.load(tfile)
with open('settemplate.json', 'r') as tfile:
    settemplate = json.load(tfile)


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

idx = 1250

type_exclusions_by_class = {
    'ama' : ['wand', 'scep', 'knif', 'swor', 'axe', 'mace', 'club', 'hamm', 'tkni', 'taxe', 'staf', 'h2h', 'h2h2', 'orb', 'pelt', 'phlm', 'ashd', 'head'],
    'bar' : ['wand', 'scep', 'knif', 'staf', 'h2h', 'h2h2', 'orb', 'pelt', 'ashd', 'ajav', 'aspe', 'abow', 'head', 'bow', 'xbow'],
    'sor' : ['h2h', 'h2h2', 'pelt', 'ashd', 'ajav', 'aspe', 'abow', 'tkni', 'taxe', 'head','bow', 'xbow', 'jave'],
    'dru' : ['wand', 'scep', 'knif', 'tkni', 'taxe', 'staf', 'h2h', 'h2h2', 'orb', 'phlm', 'ashd', 'ajav', 'aspe', 'abow', 'head','bow', 'xbow', 'jave'],
    'ass' : ['wand', 'scep', 'knif', 'swor', 'axe', 'club', 'hamm', 'tkni', 'taxe', 'staf', 'orb', 'pelt', 'phlm', 'ashd', 'ajav', 'aspe', 'abow', 'head','bow', 'xbow', 'jave'],
    'nec' : ['scep', 'tkni', 'taxe', 'staf', 'h2h', 'h2h2', 'orb', 'pelt', 'phlm', 'ashd', 'ajav', 'aspe', 'abow','bow', 'xbow', 'jave'],
    'pal' : ['wand', 'knif', 'tkni', 'taxe', 'staf', 'h2h', 'h2h2', 'orb', 'pelt', 'phlm', 'ajav', 'aspe', 'abow', 'head', 'bow', 'xbow', 'jave']
}

# "[Class Skill Tab ID] = (Amazon = 0-2, Sorceress = 3-5, Necromancer = 6-8, Paladin = 9-11, Barbarian = 12-14, Druid = 15-17,  Assassin = 18-20)"
skilltablookup = { 
    'ama' : {
        34 : 0,
        35 : 0,
        25 : 0,
        15 : 0,
        24 : 0,
        32 : 1,
        31 : 2,
        21 : 2,
        11 : 2,
        12 : 2,
        22 : 2,
        26 : 2,
        7 : 2,
        16 : 2,
        27 : 2 
    }, 
    'ass' : {
        274 : 18,
        275 : 18,
        278 : 19,
        279 : 19,
        271 : 20,
        277 : 20,
    }, 
    'bar' : {
        148 : 13,
        145 : 13,
        153 : 13,
        151 : 14,
        147 : 14
    },
    'dru' : {
        250 : 15,
        225 : 15,
        229 : 15,
        249 : 15,
        248 : 16,
        238 : 16,
        233 : 16,
        247 : 17
    }, 
    'nec' : {
        75 : 6,
        85 : 6,
        94 : 6, 
        90 : 6,
        84 : 7, 
        93 : 7,
        92 : 7, 
        73 : 7
    },
    'pal' : {
        122 : 10,
        103 : 10,
        119 : 10,
        118 : 10,
        114 : 10,
        102 : 10,
        106 : 11,
        121 : 11
    },
    'sor' : {
        59 : 3,
        64 : 3,
        57 : 4,
        48 : 4,
        53 : 4,
        62 : 5,
        51 : 5,
        56 : 5,
        52 : 5
    }
}
itemcache = set()

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
    global itemcache
    f, s = random.sample(first, 1)[0], random.sample(second, 1)[0]
    newname = ' '.join([f, s])
    if newname in itemcache:
        return generateItemName(first, second)
    else:
        itemcache.add(newname)
        return newname

def create_items(firstNames, secondNames):
    global idx
    setItems = []
    sets = []
    propertySelector = PropertySelector(affix_file = 'set_item_affixes.txt')
    setPropertySelector = SetPropertySelector(affix_file = 'set_bonus_affixes.txt')

    # For each set...
    while q:
        skill, id, charclass, element, minilvl, type_restrictions, numitems = q.popleft()

        # Randomly uplevel the set
        level = random.randint(minilvl, 80)

        # Get Set Name
        setName = generateItemName(firstNames, secondNames)
        firstName = setName.split(' ')[0:1]

        print(skill, id, charclass, element, minilvl, level, numitems)

        setObject = copy(settemplate)
        setObject['index'] = setName
        setObject['name'] = setName

        exclusion_list = copy(type_exclusions_by_class[charclass])
        restriction_list = type_restrictions.split(',') if type(type_restrictions) == type('') else []

        items = []
        rings = 0
        hands = 2
        auraSet = False
        oskillSet = False
        exclusion_list.append('shie')

        # For each item ... 
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

            outitem = copy(itemtemplate)
            outitem['index'] = generateItemName(firstName, secondNames)
            outitem['*ID'] = idx+407
            outitem['set'] = setName
            outitem['lvl'] = int(level)
            outitem['item'] = item['code'].values[0]
            outitem['*ItemName'] = item['name'].values[0]

            c = 0
            hlevel = 1
            # For each property
            while c < numprop:
                prop = propertySelector.search_property(level, itemclass, itemtype, etype, hlevel, propertyCodes, forceClass = charclass)
                propertyCodes.append(prop['Property'].values[0])

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

            anumprop = random.randint(math.floor(numitems/2), min(5, numitems-1))

            apropertyCodes = []
            propertyType = 'ascaler'

            c = 0
            # For each aproperty itype, etype, prop_type, used_prop_codes,
            while c < anumprop:
                prop = setPropertySelector.search_property(itemclass, element, propertyType, apropertyCodes, forceClass = charclass)
                propcode = prop['prop'].values[0]
                apropertyCodes.append(propcode)


                param = prop['param'].values[0]
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

                if propcode == 'skill':
                    param = id
                elif propcode == 'skilltab':
                    param = skilltablookup[charclass][id]

                maxval = max(maxval, minval)
                outitem[f'aprop{c+1}a'] = propcode
                outitem[f'apar{c+1}a'] = '' if pd.isna(param) else param  
                outitem[f'amin{c+1}a'] = int(minval)
                outitem[f'amax{c+1}a'] = int(maxval)

                c += 1

            idx += 1
            items.append(outitem)
            setItems.append(outitem)

        # Build partial set props
        pnumprops = random.randint(2, max(2, min(4,numitems-1)))

        ppropertyCodes = []
        propertyType = 'pscaler'

        c = 0
        while c < pnumprops:
            prop = setPropertySelector.search_property('all', element, propertyType, ppropertyCodes, forceClass = charclass)
            propcode = prop['prop'].values[0]
            ppropertyCodes.append(propcode)

            param = prop['param'].values[0]
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

            if propcode == 'skill':
                param = id
            elif propcode == 'skilltab':
                param = skilltablookup[charclass][id]

            maxval = max(maxval, minval)
            setObject[f'PCode{c+2}a'] = propcode
            setObject[f'PParam{c+2}a'] = '' if pd.isna(param) else param  
            setObject[f'PMin{c+2}a'] = int(minval)
            setObject[f'PMax{c+2}a'] = int(maxval)

            c += 1

        # Build full set props
        fnumprops = random.randint(numitems, 8)

        fpropertyCodes = []
        propertyType = 'fscaler'

        c = 0
        while c < fnumprops:
            prop = setPropertySelector.search_property('all', element, propertyType, fpropertyCodes, forceClass = charclass)
            propcode = prop['prop'].values[0]
            fpropertyCodes.append(propcode)

            param = prop['param'].values[0]
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

            if propcode == 'skill':
                param = id
            elif propcode == 'skilltab':
                param = skilltablookup[charclass][id]

            maxval = max(maxval, minval)
            setObject[f'FCode{c+1}'] = propcode
            setObject[f'FParam{c+1}'] = '' if pd.isna(param) else param  
            setObject[f'FMin{c+1}'] = int(minval)
            setObject[f'FMax{c+1}'] = int(maxval)

            c += 1
        
        sets.append(setObject)

    df = pd.DataFrame(setItems)
    df.to_csv('setitems.txt', index=False, sep='\t')

    df = pd.DataFrame(sets)
    df.to_csv('sets.txt', index=False, sep='\t')

firstNames, secondNames = getNameComponents()
create_items(firstNames, secondNames)


id = 375000
jsons = []
for n in itemcache:
    jsons.append(
        {
            "id": id,
            "Key": n,
            "enUS": n
        }
    )
    id += 1

with open('names.json', 'w') as ofile:
    json.dump(jsons, ofile, indent=4)