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
      <span class="s-meta">${esc(p.ai || '')} <b>${esc(grp || '')}</b></span>`;
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
}

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

function renderOrder() {
  output.innerHTML = '';
  if (!selected.length) return;

  const mixable = selected.filter((s) => s.group >= 1 && s.group <= 5);
  const granular = selected.filter((s) => s.group === 0);
  const unknown = selected.filter((s) => s.group == null);

  // order: by group, pesticides before adjuvants within each group
  const ordered = [];
  for (const g of GROUP_ORDER) {
    const inGroup = mixable.filter((s) => s.group === g);
    inGroup.sort((a, b) => (a.adjuvant ? 1 : 0) - (b.adjuvant ? 1 : 0));
    ordered.push(...inGroup);
  }

  const frag = document.createDocumentFragment();

  // warnings
  const warns = [];
  const hasAMS = selected.some((s) => s.code === 'AMS' || s.code === 'AMS-L' || s.ammonium);
  const dicambaProds = selected.filter((s) => isDicamba(s.ai)).map((s) => s.name);
  if (hasAMS && dicambaProds.length) {
    warns.push(`<strong>Do not use AMS with dicamba.</strong> Ammonium increases dicamba
      volatility and reduces the effect of low-volatile formulations (guide p.86).
      Dicamba product(s) selected: ${esc(dicambaProds.join(', '))}.`);
  }
  if (unknown.length) {
    warns.push(`Formulation not listed for: <strong>${esc(unknown.map((u) => u.name).join(', '))}</strong>.
      Check the product label for its formulation and mixing sequence.`);
  }
  if (granular.length) {
    warns.push(`Dry granular / soil-applied (not tank-mixed): <strong>${esc(granular.map((u) => u.name).join(', '))}</strong>.
      These are typically applied dry, not in a spray tank.`);
  }
  if (warns.length) {
    const w = document.createElement('div');
    w.className = 'warnings';
    w.innerHTML = warns.map((t) => `<p>⚠ ${t}</p>`).join('');
    frag.appendChild(w);
  }

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
