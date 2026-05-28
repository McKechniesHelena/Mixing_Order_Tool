import re, json

RAW = open('compendium_raw.txt', encoding='utf-8').read()

COMPANIES = [
    'Tenkoz','Syngenta','Loveland','Albaugh','BASF','Bayer','Corteva','NuFarm','Nufarm',
    'Winfield','FMC','Valent','UPL','Gowan','AMVAC','ADAMA','Helena','Drexel','Helm Agro',
    'Helm','TKI','Aceto','Willowood','Belchim','PBI','Innvictis','Several','Gangster',
]
COMPANY_RE = re.compile(r'\b(' + '|'.join(sorted(COMPANIES, key=len, reverse=True)) + r')\b')

# Companies whose products should be left out of the tool.
EXCLUDE_COMPANIES = {'Tenkoz'}

# Formulation code -> (group number, group label)
# Groups follow A.P.P.L.E.S. (NDSU ND Weed Guide p.86)
CODE_GROUP = {
    # 1 = soluble powders
    'SG': 1, 'SP': 1,
    # 2 = dry powders
    'DF': 2, 'WDG': 2, 'WG': 2, 'WP': 2, 'XP': 2, 'DG': 2,
    # 3 = liquid flowables / suspensions
    'ASC': 3, 'ACS': 3, 'SC': 3, 'SE': 3, 'ME': 3, 'F': 3, 'L': 3, 'ZC': 3, 'CS': 3, 'AS': 3,
    # 4 = emulsifiable concentrates
    'EC': 4, 'EW': 4, 'OD': 4, 'AE': 4,
    # 5 = solutions
    'SL': 5, 'S': 5,
    # 0 = granular / not tank-mixed
    'G': 0, 'PS': 0,
}
GROUP_LABEL = {
    1: 'Soluble powders (SG, SP, dry fertilizer)',
    2: 'Dry powders (DF, WDG, WP)',
    3: 'Liquid flowables / suspensions (SC, SE, ME, F, L, CS, ZC)',
    4: 'Emulsifiable concentrates (EC, EW, OD)',
    5: 'Solutions (S, SL)',
    0: 'Dry granular / pelleted (not tank-mixed)',
}

# code tokens, longest first so ACS/WDG match before AS/WG/S etc.
ALL_CODES = sorted(CODE_GROUP.keys(), key=len, reverse=True)
CODE_RE = re.compile(r'([0-9][0-9.]*)\s*(' + '|'.join(ALL_CODES) + r')(?![a-zA-Z])')

SKIP_SUBSTR = ['Product', 'Brand', 'Equiv', 'Active ingredients', 'Low Med High', 'Site of action']

# Herbicide site-of-action group numbers used as superscripts in the guide
VALID_SOA = {1,2,3,4,5,6,9,10,14,15,16,19,22,27,29}

def strip_soa(name):
    """Remove the trailing site-of-action superscript(s) the PDF glued onto the name,
    while preserving legitimate trailing numbers in the product name (e.g. 'RT 3')."""
    m = re.search(r'[\d,]+$', name)
    if not m:
        return name.strip()
    run = m.group()
    toks = run.split(',')
    # tokens after the first comma are pure SOA numbers (must be valid)
    if any((not t.isdigit()) or (int(t) not in VALID_SOA) for t in toks[1:]):
        return name.strip()  # doesn't look like an SOA run; leave as-is
    first = toks[0]
    # the first token is name-digits glued to the first SOA number; find the
    # longest no-leading-zero suffix of `first` that is a valid SOA number
    keep_len = len(first)
    for i in range(len(first)):
        suf = first[i:]
        if suf[0] == '0':
            continue
        if int(suf) in VALID_SOA:
            keep_len = i
            break
    name_digits = first[:keep_len]
    base = name[:m.start()] + name_digits
    return base.strip()

def find_codes(text):
    """Return list of (code, end_index) for qualifying formulation tokens."""
    out = []
    for m in CODE_RE.finditer(text):
        code = m.group(2)
        if code in CODE_GROUP:
            out.append((code, m.start(), m.end()))
    return out

products = []
for line in RAW.splitlines():
    s = line.strip()
    if not s:
        continue
    if any(k in s for k in SKIP_SUBSTR):
        continue
    if re.fullmatch(r'\d{2,3}', s):  # page number
        continue
    cmatch = COMPANY_RE.search(s)
    if not cmatch:
        continue
    if cmatch.group(1) in EXCLUDE_COMPANIES:
        continue
    name = s[:cmatch.start()].strip()
    name = strip_soa(name)
    name = re.sub(r'^RU\b', 'Roundup', name)  # guide abbreviates Roundup as "RU"
    if not name:
        continue
    post = s[cmatch.end():]
    codes = find_codes(post)
    if not codes:
        info = re.sub(r'[\d.\s+&,()-]+$', '', post.lstrip(' -')).strip()
        products.append({'name': name, 'code': None, 'group': None,
                         'groupLabel': 'Unknown — check product label', 'ai': info})
        continue
    info = post[:codes[0][1]].lstrip(' -')
    info = re.sub(r'[\d.\s+&,()-]+$', '', info).strip()
    code = codes[-1][0]  # trailing code = product's overall formulation
    grp = CODE_GROUP[code]
    products.append({'name': name, 'code': code, 'group': grp,
                     'groupLabel': GROUP_LABEL[grp], 'ai': info})

# de-dupe by name keeping first
seen = set(); dedup = []
for p in products:
    if p['name'] in seen:
        continue
    seen.add(p['name']); dedup.append(p)

dedup.sort(key=lambda p: p['name'].lower())
print('total parsed:', len(products), 'unique:', len(dedup))
print('no-code:', sum(1 for p in dedup if p['code'] is None))
from collections import Counter
print('by group:', Counter(p['group'] for p in dedup))
print('codes:', Counter(p['code'] for p in dedup))
json.dump(dedup, open('products.json','w',encoding='utf-8'), indent=1, ensure_ascii=False)
# data.js is written by build_data.py (which merges in the Helena guide).
print('wrote products.json — now run: py build_data.py')
print('dicamba products:', sum(1 for p in dedup if 'dicamba' in (p.get('ai') or '').lower()))
