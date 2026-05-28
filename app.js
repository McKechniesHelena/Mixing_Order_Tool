'use strict';

/* ---- A.P.P.L.E.S. mixing groups (ND Weed Control Guide W-253, p.86) ---- */
const GROUP_NAMES = {
  1: 'Soluble powders',
  2: 'Dry powders',
  3: 'Liquid flowables / suspensions',
  4: 'Emulsifiable concentrates',
  5: 'Solutions',
};
const GROUP_CODES = {
  1: 'SG, SP, dry fertilizer',
  2: 'DF, WDG, WP',
  3: 'SC, SE, ME, F, L, CS, ZC, DC',
  4: 'EC, EW, OD',
  5: 'S, SL',
};

/* ---- Adjuvants: placed in the same sequence as pesticides (guide p.86) ----
   AMS = soluble powder (1); oil adjuvants = EC (4); surfactants = solutions (5).
   Within a group, pesticides are added before adjuvants. */
const ADJUVANTS = [
  { name: 'AMS (ammonium sulfate, spray grade)', code: 'AMS', group: 1, adjuvant: true,
    note: 'Do NOT use AMS with any dicamba formulation — it increases dicamba volatility.' },
  { name: 'Liquid AMS / water conditioner', code: 'AMS-L', group: 1, adjuvant: true,
    note: 'Water-conditioning agent; follow the label — many are added to the water first.' },
  { name: 'Crop oil concentrate (COC)', code: 'COC', group: 4, adjuvant: true },
  { name: 'Methylated seed oil (MSO)', code: 'MSO', group: 4, adjuvant: true },
  { name: 'Nonionic surfactant (NIS)', code: 'NIS', group: 5, adjuvant: true },
  { name: 'Drift reduction agent (DRA)', code: 'DRA', group: 5, adjuvant: true,
    note: 'Add last, just before topping off the tank.' },
  { name: 'Defoaming agent', code: 'AF', group: 5, adjuvant: true,
    note: 'Add last, as needed.' },
];

/* Formulation code -> A.P.P.L.E.S. group, for custom products */
const CODE_GROUP = {
  SG: 1, SP: 1,
  DF: 2, WDG: 2, WG: 2, WP: 2,
  SC: 3, SE: 3, ME: 3, F: 3, L: 3, CS: 3, ZC: 3, DC: 3,
  EC: 4, EW: 4, OD: 4,
  S: 5, SL: 5,
};

const isDicamba = (ai) => /dicamba|\bdic[-.]/i.test(ai || '');

/* ---- Mixing-order schemes ----
   A scheme maps each item to a numbered phase and supplies the phase labels.
   `phaseOf` returns null for items that aren't tank-mixed (granular / unknown). */
const INDUSTRY_LABELS = {
  0: { name: 'Water conditioners / AMS', codes: 'add to the water first' },
  2: { name: 'Dry products', codes: 'SG, SP, DF, WDG, WP' },
  3: { name: 'Suspensions / flowables', codes: 'SC, SE, ME, F, L, CS, ZC, DC' },
  4: { name: 'Soluble liquids / solutions', codes: 'S, SL' },
  5: { name: 'Emulsifiable concentrates', codes: 'EC, EW, OD' },
  6: { name: 'Oils', codes: 'COC, MSO' },
  7: { name: 'Surfactants', codes: 'NIS' },
  8: { name: 'Drift / defoaming agents', codes: 'add last' },
};

const HELENA_LABELS = {
  2: { name: 'Water conditioners / AMS / foam control', codes: 'add early (guide steps 2–3)' },
  4: { name: 'Dry water-soluble products', codes: 'SG, SP — allow 10–15 min' },
  5: { name: 'Water-dispersible granules / dry flowables', codes: 'WDG, DF, WP — allow 10–15 min' },
  6: { name: 'Suspensions / liquid flowables', codes: 'SC, SE, ME, F, L, CS, ZC' },
  7: { name: 'Dispersible & emulsifiable concentrates', codes: 'DC, EC, EW, OD' },
  8: { name: 'Soluble liquids', codes: 'S, SL' },
  11: { name: 'Drift reduction agents', codes: 'polymer-based here; add starch/guar types FIRST' },
  12: { name: 'Surfactants / remaining adjuvants', codes: 'NIS' },
  13: { name: 'Oil-based adjuvants', codes: 'COC, MSO — add last' },
};

const SCHEMES = {
  helena: {
    title: 'Helena NBU 2026 Product Guide mixing order (p.95)',
    startFill: 'Fill the tank 1/3–1/2 full with clean water and start agitation. Keep agitating throughout.',
    nearFullBefore: 11,   // fill nearly full before adding DRAs / final adjuvants (guide step 9)
    endText: 'Keep agitating and spray promptly.',
    phaseOf: (item) => {
      if (item.adjuvant) {
        if (item.group === 1) return 2;                 // water conditioners / AMS
        if (item.group === 4) return 13;                // oil-based adjuvants last
        if (item.group === 5) {
          if (/AF/i.test(item.code || '')) return 2;    // foam control
          if (/DRA/i.test(item.code || '') || /\blast\b/i.test(item.note || '')) return 11;
          return 12;                                    // surfactants (NIS)
        }
        return null;
      }
      if ((item.code || '').toUpperCase() === 'DC') return 7;  // DC sits with the ECs
      switch (item.group) {
        case 1: return 4;   // dry water-soluble
        case 2: return 5;   // WDG / DF / WP
        case 3: return 6;   // suspensions / flowables
        case 4: return 7;   // emulsifiable concentrates
        case 5: return 8;   // soluble liquids
        default: return null;
      }
    },
    secondary: () => 0,
    label: (ph) => HELENA_LABELS[ph],
  },
  apples: {
    title: 'A.P.P.L.E.S. method (ND Weed Control Guide W-253, p.86)',
    phaseOf: (item) => (item.group >= 1 && item.group <= 5 ? item.group : null),
    secondary: (item) => (item.adjuvant ? 1 : 0),   // pesticide before adjuvant
    label: (ph) => ({ name: GROUP_NAMES[ph], codes: GROUP_CODES[ph] }),
  },
  industry: {
    title: 'Solutions-before-EC order (label / industry sequence)',
    phaseOf: (item) => {
      if (item.adjuvant) {
        if (item.group === 1) return 0;                 // AMS / water conditioners first
        if (item.group === 4) return 6;                 // oils (COC/MSO)
        if (item.group === 5) {
          return (/DRA|AF/i.test(item.code || '') || /\blast\b/i.test(item.note || '')) ? 8 : 7;
        }
        return null;
      }
      switch (item.group) {
        case 1: case 2: return 2;   // dry products
        case 3: return 3;           // suspensions / flowables
        case 5: return 4;           // soluble liquids / solutions
        case 4: return 5;           // emulsifiable concentrates
        default: return null;       // granular / unknown
      }
    },
    secondary: () => 0,
    label: (ph) => INDUSTRY_LABELS[ph],
  },
};

const SCHEME_KEY = 'mixSchemeV2';
let currentScheme = SCHEMES[localStorage.getItem(SCHEME_KEY)] ? localStorage.getItem(SCHEME_KEY) : 'helena';

/* ---- State ---- */
const selected = [];   // array of item objects
const products = (window.PRODUCTS || []).slice();

/* ---- DOM ---- */
const $ = (id) => document.getElementById(id);
const searchInput = $('search');
const suggestions = $('suggestions');
const chips = $('chips');
const adjBar = $('adjuvants');
const output = $('output');
const copyBtn = $('copyBtn');
const simpleCopyBtn = $('simpleCopyBtn');
const clearBtn = $('clearBtn');
const customToggle = $('customToggle');
const customForm = $('customForm');
const customName = $('customName');
const customCode = $('customCode');

/* ---- Build adjuvant quick-add buttons ---- */
ADJUVANTS.forEach((a) => {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'adj-btn';
  b.textContent = '+ ' + a.code;
  b.title = a.name;
  b.onclick = () => addItem(a);
  adjBar.appendChild(b);
});

/* Commonly-used Helena adjuvants — pulled from the product data so they carry
   the correct group, code and notes. */
const HELENA_QUICK = ['Zaar', 'Dyne-Amic', 'Cohort', 'Smoke', 'Hel-Fire', 'Fire-Zone'];
const helenaBar = $('helenaAdjuvants');
HELENA_QUICK.forEach((name) => {
  const prod = products.find((p) => p.name.toLowerCase() === name.toLowerCase());
  if (!prod) return;
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'adj-btn';
  b.textContent = '+ ' + prod.name;
  b.title = prod.ai || prod.name;
  b.onclick = () => addItem(prod);
  helenaBar.appendChild(b);
});

/* ---- Selection ---- */
function keyOf(item) { return (item.adjuvant ? 'adj:' : 'prod:') + item.name; }

function addItem(item) {
  if (selected.some((s) => keyOf(s) === keyOf(item))) return;
  selected.push(item);
  searchInput.value = '';
  suggestions.innerHTML = '';
  render();
}

function removeItem(item) {
  const i = selected.findIndex((s) => keyOf(s) === keyOf(item));
  if (i >= 0) selected.splice(i, 1);
  render();
}

/* ---- Search / autocomplete ---- */
function search(q) {
  q = q.trim().toLowerCase();
  if (!q) return [];
  const starts = [], contains = [];
  for (const p of products) {
    const n = p.name.toLowerCase();
    const ai = (p.ai || '').toLowerCase();
    if (n.startsWith(q)) starts.push(p);
    else if (n.includes(q) || ai.includes(q)) contains.push(p);
    if (starts.length >= 30) break;
  }
  return starts.concat(contains).slice(0, 30);
}

searchInput.addEventListener('input', () => {
  const q = searchInput.value.trim();
  const results = search(searchInput.value);
  suggestions.innerHTML = '';
  results.forEach((p) => {
    const li = document.createElement('li');
    const grp = p.group == null ? '?' : p.code;
    li.innerHTML = `<span class="s-name">${esc(p.name)}</span>
      <span class="s-meta"><span class="s-ai">${esc(p.ai || '')}</span> <b>${esc(grp || '')}</b></span>`;
    li.onclick = () => addItem(p);
    suggestions.appendChild(li);
  });
  if (q && !results.length) {
    const li = document.createElement('li');
    li.className = 's-custom';
    li.innerHTML = `No matches — <b>add “${esc(q)}” as a custom product</b>`;
    li.onclick = () => openCustomForm(q);
    suggestions.appendChild(li);
  }
});

searchInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    const first = suggestions.querySelector('li');
    if (first) first.click();
  }
});

/* ---- Render ---- */
function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

function render() {
  renderChips();
  renderOrder();
  const empty = orderedItems().length === 0;
  copyBtn.hidden = empty;
  simpleCopyBtn.hidden = empty;
  clearBtn.hidden = selected.length === 0;
}

/* ---- Plain-text export ---- */
function orderToText() {
  const ordered = orderedItems();
  if (!ordered.length) return '';
  const sc = SCHEMES[currentScheme];
  const lines = [
    `TANK MIX ORDER — ${sc.title}`,
    '',
  ];
  let n = 1;
  lines.push(`${n++}. ${sc.startFill || 'Fill tank 1/2–3/4 full with clean water and start agitation (keep agitating throughout).'}`);
  let lastPhase = null, nearFullDone = false;
  ordered.forEach((item) => {
    const ph = sc.phaseOf(item);
    if (sc.nearFullBefore != null && !nearFullDone && ph >= sc.nearFullBefore) {
      lines.push('', `${n++}. Fill the tank nearly full with water, keep agitating.`);
      nearFullDone = true;
    }
    if (ph !== lastPhase) {
      const lab = sc.label(ph);
      lines.push('', `   — ${lab.name}${lab.codes ? ' (' + lab.codes + ')' : ''} —`);
      lastPhase = ph;
    }
    lines.push(`${n++}. ${item.name} [${item.code || '?'}${item.adjuvant ? ', adjuvant' : ''}]`);
    if (item.note) lines.push(`      note: ${item.note}`);
  });
  lines.push('', `${n++}. ${sc.endText || 'Top off with the remaining water, keep agitating, and spray promptly.'}`);

  const warns = computeWarnings();
  if (warns.length) {
    lines.push('', 'WARNINGS:');
    warns.forEach((w) => lines.push(`! ${w}`));
  }
  lines.push('', 'Reference only — always read and follow individual product labels.');
  return lines.join('\n');
}

/* Just the numbered add-order, products only — water first, no notes/warnings. */
function simpleToText() {
  const ordered = orderedItems();
  if (!ordered.length) return '';
  const lines = ['1. Water'];
  ordered.forEach((item, i) => lines.push(`${i + 2}. ${item.name}`));
  return lines.join('\n');
}

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch { /* blocked (e.g. embedded frame) — fall back below */ }
  }
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  const ok = document.execCommand('copy');
  ta.remove();
  if (!ok) throw new Error('copy command failed');
}

function wireCopy(btn, label, textFn) {
  btn.addEventListener('click', async () => {
    const text = textFn();
    if (!text) return;
    try {
      await copyText(text);
      btn.textContent = 'Copied ✓';
      btn.classList.add('done');
    } catch {
      btn.textContent = 'Copy failed';
    }
    setTimeout(() => {
      btn.textContent = label;
      btn.classList.remove('done');
    }, 1600);
  });
}
wireCopy(copyBtn, 'Copy order', orderToText);
wireCopy(simpleCopyBtn, 'Simple copy', simpleToText);

clearBtn.addEventListener('click', () => {
  selected.length = 0;
  render();
});

/* ---- Custom product ---- */
function openCustomForm(prefill) {
  customForm.hidden = false;
  customName.value = prefill || '';
  suggestions.innerHTML = '';
  customName.focus();
}

function closeCustomForm() {
  customForm.hidden = true;
  customName.value = '';
}

function addCustom() {
  const name = customName.value.trim();
  if (!name) { customName.focus(); return; }
  const code = customCode.value || null;
  const group = code ? CODE_GROUP[code] : null;
  addItem({
    name,
    code,
    group: group == null ? null : group,
    groupLabel: group ? GROUP_NAMES[group] : 'Unknown — check product label',
    ai: name,                 // so the dicamba check can still catch e.g. "Dicamba HD"
    adjuvant: false,
    custom: true,
  });
  closeCustomForm();
}

customToggle.addEventListener('click', () => {
  if (customForm.hidden) openCustomForm(searchInput.value.trim());
  else closeCustomForm();
});
$('customAdd').addEventListener('click', addCustom);
$('customCancel').addEventListener('click', closeCustomForm);
customName.addEventListener('keydown', (e) => { if (e.key === 'Enter') addCustom(); });

/* ---- Order scheme toggle ---- */
document.querySelectorAll('input[name="scheme"]').forEach((r) => {
  if (r.value === currentScheme) r.checked = true;
  r.addEventListener('change', () => {
    if (!r.checked) return;
    currentScheme = r.value;
    localStorage.setItem(SCHEME_KEY, currentScheme);
    renderOrder();
  });
});

function renderChips() {
  chips.innerHTML = '';
  if (!selected.length) {
    chips.innerHTML = '<p class="empty">No products selected yet.</p>';
    return;
  }
  selected.forEach((item) => {
    const c = document.createElement('span');
    c.className = 'chip' + (item.adjuvant ? ' chip-adj' : '');
    c.innerHTML = `${esc(item.name)} <small>${esc(item.code || '?')}</small>
      <button aria-label="remove">&times;</button>`;
    c.querySelector('button').onclick = () => removeItem(item);
    chips.appendChild(c);
  });
}

/* order items by the active scheme's phases (granular/unknown items drop out) */
function orderedItems() {
  const sc = SCHEMES[currentScheme];
  return selected
    .map((it, i) => ({ it, i, ph: sc.phaseOf(it) }))
    .filter((x) => x.ph != null)
    .sort((a, b) => (a.ph - b.ph) || (sc.secondary(a.it) - sc.secondary(b.it)) || (a.i - b.i))
    .map((x) => x.it);
}

/* plain-text warning strings (shared by the warning box and the copied text) */
function computeWarnings() {
  const w = [];
  const hasAMS = selected.some((s) => s.code === 'AMS' || s.code === 'AMS-L' || s.ammonium);
  const dicambaProds = selected.filter((s) => isDicamba(s.ai)).map((s) => s.name);
  if (hasAMS && dicambaProds.length) {
    w.push(`Do not use AMS with dicamba. Ammonium increases dicamba volatility and reduces `
      + `the effect of low-volatile formulations (guide p.86). `
      + `Dicamba product(s) selected: ${dicambaProds.join(', ')}.`);
  }
  const unknown = selected.filter((s) => s.group == null);
  if (unknown.length) {
    w.push(`Formulation not listed for: ${unknown.map((u) => u.name).join(', ')}. `
      + `Check the product label for its formulation and mixing sequence.`);
  }
  const granular = selected.filter((s) => s.group === 0);
  if (granular.length) {
    w.push(`Dry granular / soil-applied (not tank-mixed): ${granular.map((u) => u.name).join(', ')}. `
      + `These are typically applied dry, not in a spray tank.`);
  }
  return w;
}

function renderOrder() {
  output.innerHTML = '';
  if (!selected.length) return;

  const ordered = orderedItems();
  const frag = document.createDocumentFragment();

  const warns = computeWarnings();
  if (warns.length) {
    const w = document.createElement('div');
    w.className = 'warnings';
    w.innerHTML = warns.map((t) => `<p>⚠ ${esc(t)}</p>`).join('');
    frag.appendChild(w);
  }
  if (!ordered.length) { output.appendChild(frag); return; }

  // steps
  const ol = document.createElement('ol');
  ol.className = 'steps';

  const sc = SCHEMES[currentScheme];

  const first = document.createElement('li');
  first.className = 'step-water';
  first.innerHTML = sc.startFill
    ? esc(sc.startFill)
    : `Fill the tank <b>½–¾ full</b> with clean water and <b>start agitation</b>.
       Keep agitating the whole time.`;
  ol.appendChild(first);

  let lastPhase = null, phaseNum = 0, nearFullDone = false;
  ordered.forEach((item) => {
    const ph = sc.phaseOf(item);
    if (sc.nearFullBefore != null && !nearFullDone && ph >= sc.nearFullBefore) {
      const nf = document.createElement('li');
      nf.className = 'step-water';
      nf.innerHTML = `Fill the tank <b>nearly full</b> with water, keep agitating.`;
      ol.appendChild(nf);
      nearFullDone = true;
    }
    if (ph !== lastPhase) {
      phaseNum++;
      const lab = sc.label(ph);
      const head = document.createElement('li');
      head.className = 'group-head';
      head.innerHTML = `<span class="g-num">${phaseNum}</span>
        ${esc(lab.name)}
        <small>${esc(lab.codes || '')}</small>`;
      ol.appendChild(head);
      lastPhase = ph;
    }
    const li = document.createElement('li');
    li.className = 'step' + (item.adjuvant ? ' step-adj' : '');
    li.innerHTML = `<span class="nm">${esc(item.name)}</span>
      <span class="tag">${esc(item.code || '?')}${item.adjuvant ? ' · adjuvant' : ''}${item.custom ? ' · custom' : ''}</span>
      ${item.note ? `<span class="note">${esc(item.note)}</span>` : ''}
      <span class="hint">Mix until fully dispersed before adding the next.</span>`;
    ol.appendChild(li);
  });

  const last = document.createElement('li');
  last.className = 'step-water';
  last.innerHTML = sc.endText
    ? esc(sc.endText)
    : `Top off with the remaining water, keep agitating, and <b>spray promptly</b>.`;
  ol.appendChild(last);

  frag.appendChild(ol);

  const foot = document.createElement('p');
  foot.className = 'foot';
  foot.innerHTML = `If a product label specifies its own mixing sequence, <b>follow the label</b> —
    it overrides this guide. For unfamiliar combinations, do a <b>jar test</b> first.`;
  frag.appendChild(foot);

  output.appendChild(frag);
}

render();
