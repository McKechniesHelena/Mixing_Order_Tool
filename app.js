'use strict';

/* ---- A.P.P.L.E.S. mixing groups (ND Weed Control Guide W-253, p.86) ---- */
const GROUP_ORDER = [1, 2, 3, 4, 5];
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

const isDicamba = (ai) => /dicamba|\bdic[-.]/i.test(ai || '');

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
  const lines = [
    'TANK MIX ORDER — A.P.P.L.E.S. method (ND Weed Control Guide W-253, p.86)',
    '',
  ];
  let n = 1;
  lines.push(`${n++}. Fill tank 1/2–3/4 full with clean water and start agitation (keep agitating throughout).`);
  let lastGroup = null;
  ordered.forEach((item) => {
    if (item.group !== lastGroup) {
      lines.push('', `   — Group ${item.group}: ${GROUP_NAMES[item.group]} (${GROUP_CODES[item.group]}) —`);
      lastGroup = item.group;
    }
    lines.push(`${n++}. ${item.name} [${item.code || '?'}${item.adjuvant ? ', adjuvant' : ''}]`);
    if (item.note) lines.push(`      note: ${item.note}`);
  });
  lines.push('', `${n++}. Top off with the remaining water, keep agitating, and spray promptly.`);

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

/* order: by group, pesticides before adjuvants within each group */
function orderedItems() {
  const ordered = [];
  for (const g of GROUP_ORDER) {
    const inGroup = selected.filter((s) => s.group === g);
    inGroup.sort((a, b) => (a.adjuvant ? 1 : 0) - (b.adjuvant ? 1 : 0));
    ordered.push(...inGroup);
  }
  return ordered;
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

  const first = document.createElement('li');
  first.className = 'step-water';
  first.innerHTML = `Fill the tank <b>½–¾ full</b> with clean water and <b>start agitation</b>.
    Keep agitating the whole time.`;
  ol.appendChild(first);

  let lastGroup = null;
  ordered.forEach((item) => {
    if (item.group !== lastGroup) {
      const head = document.createElement('li');
      head.className = 'group-head';
      head.innerHTML = `<span class="g-num">${item.group}</span>
        ${esc(GROUP_NAMES[item.group])}
        <small>${esc(GROUP_CODES[item.group])}</small>`;
      ol.appendChild(head);
      lastGroup = item.group;
    }
    const li = document.createElement('li');
    li.className = 'step' + (item.adjuvant ? ' step-adj' : '');
    li.innerHTML = `<span class="nm">${esc(item.name)}</span>
      <span class="tag">${esc(item.code || '?')}${item.adjuvant ? ' · adjuvant' : ''}</span>
      ${item.note ? `<span class="note">${esc(item.note)}</span>` : ''}
      <span class="hint">Mix until fully dispersed before adding the next.</span>`;
    ol.appendChild(li);
  });

  const last = document.createElement('li');
  last.className = 'step-water';
  last.innerHTML = `Top off with the remaining water, keep agitating, and <b>spray promptly</b>.`;
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
