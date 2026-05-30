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
    ('Outlaw', 'SL', '2,4-D & dicamba (liquid concentrate)'),
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
    ('Clasp', 5, 'DRA', 'drift reduction agent (ready-to-use)', '', False),
    ('Justified', 5, 'DRA', 'drift reduction agent', '', False),
    ('PointBlank WM', 5, 'DRA', 'drift reduction + deposition agent', '', False),
]

# --- Generic / third-party adjuvants from the EDak product list. Placement by
# function, same rule as HELENA_ADJUVANTS.
# (name, group, short-code, type description, note, ammonium?)
EDAK_ADJUVANTS = [
    ('Accuquest WM', 1, 'WC', 'water conditioner + deposition aid (AMS replacement)',
        'Non-AMS; also aids deposition.', False),
    ('Ad-Spray 80', 5, 'NIS', 'nonionic surfactant (NIS)', '', False),
    ('Ad-Spray 90 NIS', 5, 'NIS', 'nonionic surfactant (NIS)', '', False),
    ('Blendex VHC', 1, 'COMP', 'compatibility / stabilizing agent',
        'Add early to keep tank-mix partners compatible.', False),
    ('Cohere', 5, 'NIS', 'nonionic spreader-sticker surfactant', '', False),
    ('Crop Oil Concentrate', 4, 'COC', 'crop oil concentrate (COC)', '', False),
    ('Kinetic', 5, 'NIS', 'nonionic surfactant + organosilicone penetrant', '', False),
    # Liquid Chisel: per Helena/operator guidance, treat as a soluble-liquid
    # solution — see MANUAL_PRODUCTS below. (NOT an MSO.)
    ('Optima', 5, 'NIS', 'nonionic surfactant', '', False),
    ('Premium MSO', 4, 'MSO', 'methylated seed oil (MSO)', '', False),
    ('Re-Duce', 1, 'WC', 'water conditioner / AMS replacement + surfactant',
        'Contains ammonium sulfate — avoid with dicamba formulations.', True),
    ('Transactive HC', 1, 'WC', 'AMS-replacement water conditioner',
        'Contains ammonium salts — avoid with dicamba formulations.', True),
    ('Trico Pro', 1, 'WC', 'AMS-replacement water conditioner',
        'Contains ammonium salts — avoid with dicamba formulations.', True),
]

# --- Manually-added products (not in the NDSU, Helena, or EDak sources).
# Hand-entered; formulation confirmed with the user / off the label.
# (name, formulation code, active ingredients, class)
MANUAL_PRODUCTS = [
    ('Shieldex', 'SC', 'tolpyralate', 'herbicide'),
    ('Regev', 'EC', 'difenoconazole & tea tree oil (Melaleuca alternifolia) (fungicide)', 'fungicide'),
    ('Medal EC', 'EC', 'metolachlor', 'herbicide'),
    ('Medal II EC', 'EC', 's-metolachlor', 'herbicide'),
    ('Explorer', 'SC', 'mesotrione', 'herbicide'),
    ('Atrazine 4F', 'F', 'atrazine', 'herbicide'),
    ('Liquid Chisel', 'SL', 'soluble-liquid adjuvant — mixes with the solutions', 'adjuvant'),
    ('Quilt', 'SE', 'azoxystrobin + propiconazole (fungicide)', 'fungicide'),
]

# --- Helena foliar nutritionals (NBU 2026 guide, Nutritionals section pp.31-42).
# Coded by physical form: dry chelated soluble microgranules -> SG (group 1);
# soluble/wettable powders -> SP/WP; liquid "FL" flowables -> F (group 3);
# liquid "LC"/foliar solutions -> SL (group 5); soil granular -> G (not mixed).
# (name, formulation code, description)
NUTRITIONAL_PRODUCTS = [
    # Axilo — dry EDTA-chelated soluble micronutrient microgranules (group 1)
    ('Axilo Calcium', 'SG', '10% Ca, EDTA-chelated (foliar micronutrient)'),
    ('Axilo Copper', 'SG', '15% Cu, EDTA-chelated (foliar micronutrient)'),
    ('Axilo Magnesium', 'SG', '6% Mg, EDTA-chelated (foliar micronutrient)'),
    ('Axilo Manganese', 'SG', '13% Mn, EDTA-chelated (foliar micronutrient)'),
    ('Axilo Iron', 'SG', '13% Fe, EDTA-chelated (foliar micronutrient)'),
    ('Axilo Zinc', 'SG', '15% Zn, EDTA-chelated (foliar micronutrient)'),
    ('Axilo BMZ', 'SG', 'boron, molybdenum + chelated manganese & zinc (foliar micronutrient)'),
    ('Axilo Mix 5', 'SG', 'multi-micronutrient blend B/Mn/Zn/Cu/Mo (foliar micronutrient)'),
    ('Axilo RMX', 'SG', 'multi-micronutrient blend (foliar micronutrient)'),
    # Brexil — dry LPCA-chelated soluble micronutrient microgranules (group 1)
    ('Brexil Calcium', 'SG', '15% Ca + boron, LPCA-chelated (foliar micronutrient)'),
    ('Brexil CBZ', 'SG', 'calcium, boron & zinc, LPCA-chelated (foliar micronutrient)'),
    ('Brexil Magnesium', 'SG', '5% Mg, LPCA-chelated (foliar micronutrient)'),
    ('Brexil Manganese', 'SG', '10% Mn, LPCA-chelated (foliar micronutrient)'),
    ('Brexil Iron', 'SG', '10% Fe, LPCA-chelated (foliar micronutrient)'),
    ('Brexil Zinc', 'SG', '10% Zn, LPCA-chelated (foliar micronutrient)'),
    ('Brexil Combi', 'SG', 'multi-micronutrient blend, LPCA-chelated (foliar micronutrient)'),
    ('Brexil Multi', 'SG', 'boron, magnesium, iron, manganese & zinc, LPCA-chelated (foliar micronutrient)'),
    # Ele-Max — mixed forms (FL flowable g3 / LC liquid g5 / WP g2 / SP g1)
    ('Ele-Max Boron LC', 'SL', '10.9% B liquid (foliar nutritional)'),
    ('Ele-Max CalBor Zn FL', 'F', '15% Ca, 6% B, 3% Zn flowable (foliar nutritional)'),
    ('Ele-Max Calcium FL', 'F', '23.8% Ca flowable (foliar nutritional)'),
    ('Ele-Max Copper FL', 'F', '33% Cu flowable (foliar nutritional)'),
    ('Ele-Max Magnesium FL', 'F', '20% Mg flowable (foliar nutritional)'),
    ('Ele-Max Manganese FL', 'F', '27.4% Mn flowable (foliar nutritional)'),
    ('Ele-Max ManZinc FL', 'F', '14% Mn, 19.5% Zn flowable (foliar nutritional)'),
    ('Ele-Max Phos-K-Mag LC', 'SL', '29% P2O5, 5% K2O, 4.1% Mg liquid (foliar nutritional)'),
    ('Ele-Max PhosCal-Zinc FL', 'F', 'phosphorus, 15% Ca, 13% Zn flowable (foliar nutritional)'),
    ('Ele-Max PhoZ B Mag WP', 'WP', 'phosphorus, boron, magnesium & zinc wettable powder (foliar nutritional)'),
    ('Ele-Max Sulfur Complete SP', 'SP', '14.5% S soluble powder + micronutrients (foliar nutritional)'),
    ('Ele-Max Super Zinc FL', 'F', '40% Zn flowable (foliar nutritional)'),
    ('Ele-Max BMZ', 'F', '1-0-0 liquid with boron, manganese & zinc (foliar nutritional)'),
    ('Ele-Max Hi-Phos LC', 'SL', 'high-analysis orthophosphate + EDTA-chelated Cu/Fe/Mn/Zn (foliar nutritional)'),
    ('Ele-Max Sulfur EZ', 'SL', '10-0-0 + 10% sulfur + boron, liquid (foliar nutritional)'),
    # KickStand — EDTA micronutrient liquid solutions (group 5); DG/Greens-Grade are dry
    ('KickStand Cu', 'SL', 'EDTA-chelated copper liquid (foliar micronutrient)'),
    ('KickStand Zn 7', 'SL', '7% zinc EDTA liquid (foliar micronutrient)'),
    ('KickStand MicroMix', 'SL', 'EDTA micronutrient mix, liquid (foliar micronutrient)'),
    ('KickStand RTU', 'SL', 'ready-to-use EDTA micronutrient liquid (foliar micronutrient)'),
    ('KickStand DG+Zn', 'WDG', 'zinc micronutrient, dry granular (verify form)'),
    ('KickStand DG + Fe Greens Grade', 'WDG', 'iron micronutrient, greens-grade dry granular (verify form)'),
    # Other named liquid foliar fertilizers (group 5 solutions)
    ('Coron Metra 25 B', 'SL', '25-0-0 controlled-release nitrogen + boron, foliar (foliar nutritional)'),
    ('ENC Flex', 'SL', '11-6-5 + chelated micronutrients, ammonia-free foliar solution (foliar nutritional)'),
    ('K-Leaf Versa', 'SL', '29% K2O + chelated micronutrients, foliar (foliar nutritional)'),
    ('Metra Full Bor', 'SL', 'controlled-release nitrogen + boron, foliar (foliar nutritional)'),
    ('Tracite 10 B', 'SL', '10% boron liquid (foliar nutritional)'),
    ('Trafix Zn', 'SL', 'liquid zinc, Asset technology (foliar nutritional)'),
    # Iron chelates
    ('Ferrilene', 'SG', '100% EDDHA-chelated 6% iron, water-soluble microgranules (nutritional)'),
    ('Ferrigran Black Iron', 'G', 'granular EDDHA+HBED iron + humic, soil-applied (not tank-mixed)'),
    # BioScience foliar biostimulants / nutritionals (NBU pp.23, 26)
    ('Megafol', 'SL', '3-0-8 foliar biostimulant with plant extracts (BioScience)'),
    ('Orbix', 'SL', '8-5-3 NPK + micronutrients ammonia-free foliar solution with plant extracts (BioScience)'),
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
    for src, adjlist in (('Helena', HELENA_ADJUVANTS), ('EDak', EDAK_ADJUVANTS)):
        for name, grp, code, typ, note, ammonium in adjlist:
            if name.lower() in by_name:
                continue
            item = {'name': name, 'code': code, 'group': grp,
                    'groupLabel': GROUP_LABEL[grp], 'ai': typ,
                    'adjuvant': True, 'source': src}
            if note:
                item['note'] = note
            if ammonium:
                item['ammonium'] = True
            by_name[name.lower()] = item
            out.append(item)
            adj += 1

    # --- EDak generic/branded pesticides (curated in edak_products.json) ---
    edak_added = edak_review = 0
    try:
        edak = json.load(open('edak_products.json', encoding='utf-8'))
    except FileNotFoundError:
        edak = []
    for p in edak:
        key = p['name'].lower()
        if key in by_name:
            continue
        code = p.get('code')
        grp = CODE_GROUP.get(code) if code else None
        item = {'name': p['name'], 'code': code, 'group': grp,
                'groupLabel': GROUP_LABEL.get(grp, 'Unknown — check product label'),
                'ai': p.get('ai', ''), 'adjuvant': False, 'source': 'EDak'}
        if p.get('review'):
            item['review'] = True
            edak_review += 1
        by_name[key] = item
        out.append(item)
        edak_added += 1

    # --- Manually-added products ---
    manual_added = 0
    for name, code, ai, _cls in MANUAL_PRODUCTS:
        key = name.lower()
        if key in by_name:
            continue
        grp = CODE_GROUP.get(code) if code else None
        item = {'name': name, 'code': code, 'group': grp,
                'groupLabel': GROUP_LABEL.get(grp, 'Unknown — check product label'),
                'ai': ai, 'adjuvant': False, 'source': 'Manual'}
        by_name[key] = item
        out.append(item)
        manual_added += 1

    # --- Helena foliar nutritionals ---
    nutri_added = 0
    for name, code, ai in NUTRITIONAL_PRODUCTS:
        key = name.lower()
        if key in by_name:
            continue
        grp = CODE_GROUP.get(code) if code else None
        item = {'name': name, 'code': code, 'group': grp,
                'groupLabel': GROUP_LABEL.get(grp, 'Unknown — check product label'),
                'ai': ai, 'adjuvant': False, 'source': 'Nutritional'}
        by_name[key] = item
        out.append(item)
        nutri_added += 1

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
    print(f'Adjuvants added (Helena + EDak): {adj}')
    print(f'EDak products added: {edak_added} (review-flagged: {edak_review})')
    print(f'Manual products added: {manual_added}')
    print(f'Nutritional products added: {nutri_added}')
    print(f'TOTAL entries in data.js: {len(out)}')


if __name__ == '__main__':
    main()
