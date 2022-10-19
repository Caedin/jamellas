
import pandas as pd
import random
from copy import copy

class PropertySelector():

    def __init__(self, affix_file):
        self.affixes = pd.read_csv(affix_file, delimiter='\t')
        self.root = self.build_property_search_tree(self.affixes)

    def build_property_search_tree(self, affixes):
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

    def search_property(self, lvl, iclass, itype, etype, hlevel, used_prop_codes, forceClass = None):
        # level filter
        minlvls = list(self.root.keys())
        minlvls = sorted(minlvls, reverse=True)
        for m in minlvls:
            if m > lvl:
                continue
            else:
                break
        mlvl = m

        def query(r0, iclass, itype, etype, hlevel):
            try:
                r1 = r0[itype]
            except KeyError:
                r1 = r0[iclass]
            
            r2 = r1[etype]

            try:
                r3 = r2[hlevel]
            except KeyError:
                if hlevel < 3:
                    return query(r0, iclass, itype, etype, hlevel+1)
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
                return query(r0, iclass, itype, etype, ((hlevel+1) % 3) + 1)

            pc = random.sample(prop_codes, 1)[0]
            p = r3['prop'].query(f'Property == "{pc}"').sample()
            return p

        return query(self.root[mlvl], iclass, itype, etype, hlevel)


class SetPropertySelector():

    def __init__(self, affix_file):
        self.affixes = pd.read_csv(affix_file, delimiter='\t')
        self.default_search_order = ['itype', 'element']
        self.root = self.build_property_search_tree(self.affixes, self.default_search_order)

    def build_property_search_tree(self, affixes, ordered_properties):
        def add_layer(root, table, properties):
            if len(properties) == 0:
                return table
            else:
                prop = properties.pop()
                options = set(table[prop].values)
                for k in options:
                    if k == 'all':
                        root[k] = add_layer({}, table, copy(properties))
                    else:
                        root[k] = add_layer({}, table[(table[prop] == k) | (table[prop] == 'all')], copy(properties))
                return root
        root = add_layer({}, affixes, ordered_properties)
        return root

    def search_property(self, itype, etype, prop_type, used_prop_codes, forceClass = None):
        skills = set(['bar', 'ama', 'nec', 'sor', 'allskills', 'ass', 'dru', 'pal'])
        used_prop_set = set(used_prop_codes)
        skillFound = len(skills.intersection(used_prop_set)) > 0
        prop_codes = []


        try:
            r3 = self.root[etype][itype]
        except KeyError:
            try:
                r3 = self.root[etype]["all"]
            except KeyError:
                r3 = self.root["all"]["all"]

        
        
        if prop_type == 'ascaler':
            r3 = r3[r3['ascaler'] > 0]
        elif prop_type == 'pscaler':
            r3 = r3[r3['pscaler'] > 0]
        elif prop_type == 'fscaler':
            r3 = r3[r3['fscaler'] > 0]


        for propertyCode in set(r3['prop'].values):
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
            return self.search_property('all', 'all', prop_type, used_prop_codes, forceClass)

        pc = random.sample(prop_codes, 1)[0]
        p = r3.query(f'prop == "{pc}"').sample()
        return p