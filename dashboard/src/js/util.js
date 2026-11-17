// ---------- helpers ----------
const f0 = d3.format(','), f1 = d3.format(',.1f'), pct = d3.format('.1%'), pct0 = d3.format('.0%');
const signed = (v) => (v > 0 ? '+' : '') + d3.format(',.1f')(v) + '%';
const signed0 = (v) => (v > 0 ? '+' : '') + d3.format(',.0f')(v) + '%';
const hh = (h) => String(h).padStart(2, '0') + ':00';
const monthFmt = new Intl.DateTimeFormat('ar-u-nu-latn', { month: 'long', year: 'numeric', timeZone: 'UTC' });
const monFmt = new Intl.DateTimeFormat('ar-u-nu-latn', { month: 'short', timeZone: 'UTC' });
const dayFmt = new Intl.DateTimeFormat('ar-u-nu-latn', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const PAY_DAYS = [25, 28];
const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let firstDraw = true;

// SVG is RTL: anchor "start" = text's right edge at x.
const RIGHT = 'start';

const tipEl = document.getElementById('tip');
function showTip(ev, head, lines) {
  tipEl.replaceChildren(el('div', 'h', head), ...lines.map((l) => el('div', 'v', l)));
  tipEl.hidden = false;
  const w = tipEl.offsetWidth, h = tipEl.offsetHeight;
  let x = ev.clientX - w - 14; if (x < 8) x = Math.min(ev.clientX + 14, innerWidth - w - 8);
  let y = ev.clientY + 14; if (y + h > innerHeight - 8) y = ev.clientY - h - 14;
  tipEl.style.left = x + 'px'; tipEl.style.top = y + 'px';
}
const hideTip = () => { tipEl.hidden = true; };

function svgIn(box, W, H) {
  box.replaceChildren();
  return d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`).attr('direction', 'rtl');
}
function measure(svg, texts, cls) {
  const g = svg.append('g').attr('class', cls); let w = 0;
  texts.forEach((t) => { w = Math.max(w, g.append('text').text(t).node().getComputedTextLength()); });
  g.remove(); return w;
}

function bars(box, rows, o) {
  const W = Math.max(280, box.clientWidth), H = o.height || 230, B = 30;
  const svg = svgIn(box, W, H);
  const y = d3.scaleLinear([0, d3.max(rows, o.val) || 1], [H - B, 14]).nice();
  const ticks = y.ticks(4);
  const mr = measure(svg, ticks.map(f0), 'tick') + 12, ml = 4;
  const x = d3.scaleBand(rows.map(o.cat), [W - mr, ml]).paddingInner(0.28).paddingOuter(0.1);
  const bw = Math.min(34, x.bandwidth()), off = (x.bandwidth() - bw) / 2;
  svg.append('g').selectAll('line').data(ticks).join('line').attr('class', (d) => (d === 0 ? 'ax' : 'gl'))
    .attr('x1', ml).attr('x2', W - mr).attr('y1', y).attr('y2', y);
  svg.append('g').selectAll('text').data(ticks).join('text').attr('class', 'tick')
    .attr('x', W - 2).attr('y', y).attr('dy', '0.32em').attr('text-anchor', RIGHT).text(f0);
  const col = o.color || (() => 'var(--accent)');
  svg.append('g').selectAll('rect').data(rows).join('rect')
    .attr('class', firstDraw && !reduce ? 'grow' : null)
    .style('animation-delay', (r, i) => i * 18 + 'ms')
    .attr('x', (r) => x(o.cat(r)) + off).attr('width', bw)
    .attr('y', (r) => y(o.val(r))).attr('height', (r) => y(0) - y(o.val(r)))
    .attr('rx', Math.min(5, bw / 2)).style('fill', col);
  const xf = o.xfmt || String;
  const lw = measure(svg, rows.map((r) => xf(o.cat(r))), 'tick') + 8;
  const every = Math.max(1, Math.ceil(lw / x.step()));
  svg.append('g').selectAll('text').data(rows.filter((r, i) => i % every === 0)).join('text').attr('class', 'tick')
    .attr('x', (r) => x(o.cat(r)) + x.bandwidth() / 2).attr('y', H - 9).attr('text-anchor', 'middle').text((r) => xf(o.cat(r)));
  if (o.labelTop) {
    const top = rows.reduce((a, b) => (o.val(b) > o.val(a) ? b : a));
    svg.append('text').attr('class', 'val').attr('x', x(o.cat(top)) + x.bandwidth() / 2).attr('y', y(o.val(top)) - 6)
      .attr('text-anchor', 'middle').text(f1(o.val(top)));
  }
  svg.append('g').selectAll('rect').data(rows).join('rect').attr('class', 'hit')
    .attr('x', (r) => x(o.cat(r)) - (x.step() - x.bandwidth()) / 2).attr('width', x.step()).attr('y', 0).attr('height', H - B)
    .on('pointermove', (ev, r) => { const t = o.tip(r); showTip(ev, t[0], t.slice(1)); }).on('pointerleave', hideTip);
}
