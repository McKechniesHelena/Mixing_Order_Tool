"""Curate EDak price-sheet products into edak_products.json (committable — NO pricing).

Source workbook (IC- EDak Price Sheet) holds INTERNAL COST/MARGIN data and is
gitignored, as is the raw extraction edak_xlsx.json. This script reads that raw
extraction and emits only product NAME / formulation CODE / active INGREDIENT /
class — the same kind of data already in build_data.py's HELENA_PRODUCTS.

Run:  py build_edak.py        (writes edak_products.json)
Then: py build_data.py        (merges everything into data.js)

Formulation code for each kept product is resolved in this priority order:
  1. code embedded in the product name (e.g. "Aatrex 4L" -> L) — reliable
  2. AI-match to an existing product in data.js that already has a code
  3. manual OVERRIDES table below (best-effort, flagged review=True)
Anything still unresolved is reported so it can be added to OVERRIDES.
"""
import json, re, csv

# formulation code -> (A.P.P.L.E.S. group number, short label) for the review sheet
GROUP = {
    'SG': (1, 'soluble powder'), 'SP': (1, 'soluble powder'),
    'WSP': (1, 'soluble powder'),
    'DF': (2, 'dry powder'), 'WDG': (2, 'dry powder'), 'WG': (2, 'dry powder'),
    'WP': (2, 'dry powder'), 'XP': (2, 'dry powder'), 'DG': (2, 'dry powder'),
    'SC': (3, 'flowable/suspension'), 'SE': (3, 'flowable/suspension'),
    'ME': (3, 'flowable/suspension'), 'F': (3, 'flowable/suspension'),
    'L': (3, 'flowable/suspension'), 'ZC': (3, 'flowable/suspension'),
    'CS': (3, 'flowable/suspension'), 'DC': (3, 'flowable/suspension'),
    'EC': (4, 'emulsifiable conc.'), 'EW': (4, 'emulsifiable conc.'),
    'OD': (4, 'emulsifiable conc.'),
    'SL': (5, 'solution'), 'S': (5, 'solution'),
    'G': (0, 'granular (not mixed)'), 'PS': (0, 'granular (not mixed)'),
}

# --- class filter: keep tank-mixable pesticides + adjuvants only -------------
KEEP_WORDS = (
    'herbicide', 'fungicide', 'insecticide', 'miticide',
    'plant growth regulator',
    'surfactant', 'crop oil', 'oil concentrate', 'oil surfactant',
    'methylated seed oil', 'mso', 'water conditioner', 'drift',
    'deposition', 'defoam', 'antifoam', 'foam concentrate', 'tank cleaner',
    'compatibility', 'spreader', 'sticker', 'wetter', 'penetrant',
    'activator', 'ams', 'adjuvant',
)
DROP_WORDS = (
    'nutrient', 'inoculant', 'seed colorant', 'soil amendment', 'fertilizer',
    'seed treatment', 'plantability', 'goose', 'stimulant', 'aquatic',
    'fumigant', 'nitrogen stabilizer', 'nitrification', 'vertebrate',
)

def keep_class(c):
    c = (c or '').lower().strip()
    if not c:
        return False
    if any(w in c for w in DROP_WORDS):
        return False
    return any(w in c for w in KEEP_WORDS)

# --- formulation code embedded in a product name -----------------------------
# longest first so WDG matches before WG, etc.
NAME_CODES = ['WDG', 'WSP', 'WG', 'WP', 'SG', 'SP', 'DF', 'DG', 'XP',
              'SC', 'SE', 'ME', 'ZC', 'CS', 'EC', 'EW', 'OD', 'SL']
NAME_CODE_RE = re.compile(r'\b(' + '|'.join(NAME_CODES) + r')\b')
# numeric-suffixed codes: "4L", "2EC", "75WG", "4SC", "1.5F", "25WP" ...
NUM_CODE_RE = re.compile(
    r'\b\d+(?:\.\d+)?\s*'
    r'(WDG|WG|WP|SG|SP|DF|DG|XP|SC|SE|SL|ME|CS|EC|EG|RFC|FS|FL|FC|LC|L|F|G)\b',
    re.I)
# map shorthand letters to a real formulation code
LETTER_CODE = {'L': 'L', 'F': 'F', 'FS': 'SC', 'FL': 'F', 'FC': 'SC',
               'LC': 'SC', 'EG': 'WG', 'RFC': 'SC', 'G': 'G'}

def code_from_name(name):
    m = NUM_CODE_RE.search(name)
    if m:
        c = m.group(1).upper()
        return LETTER_CODE.get(c, c)
    m = NAME_CODE_RE.search(name)
    if m:
        return m.group(1).upper()
    return None

# --- active-ingredient normalisation for matching ----------------------------
SALT_WORDS = re.compile(
    r'\b(ester|amine|acid|salt|dma|dga|tea|ipa|choline|sodium|potassium|'
    r'dimethylamine|diglycolamine|isopropylamine|technical|group|\d+)\b', re.I)

def norm_one(tok):
    tok = SALT_WORDS.sub(' ', tok.lower())
    tok = re.sub(r'\([^)]*\)', ' ', tok)
    return re.sub(r'[^a-z0-9]', '', tok)

def ai_set(ai):
    """Normalised set of all active ingredients in an AI string."""
    parts = re.split(r'[+&,/]| and ', (ai or '').lower())
    return frozenset(p for p in (norm_one(t) for t in parts) if p)

def primary_ai(ai):
    s = ai_set(ai)
    return next(iter(s)) if len(s) == 1 else None

# --- products to exclude by exact name --------------------------------------
# Seed treatments, granular/dust soil products, planter-box dusts, tank
# cleaners and foam markers are NOT added to the spray tank, so they don't
# belong in the mixing-order tool. Standalone adjuvants are added through
# build_data.py's EDAK_ADJUVANTS (proper adjuvant schema) instead.
DROP_NAMES = {
    # seed treatments
    'Afla-Guard GR', 'Allegiance FL', 'Apron Maxx RTA', 'Apron XL',
    'CruiserMaxx APX', 'CruiserMaxx Potato', 'CruiserMaxx Potato Extreme',
    'CruiserMaxx Vibrance', 'CruiserMaxx Vibrance Cereals',
    'CruiserMaxx Vibrance Potato', 'Emesto Silver', 'First Defense Cereals ZX',
    'First Defense SBR', 'ILeVO', 'Maxim MZ Nubark', 'Raxil Pro MD',
    'Raxil Pro Shield', 'Saltro', 'Seed Shield Max Cereals',
    'Seed Shield Select', 'Stamina F4 Cereals', 'Vibrance', 'Vibrance Extreme',
    'Vibrance Trio', 'Teraxxa', 'Teraxxa F4', 'Heads Up', 'Heads Up RTA',
    'Velum Rise',
    # granular / dust soil products
    'Ridomil Gold GR', 'Dusta-Cide 6',
    # not part of the spray sequence
    'Align (Foam Marker)', 'Foambuster Max', 'Valent Tank Cleaner',
    'Wipe-Out XS Tank Cleaner', 'Verified VaporGrip Xtra Agent',
    # duplicate of Helena 'PointBlank WM'
    'Point Blank WM',
    # inoculants (peat / granular), not tank-mixed
    'Exceed 500XR', 'Exceed Granulated Peat',
    # handled as adjuvants in build_data.py (EDAK_ADJUVANTS)
    'Accuquest WM', 'Ad-Spray 80', 'Ad-Spray 90 NIS', 'Blendex VHC', 'Cohere',
    'Crop Oil Concentrate', 'Kinetic', 'Liquid Chisel', 'Optima',
    'Premium MSO', 'Re-Duce', 'Transactive HC', 'Trico Pro',
}

# light cleanup of the active-ingredient text for display
AI_FIX = [
    (r'\b24D\b', '2,4-D'), (r'sufentrazone', 'sulfentrazone'),
    (r'mesotrion\b', 'mesotrione'), (r'Metalxyl', 'metalaxyl'),
    (r'\bMetalaxyl\b', 'metalaxyl'),
]

def clean_ai(ai):
    ai = (ai or '').strip()
    for pat, repl in AI_FIX:
        ai = re.sub(pat, repl, ai)
    ai = re.sub(r'\s*\+\s*', ' + ', ai)
    ai = re.sub(r'\s{2,}', ' ', ai)
    return ai.strip()

# Hand-authored active-ingredient corrections that override the EDak source
# (the EDak xlsx ai column sometimes lists only the lead active for premixes).
# Keyed by exact EDak product name.
AI_OVERRIDES = {
    'Sinister Intent': 'fomesafen + s-metolachlor',
}

# --- manual overrides for products with no name-code and no AI-match ---------
# Real ag products keyed by exact EDak name -> best-effort formulation code,
# from product knowledge. All flagged review=True on output so the user gets a
# complete list of everything hand-assigned.
OVERRIDES = {
    # fungicides
    'Absolute Maxx': 'SC', 'Adastrio': 'SC', 'Aproach': 'SC',
    'Aproach Prima': 'SC', 'Cabrio EG': 'WG', 'Caramba': 'EC',
    'Delaro Complete': 'SC', 'Enable': 'F', 'Endura': 'WG', 'Endura Pro': 'WG',
    'Fontelis': 'SC', 'Forcivo': 'SC', 'Forum': 'SC', 'Headline AMP': 'SC',
    'Inspire Super': 'EC', 'Inspire XT': 'EC', 'Lucento': 'SC',
    'Luna Experience': 'SC', 'Luna Sensation': 'SC', 'Luna Tranquility': 'SC',
    'Merivon': 'SC', 'Miravis Ace': 'SE', 'Miravis Neo': 'SE',
    'Miravis Prime': 'SC', 'Miravis Top': 'SC', 'Nexicor': 'EC', 'Nuviga': 'SC',
    'Preside Ultra Soybean': 'SC', 'Presidio': 'SC', 'Priaxor Xemium': 'SC',
    'Pristine': 'WG', 'Propulse': 'SC', 'Prosaro Pro': 'SC', 'Quintec': 'SC',
    'Revus': 'SC', 'Revus Top': 'SC', 'Sphaerex': 'EC', 'Stratego YLD': 'EC',
    'Topguard Fungicide (Row Crops)': 'SC', 'Torino': 'SC', 'Veltyma': 'SC',
    'Vivando': 'SC', 'Zampro': 'SC', 'Zorina': 'SC', 'Excalia': 'SC',
    'Revytek': 'SC',
    # herbicides
    'Acuron GT': 'SE', 'Antares Herbicide': 'SC', 'Assure II': 'EC',
    'Axial XL': 'EC', 'Balance Flexx': 'SC', 'Beyond Xtra': 'SL',
    'Callisto Xtra (Enhanced)': 'SC', 'Classic': 'DF', 'Freelexx': 'SL',
    'Nurizma': 'SC', 'Obvius': 'WDG', 'Obvius Plus': 'WDG', 'Prefar 4E': 'EC',
    'Raptor': 'SL', 'Surmount': 'EC', 'Tordon RTU': 'SL', 'Trimec 992': 'SL',
    'Trivence': 'WDG', 'Unison (ultra low vol 2,4-D)': 'EC', 'Velum Prime': 'SC',
    'Ridgeback': 'SC', 'Renestra': 'SC', 'Opello': 'SC',
    # insecticides
    'Actara': 'WG', 'Admire Pro': 'SC', 'Altacor': 'WDG', 'Asana XL': 'EC',
    'Avaunt': 'WDG', 'Baythroid XL': 'EC', 'Belay Insecticide': 'SC',
    'Beleaf 50': 'SG', 'Besiege': 'ZC', 'Bifender FC': 'SC', 'Blackhawk': 'WG',
    'Brigade EVO': 'WDG', 'Brigade WSB': 'WP', 'Capture LFR': 'SC',
    'Capture 3RIVE 3D': 'SC', 'Carbine': 'WG', 'Dibrom 8E': 'EC',
    'Dimethoate 4E Insecticide': 'EC', 'Elatus': 'WG',
    'Elevest Insect Control': 'SC', 'Endigo ZCX': 'ZC', 'Ethos 3D': 'SC',
    'Ethos XB': 'SC', 'Ethos Elite': 'SC', 'Force EVO': 'EC', 'Hero': 'EC',
    'Index': 'EC', 'Leverage 360': 'SC', 'Midac 4': 'SC', 'Minecto Pro': 'SC',
    'Movento': 'SC', 'Movento HL': 'SC', 'Mustang Maxx': 'EC',
    'Pounce 25WP': 'WP', 'Ruckus LFR': 'SC', 'Sefina Inscalis': 'SC',
    'Sivanto Prime': 'SL', 'SmartChoice HC SB': 'SC', 'Sultrus': 'EC',
    'Tempest': 'EC', 'Vantacor': 'SC', 'Warrior II W/Zeon Tech': 'CS',
    'Xentari': 'DF',
    # plant growth regulators
    'Apogee': 'WDG', 'Kickstand PGR': 'SL', 'MaxCel': 'SL',
    'Palisade Maxx': 'EC', 'PoMaxa PGR': 'SL', 'Receptor': 'SL', 'Retain': 'SP',
    # multi-active herbicide/fungicide premixes (no single-active match)
    'Aatrex Nine-0': 'WDG', 'Accent Q': 'WDG', 'Acuron': 'SE',
    'Acuron Flexi': 'SE', 'Affinity BroadSpec': 'SG', 'Affinity Tank Mix': 'SG',
    'Afforia': 'WDG', 'Anthem Flex': 'EC', 'Anthem Maxx': 'SE', 'Armezon': 'SC',
    'Armezon Pro': 'EC', 'Authority Assist': 'SC', 'Authority Edge': 'SC',
    'Authority Supreme': 'SC', 'Authority XL': 'WDG', 'Axial Bold': 'EC',
    'Axial Star': 'EC', 'Azterknot': 'SC', 'AZteroid FC 3.3': 'SC',
    'Basis Blend': 'SG', 'Bicep II Magnum': 'SC', 'Bicep II Magnum FC': 'SC',
    'Bicep Lite II Magnum': 'SC', 'Coragen': 'SC', 'Enlite': 'WDG',
    'Enversa': 'ME', 'Envive': 'WDG', 'Fierce XLT': 'WDG',
    'Finesse Cereal & Fallow': 'DF', 'Harness  MAX': 'SC', 'Lexar EZ': 'SE',
    'Milestone': 'SL', 'Panoflex w/TotalSol': 'SG', 'PastureGard HL': 'EC',
    'Pramitol 5PS': 'PS', 'Quadris Flowable': 'SC', 'Quadris Opti': 'SC',
    'Rave': 'WDG', 'Resicore REV': 'SE', 'Roundup QuikPro': 'SG',
    'Sentris': 'SC', 'Sinister Intent': 'DC', 'Steadfast Q': 'WDG',
    'Stryax': 'SE', 'Tavium': 'SE', 'TeamMate': 'WDG', 'Topguard EQ': 'SC',
    'Trivapro': 'SE', 'TrumpCard': 'DC', 'Valor XLT': 'WDG', 'Wide Match': 'EC',
    'Wolverine Advanced': 'EC',
}

def main():
    raw = json.load(open('edak_xlsx.json', encoding='utf-8'))
    kept = [r for r in raw if keep_class(r['class'])]

    # Read existing products from data.js, but IGNORE source=='EDak' entries so
    # this script stays idempotent (data.js already contains a prior EDak run).
    js = open('data.js', encoding='utf-8').read()
    existing_names = set()
    # build two AI -> code maps from existing products that have a code:
    #   set2code   : exact full active-ingredient set -> code (reliable generic match)
    #   single2code: single active -> code, only from existing single-active products
    set2code, single2code = {}, {}
    for obj in re.findall(r'\{[^{}]*\}', js):
        try:
            o = json.loads(obj)
        except Exception:
            continue
        if o.get('source') == 'EDak':
            continue
        if o.get('name'):
            existing_names.add(o['name'].lower())
        if not (o.get('code') and o.get('ai')):
            continue
        s = ai_set(o['ai'])
        if s:
            set2code.setdefault(s, o['code'])
        if len(s) == 1:
            single2code.setdefault(next(iter(s)), o['code'])

    new = [r for r in kept
           if r['name'].lower() not in existing_names
           and r['name'] not in DROP_NAMES]

    out, unresolved, review_list = [], [], []
    n_name = n_set = n_single = n_over = 0
    for r in new:
        name, ai, cls = r['name'], clean_ai(r['ai']), r['class']
        if name in AI_OVERRIDES:
            ai = AI_OVERRIDES[name]
        s = ai_set(r['ai'])
        review = False
        code = code_from_name(name)
        # Resolution priority: name-embedded code -> hand-authored override ->
        # exact active-ingredient-set match -> single-active fallback. The
        # hand-authored override comes BEFORE active-ingredient inference
        # because a single-active heuristic can wrongly assign a code that's
        # right for one product but wrong for another (e.g. Atrazine 4F is
        # flowable F, but Aatrex Nine-0 is a Water Dispersible Granule).
        if code:
            n_name += 1
        elif name in OVERRIDES:
            code, review = OVERRIDES[name], True
            n_over += 1
            review_list.append((cls, name, code, ai))
        elif s in set2code:                       # exact same-actives generic match
            code = set2code[s]
            n_set += 1
        elif len(s) == 1 and next(iter(s)) in single2code:
            code, review = single2code[next(iter(s))], True
            n_single += 1
            review_list.append((cls, name, code, ai))
        else:
            unresolved.append(r)
            continue
        out.append({'name': name, 'code': code, 'ai': ai,
                    'class': cls, 'review': review})

    out.sort(key=lambda p: p['name'].lower())
    json.dump(out, open('edak_products.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'kept tank-mixable: {len(kept)}  new (after drops): {len(new)}')
    print(f'  by name-code: {n_name}   exact-AI: {n_set}   '
          f'single-AI(review): {n_single}   override(review): {n_over}')
    print(f'  RESOLVED -> edak_products.json: {len(out)}')
    print(f'  UNRESOLVED (need OVERRIDES or DROP): {len(unresolved)}')
    for r in unresolved:
        print(f"    {r['class']:<22} | {r['name']:<32} | {r['ai']}")
    # write the human review list of best-effort (override) formulations
    review_list.sort()
    with open('edak_review.txt', 'w', encoding='utf-8') as f:
        f.write('EDak products with BEST-EFFORT (hand-assigned) formulation codes.\n')
        f.write('Verify each against the product label.\n\n')
        f.write(f'{"class":<14}  {"product":<34}  code  active ingredient\n')
        f.write('-' * 90 + '\n')
        for cls, name, code, ai in review_list:
            f.write(f'{cls:<14}  {name:<34}  {code:<4}  {ai}\n')
    # spreadsheet version for round-trip review
    with open('edak_review.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['class', 'product', 'active ingredient',
                    'assigned code', 'mixing group', 'group label',
                    'corrected code (fill if wrong)', 'notes'])
        for cls, name, code, ai in review_list:
            grp, glabel = GROUP.get(code, ('', ''))
            w.writerow([cls, name, ai, code, grp, glabel, '', ''])
    print(f'  review list ({len(review_list)}) -> edak_review.txt, edak_review.csv')


if __name__ == '__main__':
    main()
