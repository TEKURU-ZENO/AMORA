/* AgentDate front end. One file, small modules keyed off what's on the page. No build step. */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const tint = id => 't' + ([...id].reduce((n, c) => n + c.charCodeAt(0), 0) % 7);  // same formula as the Jinja filter
const mono = (name, id, size = 'sm') => `<span class="mono ${size} ${tint(id)}" aria-hidden="true">${esc((name || '?')[0].toUpperCase())}</span>`;

/* Subscribe to a job's server-sent events. Strings are log lines, objects are structured events. */
function stream(job, {onMsg, onEvent, onDone}) {
  const es = new EventSource(`/api/jobs/${job}/stream`);
  es.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.msg) onMsg?.(m.msg);
    if (m.event) onEvent?.(m.event);
    if (m.done) { es.close(); onDone?.(m); }
  };
  es.onerror = () => { es.close(); onDone?.({error: 'Lost the connection to the server. Refresh to pick up where it left off.'}); };
  return es;
}

/* Turn raw failures into something a person can act on. */
function humanError(err) {
  const e = String(err || '');
  if (/private/i.test(e)) return 'This Instagram is private. Only public profiles can be read.';
  if (/APIFY_TOKEN|Scraping is off/i.test(e)) return 'Scraping is off on this server (no APIFY_TOKEN), so live links can\'t be read.';
  if (/Neither LinkedIn nor Instagram/i.test(e)) return 'Neither profile could be read. Check both links are public and spelled right.';
  if (/returned no data/i.test(e)) return 'The scraper found nothing at that link. Is the profile public and spelled right?';
  if (/at least two/i.test(e)) return 'A round needs at least two people in the pool.';
  return e || 'Something went wrong.';
}

/* Tooltip shared by the floor and the matrix. */
const tip = $('#tip');
function showTip(html, ev) {
  if (!tip) return;
  tip.innerHTML = html; tip.classList.add('on');
  const x = Math.min(ev.clientX + 14, innerWidth - tip.offsetWidth - 10), y = ev.clientY + 16;
  tip.style.left = x + 'px'; tip.style.top = (y + tip.offsetHeight > innerHeight ? ev.clientY - tip.offsetHeight - 10 : y) + 'px';
}
const hideTip = () => tip?.classList.remove('on');

/* Count a number up from 0 (600ms). */
function countUp(el, to, ms = 600) {
  if (calm) { el.textContent = to.toFixed(1); return; }
  const t0 = performance.now();
  const f = t => { const k = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - k, 3);
    el.textContent = (to * e).toFixed(1); if (k < 1) requestAnimationFrame(f); };
  requestAnimationFrame(f);
}

/* ================================================================ paste card: inline validation + submit */
function checkLink(kind, raw) {
  let v = raw.trim();
  if (!v) return {ok: null, msg: kind === 'linkedin' ? 'Your public LinkedIn profile' : 'A public Instagram profile, not a post'};
  if (!/^https?:\/\//i.test(v)) v = 'https://' + v;
  let u; try { u = new URL(v); } catch { return {ok: false, msg: 'That doesn\'t look like a link yet'}; }
  const host = u.hostname.toLowerCase().replace(/^www\./, ''), path = u.pathname;
  if (kind === 'linkedin') {
    if (!host.endsWith('linkedin.com')) return {ok: false, msg: host.includes('instagram') ? 'That\'s an Instagram link, it goes in the box below' : 'Paste a linkedin.com/in/… profile link'};
    if (/^\/(company|school)\//.test(path)) return {ok: false, msg: 'That\'s a company page, paste a personal profile (linkedin.com/in/…)'};
    if (/^\/(posts|feed|pulse)\//.test(path)) return {ok: false, msg: 'That\'s a post link, paste the profile URL'};
    const m = path.match(/^\/in\/([A-Za-z0-9\-_%]{3,100})\/?$/);
    return m ? {ok: true, msg: `✓ LinkedIn profile: ${decodeURIComponent(m[1])}`, url: v} : {ok: false, msg: 'Paste a personal profile link (linkedin.com/in/…)'};
  }
  if (!['instagram.com', 'instagr.am'].includes(host)) return {ok: false, msg: host.includes('linkedin') ? 'That\'s a LinkedIn link, it goes in the box above' : 'Paste an instagram.com/… profile link'};
  if (/^\/(p|reel|reels|tv)\//.test(path)) return {ok: false, msg: 'That\'s a post link, paste the profile URL'};
  if (/^\/stories\//.test(path)) return {ok: false, msg: 'That\'s a story link, paste the profile URL'};
  const m = path.match(/^\/([A-Za-z0-9._]{1,30})\/?$/);
  if (!m || ['explore', 'accounts', 'direct'].includes(m[1].toLowerCase())) return {ok: false, msg: 'Paste a profile link (instagram.com/username)'};
  return {ok: true, msg: `✓ Instagram @${m[1]}. It has to be public.`, url: v};
}

const paste = $('#paste');
if (paste) {
  const fields = $$('.field', paste);
  const validate = (f, strict) => {
    const inp = $('input', f), r = checkLink(f.dataset.kind, inp.value);
    f.classList.toggle('good', r.ok === true);
    f.classList.toggle('bad', r.ok === false || (strict && r.ok === null));
    $('.hint', f).textContent = strict && r.ok === null ? 'Needed: ' + r.msg.toLowerCase() : r.msg;
    return r;
  };
  fields.forEach(f => {
    const inp = $('input', f);
    inp.addEventListener('input', () => validate(f));
    inp.addEventListener('blur', () => { const r = validate(f); if (r.ok) inp.value = r.url; });
  });
  paste.addEventListener('submit', async e => {
    e.preventDefault();
    const status = $('#paste-status'), btn = $('button[type=submit]', paste);
    const results = fields.map(f => validate(f, true));
    status.className = 'saying err';
    if (!results.every(r => r.ok)) { status.textContent = 'Fix the highlighted link first.'; return; }
    fields.forEach((f, i) => $('input', f).value = results[i].url);
    if (!paste.consent.checked) { status.textContent = 'Tick the consent box: you must be this person or have their permission.'; return; }
    btn.disabled = true; status.className = 'saying';
    status.innerHTML = '<span class="dots"><i></i><i></i><i></i></span> Sending your agent out…';
    try {
      const r = await fetch('/api/people', {method: 'POST', body: new FormData(paste)});
      const j = await r.json();
      if (!r.ok) throw new Error(j.error);
      location.href = `/person/${j.person}`;  // the reading screen picks up the live job
    } catch (err) {
      status.className = 'saying err'; status.textContent = humanError(err.message); btn.disabled = false;
    }
  });
}

/* Copy-link buttons */
$$('[data-copy]').forEach(b => b.addEventListener('click', async () => {
  const url = new URL(b.dataset.copy, location.origin).href;
  try { await navigator.clipboard.writeText(url); b.textContent = 'Copied ✓'; } catch { b.textContent = url; }
}));

/* "Run a dating round" buttons anywhere: start (or join) the round, then watch it on the floor */
$$('[data-run-round]').forEach(b => b.addEventListener('click', async () => {
  b.disabled = true; const label = b.innerHTML; b.textContent = 'Starting the round…';
  try {
    const r = await fetch('/api/round', {method: 'POST'}); const j = await r.json();
    if (!r.ok) throw new Error(j.error);
    location.href = `/round?job=${j.job}`;
  } catch (err) { b.innerHTML = label; b.disabled = false; alert(humanError(err.message)); }
}));

/* ================================================================ date replay */
const replay = $('#replay');
if (replay) {
  const msgs = $$('.chat .msg'), typing = $('#typing'), playBtn = $('#play'), verdicts = $('#verdicts');
  const sw = $('#thoughts');
  let i = 0, playing = false, speed = 1, timer = null, finished = false;

  const setThoughts = on => {
    document.body.classList.toggle('thoughts', on); sw.setAttribute('aria-checked', on);
    try { localStorage.setItem('ad-thoughts', on ? '1' : ''); } catch {}
  };
  sw.addEventListener('click', () => setThoughts(sw.getAttribute('aria-checked') !== 'true'));
  const q = new URLSearchParams(location.search).get('thoughts');
  let saved = ''; try { saved = localStorage.getItem('ad-thoughts'); } catch {}
  setThoughts(q != null ? q === '1' : !!saved);

  const label = () => {
    playBtn.innerHTML = finished ? '↺ Replay' : playing ? '❚❚ Pause' : '▶ Play';
    playBtn.setAttribute('aria-label', finished ? 'Replay' : playing ? 'Pause' : 'Play');
  };
  const follow = el => { const r = el.getBoundingClientRect(); if (r.bottom > innerHeight - 40) el.scrollIntoView({block: 'end', behavior: calm ? 'auto' : 'smooth'}); };
  const reveal = () => {
    typing.classList.remove('on');
    const m = msgs[i++]; m.classList.add('show'); follow(m);
    if (i >= msgs.length) return finish();
    if (playing) wait();
  };
  const wait = () => {  // the typing indicator sits on the side of whoever speaks next
    typing.className = 'typing on ' + (msgs[i].classList.contains('b') ? 'b' : 'a');
    msgs[i].before(typing);
    timer = setTimeout(reveal, 900 / speed);
  };
  const finish = () => {
    clearTimeout(timer); typing.classList.remove('on');
    msgs.forEach(m => m.classList.add('show'));
    i = msgs.length; playing = false;
    if (!finished) {
      finished = true;
      verdicts.classList.add('in');
      setTimeout(() => $$('[data-count]', verdicts).forEach(el => countUp(el, parseFloat(el.dataset.count))), calm ? 0 : 450);
    }
    label();
  };
  const reset = () => {
    finished = false; i = 0; verdicts.classList.remove('in');
    msgs.forEach(m => m.classList.remove('show')); scrollTo({top: 0, behavior: calm ? 'auto' : 'smooth'});
  };
  const play = () => { if (finished) reset(); playing = true; label(); clearTimeout(timer); timer = setTimeout(i === 0 ? () => wait() : reveal, 400); };
  const pause = () => { playing = false; clearTimeout(timer); typing.classList.remove('on'); label(); };
  const next = () => { if (finished) return; clearTimeout(timer); reveal(); };

  playBtn.addEventListener('click', () => playing ? pause() : play());
  $('#skip').addEventListener('click', finish);
  $$('.speed button').forEach(b => b.addEventListener('click', () => {
    speed = parseFloat(b.dataset.speed);
    $$('.speed button').forEach(x => x.setAttribute('aria-pressed', x === b));
  }));
  addEventListener('keydown', e => {
    if (e.target.closest('input,textarea,select')) return;
    if (e.key === ' ' && !e.target.closest('button')) { e.preventDefault(); playing ? pause() : play(); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); next(); }
    else if (e.key.toLowerCase() === 't' && !e.metaKey && !e.ctrlKey) sw.click();
  });

  if (calm || !msgs.length) finish(); else play();
}

/* ================================================================ reading screen */
const reading = $('#reading');
if (reading) {
  const {job, pid} = reading.dataset;
  const status = $('#read-status'), steps = $$('.stepper li'), li = $('#src-li'), ig = $('#src-ig');
  const setStatus = (html, err) => { status.className = 'saying' + (err ? ' err' : ''); status.innerHTML = html; };
  const busy = t => `<span class="dots"><i></i><i></i><i></i></span> ${esc(t)}`;
  let current = -1;
  const activate = n => {
    steps.forEach((s, k) => { s.classList.toggle('done', k < n); s.classList.toggle('active', k === n); });
    current = n;
  };
  const queue = []; let running = false;  // notes stream in one at a time, so passes never overlap on screen
  const pump = async () => {
    if (running) return; running = true;
    while (queue.length) await queue.shift()();
    running = false;
  };
  const typeInto = async (el, text) => {
    if (calm) { el.textContent = text; return; }
    const words = text.split(/(\s+)/);
    for (let k = 0; k < words.length; k++) { el.textContent += words[k]; if (k % 2 === 0) await sleep(18); }
  };
  const block = (pane, html) => { const d = document.createElement('div'); d.className = 'block'; d.innerHTML = html; pane.append(d); requestAnimationFrame(() => d.classList.add('in')); return d; };

  const renderSource = async ev => {
    if (ev.which === 'linkedin') {
      li.innerHTML = '';
      if (ev.headline) block(li, `<h4>Headline</h4><div class="serif" style="font-size:19px">${esc(ev.headline)}</div>`);
      if (ev.location) block(li, `<div class="small muted">${esc(ev.location)}</div>`);
      await sleep(250);
      if (ev.about) block(li, `<h4>About</h4><div class="small">${esc(ev.about)}…</div>`);
      await sleep(250);
      if (ev.roles.length) block(li, `<h4>Experience</h4><ul class="list">${ev.roles.map(r => `<li>${esc(r)}</li>`).join('')}</ul>`);
      await sleep(250);
      if (ev.skills.length) block(li, `<h4>Skills</h4><div class="chips">${ev.skills.map(s => `<span class="chip n">${esc(s)}</span>`).join('')}</div>`);
    } else {
      ig.innerHTML = '';
      block(ig, `<h4>@${esc(ev.username)} · ${ev.n_posts} posts</h4><div class="small">${esc(ev.bio)}</div>`);
      const grid = block(ig, '<div class="posts"></div>').firstChild;
      for (const p of ev.posts) {
        const d = document.createElement('div'); d.className = 'post';
        d.textContent = (p.location ? '📍 ' + p.location + ' · ' : '') + (p.caption || p.tags.map(t => '#' + t).join(' '));
        grid.append(d); await sleep(calm ? 0 : 110); d.classList.add('in');
      }
    }
  };
  const passIndex = t => /^LinkedIn pass/i.test(t) ? 0 : /^Instagram pass/i.test(t) ? 1 : /^Cross-read/i.test(t) ? 2 : -1;

  stream(job, {
    onMsg: m => { if (/scraping LinkedIn/i.test(m)) setStatus(busy('Reading the LinkedIn profile…'));
      else if (/scraping Instagram/i.test(m)) setStatus(busy('Reading the Instagram grid…'));
      else if (/analyst agent/i.test(m)) setStatus(busy('The analyst is reading both sources…')); },
    onEvent: ev => queue.push(async () => {
      if (ev.type === 'scrape') {
        const pane = ev.which === 'linkedin' ? li : ig;
        pane.innerHTML = `<div class="waiting">${busy(ev.which === 'linkedin' ? 'Pulling headline, roles, skills…' : 'Pulling bio and recent posts…')}</div>`;
      } else if (ev.type === 'source') {
        if (ev.which === 'instagram') setStatus(busy(`Reading ${ev.n_posts} Instagram posts…`));
        await renderSource(ev);
      } else if (ev.type === 'source_failed') {
        (ev.which === 'linkedin' ? li : ig).innerHTML = `<div class="banner"><b>Couldn't read this source.</b> ${esc(humanError(ev.error))} The profile will be built from the other one.</div>`;
      } else if (ev.type === 'pass') {
        let n = passIndex(ev.text); if (n < 0) n = Math.max(current, 0);
        activate(n);
        setStatus(busy(['Pass 1: reading the LinkedIn self…', 'Pass 2: reading the Instagram self…', 'Pass 3: cross-reading the two…'][n]));
        const notes = $('.notes', steps[n]);
        if (notes.textContent) notes.textContent += '\n';
        await typeInto(notes, ev.text.replace(/^(LinkedIn pass|Instagram pass|Cross-read):?\s*/i, ''));
      }
    }) && pump(),
    onDone: m => queue.push(async () => {
      if (m.error) {
        steps.forEach(s => s.classList.remove('active'));
        setStatus(esc(humanError(m.error)) + ' <a href="/join">Try another link</a>', true);
        return;
      }
      activate(3);
      setStatus('✓ Profile written. Assembling it now…');
      await sleep(calm ? 0 : 900);
      location.href = `/person/${m.person || pid}?assemble=1`;
    }) && pump(),
  });
}

/* ================================================================ profile */
const profile = $('#profile');
if (profile) {
  // chips: clicking a claim opens the receipts drawer and highlights the snippet behind it
  $$('[data-claim]', profile).forEach(c => c.addEventListener('click', () => {
    const r = document.getElementById('rc-' + c.dataset.claim);
    if (!r) return;
    $('details.receipts').open = true;
    $$('.receipt.hl').forEach(x => x.classList.remove('hl'));
    r.classList.add('hl'); r.scrollIntoView({block: 'center', behavior: calm ? 'auto' : 'smooth'});
    setTimeout(() => r.classList.remove('hl'), 2600);
  }));
  // staggered assembly after a fresh read
  if (profile.classList.contains('assemble')) {
    $$('.chip, .needs li, ul.list li', profile).forEach((el, k) => el.style.setProperty('--i', k));
    history.replaceState(null, '', location.pathname);
  }
  const rm = $('.remove');
  rm && $('.start', rm).addEventListener('click', () => rm.classList.add('ask'));
  rm && $('.cancel', rm).addEventListener('click', () => rm.classList.remove('ask'));
}

/* ================================================================ dating floor */
const floor = $('#floor');
if (floor && $('#ring')) {
  const data = JSON.parse($('#floor-data').textContent);
  const roster = data.roster, byId = Object.fromEntries(roster.map(p => [p.id, p]));
  const svg = $('#ring svg'), arcsG = $('#arcs', svg), nodesG = $('#nodes', svg), wall = $('#wall');
  const C = 260, R = 196, N = roster.length;
  const pos = {};
  roster.forEach((p, k) => { const a = -Math.PI / 2 + 2 * Math.PI * k / N; pos[p.id] = [C + R * Math.cos(a), C + R * Math.sin(a), a]; });
  const NS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };

  // nodes
  roster.forEach(p => {
    const [x, y, a] = pos[p.id], g = el('g', {class: 'node', 'data-id': p.id, tabindex: 0});
    g.append(el('circle', {cx: x, cy: y, r: 16}));
    const t = el('text', {x, y}); t.textContent = p.first[0].toUpperCase(); g.append(t);
    const lx = C + (R + 34) * Math.cos(a), ly = C + (R + 34) * Math.sin(a);
    const lb = el('text', {x: lx, y: ly, class: 'lbl'}); lb.textContent = p.first; g.append(lb);
    nodesG.append(g);
    g.addEventListener('mouseenter', () => focusNode(p.id)); g.addEventListener('mouseleave', () => focusNode(null));
    g.addEventListener('click', () => location.href = `/person/${p.id}`);
  });
  const focusNode = id => $$('.arc', arcsG).forEach(a => {
    a.classList.toggle('dim', !!id && a.dataset.from !== id && a.dataset.to !== id);
    a.classList.toggle('hot', !!id && (a.dataset.from === id || a.dataset.to === id));
  });

  const asked = {};  // from -> Set(to)
  function drawArc(from, to, why, animate) {
    if (!pos[from] || !pos[to]) return;
    (asked[from] ||= new Set()).add(to);
    const [x1, y1] = pos[from], [x2, y2] = pos[to];
    const mx = (x1 + x2) / 2, my = (y1 + y2) / 2, cx = C + (mx - C) * .35, cy = C + (my - C) * .35;
    const mutual = asked[to]?.has(from);
    const path = el('path', {d: `M${x1},${y1} Q${cx},${cy} ${x2},${y2}`, class: 'arc' + (mutual ? ' mut' : ''), 'data-from': from, 'data-to': to});
    if (mutual) $$(`.arc[data-from="${to}"][data-to="${from}"]`, arcsG).forEach(a => a.classList.add('mut'));
    arcsG.append(path);
    if (animate && !calm) { path.style.setProperty('--len', path.getTotalLength()); path.classList.add('draw'); }
    path.addEventListener('mousemove', e => showTip(`<b>${esc(byId[from].first)}'s agent</b> asked out <b>${esc(byId[to].first)}</b>${mutual ? ' (mutual)' : ''}<br>${esc(why)}`, e));
    path.addEventListener('mouseleave', hideTip);
  }

  // phases + counters
  const ph = {screening: $('[data-ph=screening]'), dating: $('[data-ph=dating]'), verdicts: $('[data-ph=verdicts]'), rankings: $('[data-ph=rankings]')};
  const order = ['screening', 'dating', 'verdicts', 'rankings'];
  const count = {asks: 0, done: 0, total: 0, mutual: 0};
  const setPhase = name => { const k = order.indexOf(name);
    order.forEach((o, j) => { ph[o].classList.toggle('done', j < k || (name === 'rankings' && j === k)); ph[o].classList.toggle('on', j === k && name !== 'rankings'); }); };
  const counters = () => {
    $('span', ph.screening).textContent = `${N} agents · ${count.asks} asks`;
    $('span', ph.dating).textContent = count.total ? `${count.done} of ${count.total} dates` : 'waiting';
    $('span', ph.verdicts).textContent = count.done ? `${count.mutual} mutual yeses` : 'waiting';
  };

  const tiles = {};
  const key = (a, b) => [a, b].sort().join('|');
  function tile(a, b) {
    const k = key(a, b); if (tiles[k]) return tiles[k];
    const A = byId[a] || {first: '?', id: a}, B = byId[b] || {first: '?', id: b};
    const t = document.createElement('a'); t.className = 'tile pending';
    t.innerHTML = `<div class="in"><div class="face front"><div class="pair">${mono(A.first, a)}${mono(B.first, b)}<span class="nm">${esc(A.first)} × ${esc(B.first)}</span></div>
      <div class="venue">finding a table…</div><div class="line"><span class="dots"><i></i><i></i><i></i></span></div></div><div class="face back"></div></div>`;
    wall.prepend(t); tiles[k] = t; $('#wall-empty')?.remove();
    return t;
  }
  async function finishTile(d, animate) {
    const t = tile(d.a, d.b);
    t.classList.remove('pending'); t.href = `/date/${d.id}`;
    t.setAttribute('aria-label', `${byId[d.a]?.first} and ${byId[d.b]?.first} at ${d.venue}, mutual ${d.mutual.toFixed(1)}`);
    $('.venue', t).textContent = '📍 ' + d.venue;
    const both = d.yes_a && d.yes_b, one = d.yes_a !== d.yes_b;
    const back = $('.back', t); back.classList.toggle('yes', both);
    back.innerHTML = `<div class="score">${d.mutual.toFixed(1)}</div><div class="tag2">${both ? 'Mutual yes' : one ? 'One-sided' : 'No spark'}</div>
      <div class="small muted" style="margin-top:6px">Watch the date →</div>`;
    const line = $('.line', t), lines = d.lines;
    if (animate && !calm && lines.length) {
      const pick = lines.length > 5 ? [lines[0], lines[2], lines[4], lines[lines.length - 3], lines[lines.length - 1]] : lines;
      for (const [who, text] of pick) { line.innerHTML = `<b>${esc(who)}:</b> ${esc(text)}`; line.classList.remove('live'); void line.offsetWidth; line.classList.add('live'); await sleep(420); }
    } else if (lines.length) {
      const [who, text] = lines[lines.length - 1]; line.innerHTML = `<b>${esc(who)}:</b> ${esc(text)}`;
    }
    t.classList.add('flip');
  }

  // events from a live job or a replay go through one paced queue, so the floor is watchable even when dates finish in a burst
  const q = []; let busy = false;
  const pace = {asks: 320, date_start: 60, date_done: 120, phase: 500};
  async function pump() {
    if (busy) return; busy = true;
    while (q.length) { const ev = q.shift(); handle(ev, true); if (!calm) await sleep(pace[ev.type] ?? 0); }
    busy = false;
  }
  function handle(ev, animate) {
    if (ev.type === 'phase') {
      setPhase(ev.phase);
      if (ev.phase === 'dating') { count.total = ev.dates; floor.classList.add('is-dating'); }
      if (ev.phase === 'rankings') { $('#to-rankings').hidden = false; $('#log')?.classList.add('collapsed'); }
    } else if (ev.type === 'asks') {
      $$('.node.asking', nodesG).forEach(n => n.classList.remove('asking'));
      $(`.node[data-id="${CSS.escape(ev.from)}"]`, nodesG)?.classList.add('asking');
      ev.picks.forEach((p, j) => animate && !calm ? setTimeout(() => drawArc(ev.from, p.id, p.why, true), j * 45) : drawArc(ev.from, p.id, p.why, false));
      count.asks += ev.picks.length;
    } else if (ev.type === 'date_start') {
      tile(ev.a, ev.b);
    } else if (ev.type === 'date_done') {
      count.done++; if (ev.yes_a && ev.yes_b) count.mutual++;
      finishTile(ev, animate);
    }
    counters();
  }
  const push = ev => { q.push(ev); pump(); };

  const lastEvents = () => {
    const evs = [{type: 'phase', phase: 'screening'}];
    for (const [from, picks] of Object.entries(data.last.asks)) evs.push({type: 'asks', from, picks});
    evs.push({type: 'phase', phase: 'dating', dates: data.last.dates.length});
    [...data.last.dates].sort((x, y) => x.id < y.id ? -1 : 1).forEach(d => evs.push({type: 'date_done', ...d}));
    evs.push({type: 'phase', phase: 'verdicts'}, {type: 'phase', phase: 'rankings'});
    return evs;
  };
  const clear = () => { arcsG.innerHTML = ''; wall.innerHTML = ''; for (const k in tiles) delete tiles[k]; for (const k in asked) delete asked[k];
    Object.assign(count, {asks: 0, done: 0, total: 0, mutual: 0}); $('#to-rankings').hidden = true; floor.classList.remove('is-dating'); };

  if (data.job) {
    clear(); const log = $('#log'); log.classList.add('on');
    stream(data.job, {
      onMsg: m => { log.textContent += m + '\n'; log.scrollTop = 1e9; },
      onEvent: push,
      onDone: m => { if (m.error) { log.innerHTML += `<span class="err">${esc(humanError(m.error))}</span>\n`; $('#floor-status').innerHTML = `<span class="saying err">${esc(humanError(m.error))}</span>`; } },
    });
    history.replaceState(null, '', '/round');
  } else if (data.last.dates.length) {
    lastEvents().forEach(ev => handle(ev, false));  // show the finished floor; "Replay" animates it
  }
  $('#replay-round')?.addEventListener('click', () => { clear(); lastEvents().forEach(push); scrollTo({top: 0, behavior: 'smooth'}); });
}

/* ================================================================ rankings */
const rk = $('#rankings');
if (rk) {
  const views = {cards: $('.cards-view'), matrix: $('.matrix-view')};
  $$('.seg button', rk).forEach(b => b.addEventListener('click', () => {
    $$('.seg button', rk).forEach(x => x.setAttribute('aria-pressed', x === b));
    for (const k in views) views[k].hidden = k !== b.dataset.view;
  }));
  const search = $('#rk-search'), table = $('table.matrix');
  search?.addEventListener('input', () => {
    const s = search.value.trim().toLowerCase();
    $$('.rk', rk).forEach(c => c.hidden = !!s && !c.dataset.name.includes(s));
    if (table) {
      table.classList.toggle('filtered', !!s);
      $$('tbody tr', table).forEach(tr => tr.classList.toggle('hot', !!s && tr.dataset.name.includes(s)));
    }
  });
  table?.addEventListener('mousemove', e => {
    const td = e.target.closest('td[data-fit]');
    if (!td) return hideTip();
    const heads = $$('thead th', table), col = td.cellIndex;
    const who = td.parentElement.firstElementChild.textContent, cand = heads[col].textContent, {fit, my, their} = td.dataset;
    showTip(`<b>${esc(who)} → ${esc(cand)}</b> · fit ${fit}<br>` + (my
      ? `${esc(who)}'s agent ${my} · ${esc(cand)}'s agent ${their}${td.classList.contains('mut') ? '<br>✓ mutual yes' : ''}`
      : 'Not dated: screening prior only'), e);
    heads.forEach((th, k) => th.classList.toggle('hot', k === col));
  });
  table?.addEventListener('mouseleave', hideTip);
  table?.addEventListener('click', e => { const td = e.target.closest('td[data-date]'); if (td) location.href = '/date/' + td.dataset.date; });
}

/* ================================================================ discovery: stream a running search, then reload */
const dlog = $('#discovery-log');
if (dlog) {
  stream(dlog.dataset.job, {
    onMsg: m => { dlog.textContent += m + '
'; dlog.scrollTop = 1e9; },
    onDone: m => {
      const st = $('#discovery-status');
      if (m.error) { st.className = 'saying err'; st.textContent = humanError(m.error); return; }
      st.textContent = '✓ Done. Loading the results…';
      setTimeout(() => location.href = '/discovery', 600);
    },
  });
}
