"""Merge NDSU herbicide compendium (products.json) with the Helena NBU 2026
product guide (Mode of Action Guide formulations + adjuvants) into data.js.

Run order:  py parse_compendium.py   (writes products.json from the NDSU PDF)
            py build_data.py         (merges Helena data, writes data.js)
"""
import json

# Formulation code -> A.P.P.L.E.S. group (ND Weed Control Guide W-253, p.86)
CODE_GROUP = {
    'SG': 1, 'SP': 1,
    'DF': 2, 'WDG': 2, 'WG': 2, 'WP': 2, 'XP': 2, 'DG': 2,
    'ASC': 3, 'ACS': 3, 'SC': 3, 'SE': 3, 'ME': 3, 'F': 3, 'L': 3,
    'ZC': 3, 'CS': 3, 'AS': 3, 'DC': 3,
    'EC': 4, 'EW': 4, 'OD': 4, 'AE': 4,
    'SL': 5, 'S': 5,
    'G': 0, 'PS': 0,
}
GROUP_LABEL = {
    1: 'Soluble powders (SG, SP, dry fertilizer)',
    2: 'Dry powders (DF, WDG, WP)',
    3: 'Liquid flowables / suspensions (SC, SE, ME, F, L, CS, ZC, DC)',
    4: 'Emulsifiable concentrates (EC, EW, OD)',
    5: 'Solutions (S, SL)',
    0: 'Dry granular / pelleted (not tank-mixed)',
}

# --- Helena herbicides & fungicides (NBU 2026 guide, Mode of Action Guide pp.119-124) ---
# (name, formulation code, active ingredients)
HELENA_PRODUCTS = [
    ('Antares', 'SC', 'sulfentrazone'),
    ('Antares Complete', 'EC', 'sulfentrazone & s-metolachlor & metribuzin'),
    ('Antares Prime', 'SC', 'sulfentrazone & cloransulam-methyl'),
    ('Antares Pro', 'SC', 'sulfentrazone'),
    ('Barrage HF', 'EC', '2,4-D ester'),
    ('Barrage Evo', 'EC', '2,4-D ester'),
    ('Battleship III', 'EC', 'MCPA ester & fluroxypyr ester & triclopyr amine'),
    ('Centrus', 'WDG', 'indaziflam & rimsulfuron'),
    ('Double Up B + D', 'EC', '2,4-D ester & bromoxynil ester'),
    ('Empyros', 'EC', 'tolpyralate & s-metolachlor'),
    ('Empyros Triad', 'SE', 'tolpyralate & s-metolachlor & atrazine'),
    ('Empyros Triad Flex', 'SE', 'tolpyralate & s-metolachlor & atrazine'),
    ('EndRun', 'SL', '2,4-D amine & MCPA amine & dicamba DMA'),
    ('Full Deck', 'DC', 'MCPA acid & fluroxypyr ester & clopyralid acid'),
    ('Hardball', 'DC', '2,4-D acid'),
    ('Latigo', 'EC', '2,4-D acid & dicamba acid'),
    ('Latigo Bold', 'EC', '2,4-D acid & dicamba acid'),
    ('On Deck', 'SL', '2,4-D acid & dicamba acid'),
    ('On Deck Icon', 'SL', '2,4-D acid & dicamba acid'),
    ('Opti-Amine', 'SL', '2,4-D amine'),
    ('Opti-DGA', 'SL', 'dicamba DGA'),
    ('Outlaw', 'EC', '2,4-D ester & dicamba acid'),
    ('Parlay', 'EC', 'bromoxynil ester & MCPA ester & fluroxypyr ester'),
    ('Provonis', 'SC', 'cloransulam-methyl'),
    ('Sinister', 'DC', 'fomesafen acid'),
    ('TapOut', 'EC', 'clethodim'),
    ('Trump Card', 'DC', 'fluroxypyr ester & 2,4-D acid'),
    ('Trycera', 'DC', 'triclopyr acid'),
    ('Unison', 'DC', '2,4-D acid'),
    ('Velossa', 'SL', 'hexazinone'),
    ('Vision', 'DC', 'dicamba acid'),
    ('Voucher', 'DC', 'fluroxypyr ester & MCPA acid'),
    ('WildCard', 'EC', 'MCPA ester'),
    ('WildCard Xtra', 'EC', 'bromoxynil ester & MCPA ester'),
    # Fungicides
    ('Avaris', 'SE', 'azoxystrobin & propiconazole (fungicide)'),
    ('Avaris 2XS', 'SE', 'azoxystrobin & propiconazole (fungicide)'),
    ('Mogul', 'SC', 'azoxystrobin & difenoconazole (fungicide)'),
    ('Odyssey', 'SE', 'phosphorous acid & tebuconazole & azoxystrobin (fungicide)'),
    ('Helena Prophyt', 'SL', 'phosphorous acid (fungicide)'),
    ('Quanta', 'SL', 'phosphorous acid (fungicide)'),
    ('Reveille', 'SL', 'phosphorous acid (fungicide)'),
    ('Tycoon', 'SC', 'azoxystrobin & difenoconazole (fungicide)'),
    ('Viathon', 'SE', 'phosphorous acid & tebuconazole (fungicide)'),
    ('Zonix', None, 'rhamnolipid biosurfactant (biofungicide) — liquid concentrate, check label'),
]

# --- Helena adjuvants (NBU 2026 guide pp.7-17). No formulation code is given;
# placement follows the guide's rule by FUNCTION: water conditioner/AMS -> group 1,
# oil (COC/MSO) -> group 4, surfactant -> group 5, drift agent -> group 5 (add last).
# (name, group, short-code, type description, note, ammonium?)
HELENA_ADJUVANTS = [
    ('Agri-Dex', 4, 'COC', 'crop oil concentrate (COC)', '', False),
    ('Cide Winder', 4, 'COC/MSO', 'multifunctional oil — usable as COC, MSO or NIS',
        'Can act as COC, MSO or NIS; placement here assumes oil use — check use rate on label.', False),
    ('Dyne-Amic', 4, 'MSO', 'methylated seed oil + organosilicone surfactant', '', False),
    ('Fire-Zone', 4, 'MSO', 'methylated seed oil + surfactant',
        'For burndown/desiccation; not for over-the-top use except harvest aid.', False),
    ('Grounded', 4, 'oil/DRA', 'oil-based adjuvant with drift reduction',
        'Oil-based; also reduces drift. Useful for pre-emergence/soil applications.', False),
    ('Zaar', 4, 'MSO', 'methylated seed oil + activator + water conditioner',
        'MSO blend that also conditions water and lowers pH.', False),
    ('Induce', 5, 'NIS', 'nonionic surfactant (NIS)', '', False),
    ('Cohort', 1, 'WC', 'water conditioner / herbicide activator',
        'Companion for AMS-requiring herbicides; lowers pH and fights hard-water antagonism.', False),
    ('Diversify', 1, 'WC', 'non-AMS water conditioner',
        'Non-AMS — suitable with dicamba and over-the-top auxin formulations.', False),
    ('Hel-Fire', 1, 'WC', 'water conditioner + deposition/activator (oil-free)', '', False),
    ('InterActive', 1, 'WC', 'AMS-replacement surfactant + water conditioner',
        'Contains ammonium salts — avoid with dicamba formulations.', True),
    ('Oculus Maxx', 1, 'WC', 'non-AMS water conditioner + activator + drift mgmt',
        'Non-AMS, dicamba/auxin-compatible; also provides drift management.', False),
    ('Quest', 1, 'WC', 'water conditioner (AMS replacement/supplement)', '', False),
    ('ReQuest', 1, 'WC', 'water conditioner with ammoniacal nitrogen',
        'Contains ammoniacal nitrogen — avoid with dicamba formulations.', True),
    ('Smoke', 1, 'WC', 'water conditioner + herbicide activator (oil-free)', '', False),
    ('Clasp', 5, 'DRA', 'drift reduction agent (ready-to-use)', 'Add last.', False),
    ('Justified', 5, 'DRA', 'drift reduction agent', 'Add last.', False),
    ('PointBlank WM', 5, 'DRA', 'drift reduction + deposition agent', 'Add last.', False),
]


def main():
    ndsu = json.load(open('products.json', encoding='utf-8'))
    by_name = {}
    out = []
    for p in ndsu:
        p = dict(p, adjuvant=False, source='NDSU')
        by_name[p['name'].lower()] = p
        out.append(p)

    added = filled = 0
    for name, code, ai in HELENA_PRODUCTS:
        grp = CODE_GROUP.get(code) if code else None
        key = name.lower()
        if key in by_name:
            ex = by_name[key]
            if ex.get('group') is None and grp is not None:  # fill an NDSU gap
                ex['code'], ex['group'] = code, grp
                ex['groupLabel'] = GROUP_LABEL[grp]
                ex['source'] = 'NDSU+Helena'
                filled += 1
            continue
        item = {'name': name, 'code': code, 'group': grp,
                'groupLabel': GROUP_LABEL.get(grp, 'Unknown — check product label'),
                'ai': ai, 'adjuvant': False, 'source': 'Helena'}
        by_name[key] = item
        out.append(item)
        added += 1

    adj = 0
    for name, grp, code, typ, note, ammonium in HELENA_ADJUVANTS:
        if name.lower() in by_name:
            continue
        item = {'name': name, 'code': code, 'group': grp,
                'groupLabel': GROUP_LABEL[grp], 'ai': typ,
                'adjuvant': True, 'source': 'Helena'}
        if note:
            item['note'] = note
        if ammonium:
            item['ammonium'] = True
        out.append(item)
        adj += 1

    out.sort(key=lambda p: p['name'].lower())
    with open('data.js', 'w', encoding='utf-8') as f:
        f.write('// Auto-generated. Sources: NDSU ND Weed Control Guide W-253 (2026) pp.86,120-128;\n')
        f.write('// Helena NBU 2026 Product Guide (formulations pp.119-124, adjuvants pp.7-17).\n')
        f.write('// Regenerate with: py parse_compendium.py && py build_data.py\n')
        f.write('window.PRODUCTS = ')
        json.dump(out, f, ensure_ascii=False)
        f.write(';\n')

    print(f'NDSU products: {len(ndsu)}')
    print(f'Helena products added: {added}, filled NDSU gaps: {filled}')
    print(f'Helena adjuvants added: {adj}')
    print(f'TOTAL entries in data.js: {len(out)}')


if __name__ == '__main__':
    main()
