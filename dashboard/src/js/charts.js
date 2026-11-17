// ---------- charts ----------
let heatMetric = 'donations';
const metricName = { donations: 'تبرع', donors: 'متبرع', amount: 'ريال' };

const charts = {
  forest(box) {
    const rows = [...model].sort((a, b) => b.c - a.c);
    const W = Math.max(300, box.clientWidth), rowH = 27, top = 6, Bm = 28, H = top + rows.length * rowH + Bm;
    const svg = svgIn(box, W, H);
    const lw = Math.min(W * 0.45, measure(svg, rows.map((r) => r.factor), 'lab') + 14);
    const vw = measure(svg, rows.map((r) => signed0(r.c)), 'val') + 12;
    const x = d3.scaleLinear([Math.min(0, d3.min(rows, (r) => r.lo)), d3.max(rows, (r) => r.hi)], [W - lw - 8, vw + 4]).nice();
    const color = (r) => (r.conclusion === 'ارتفاع واضح' ? 'var(--accent)' : r.conclusion === 'انخفاض واضح' ? 'var(--bad)' : 'var(--bar-muted)');
    const yb = H - Bm, tk = x.ticks(W < 500 ? 3 : 6);
    svg.append('g').selectAll('line').data(tk).join('line').attr('class', 'gl').attr('x1', x).attr('x2', x).attr('y1', top).attr('y2', yb);
    svg.append('g').selectAll('text').data(tk).join('text').attr('class', 'tick').attr('x', x).attr('y', H - 8).attr('text-anchor', 'middle').text((v) => f0(v) + '%');
    svg.append('line').attr('class', 'ref').attr('x1', x(0)).attr('x2', x(0)).attr('y1', top).attr('y2', yb);
    const g = svg.append('g').selectAll('g').data(rows).join('g').attr('transform', (r, i) => `translate(0,${top + i * rowH + rowH / 2})`);
    g.append('rect').attr('x', 0).attr('width', W).attr('y', -rowH / 2).attr('height', rowH).style('fill', (r, i) => (i % 2 ? 'transparent' : 'var(--surface-2)')).attr('rx', 6).style('opacity', .6);
    g.append('text').attr('class', 'lab').attr('x', W - 6).attr('dy', '0.32em').attr('text-anchor', RIGHT).text((r) => r.factor);
    g.append('line').attr('x1', (r) => x(r.lo)).attr('x2', (r) => x(r.hi)).style('stroke', color).attr('stroke-width', 3).attr('stroke-linecap', 'round').style('opacity', .55);
    g.append('circle').attr('cx', (r) => x(r.c)).attr('r', 5.5).style('fill', color).style('stroke', 'var(--surface)').attr('stroke-width', 2);
    g.append('text').attr('class', 'val').attr('x', (r) => x(r.hi) - 8).attr('dy', '0.32em').attr('text-anchor', RIGHT).text((r) => signed0(r.c));
    g.append('rect').attr('class', 'hit').attr('x', 0).attr('width', W).attr('y', -rowH / 2).attr('height', rowH)
      .on('pointermove', (ev, r) => showTip(ev, r.factor, ['التغيّر المقدّر: ' + signed(r.c), 'المدى ٩٥٪: ' + signed(r.lo) + ' إلى ' + signed(r.hi), r.conclusion]))
      .on('pointerleave', hideTip);
  },

  heat(box) {
    const days = Array.from(new Map(wh.map((r) => [r.wo, r.wd])).entries()).sort((a, b) => a[0] - b[0]).map((e) => e[1]);
    const W = Math.max(300, box.clientWidth);
    const svg = svgIn(box, W, 100);
    const lw = measure(svg, days, 'lab') + 12;
    const cw = (W - lw - 2) / 24, ch = Math.max(22, Math.min(34, cw));
    const H = days.length * ch + 28;
    svg.attr('viewBox', `0 0 ${W} ${H}`);
    const cx = (h) => W - lw - (h + 1) * cw, cy = (wo) => (wo - 1) * ch;
    const v = (r) => r[heatMetric];
    const max = d3.max(wh, v) || 1;
    const best = wh.reduce((a, b) => (v(b) > v(a) ? b : a));
    svg.append('g').selectAll('rect').data(wh).join('rect')
      .attr('class', firstDraw && !reduce ? 'fade' : null).style('animation-delay', (r) => r.h * 15 + 'ms')
      .attr('x', (r) => cx(r.h) + 1.5).attr('y', (r) => cy(r.wo) + 1.5).attr('width', Math.max(1, cw - 3)).attr('height', ch - 3).attr('rx', 4)
      .style('fill', 'var(--accent)').style('fill-opacity', (r) => 0.06 + 0.94 * Math.pow(v(r) / max, 0.85))
      .style('stroke', (r) => (r === best ? 'var(--gold)' : 'none')).attr('stroke-width', 2.5)
      .on('pointermove', (ev, r) => showTip(ev, r.wd + ' · ' + hh(r.h) + '–' + hh((r.h + 1) % 24), [f0(r.donations) + ' تبرع', f0(r.donors) + ' متبرع', f0(r.amount) + ' ريال']))
      .on('pointerleave', hideTip);
    svg.append('g').selectAll('text').data(days).join('text').attr('class', 'lab')
      .attr('x', W - 2).attr('y', (d, i) => i * ch + ch / 2).attr('dy', '0.32em').attr('text-anchor', RIGHT).text((d) => d);
    const step = cw < 18 ? 6 : 3;
    svg.append('g').selectAll('text').data(d3.range(0, 24, step)).join('text').attr('class', 'tick')
      .attr('x', (h) => cx(h) + cw / 2).attr('y', H - 8).attr('text-anchor', 'middle').text(hh);
  },

  clock(box) {
    const W = Math.max(260, box.clientWidth), size = Math.min(W, 380), H = size;
    const svg = svgIn(box, W, H);
    const g = svg.append('g').attr('transform', `translate(${W / 2},${H / 2})`);
    const R = size / 2 - 24, r0 = R * 0.38;
    const max = d3.max(hourly, (r) => r.n);
    const rs = d3.scaleRadial([0, max], [r0, R]);
    const ang = (h) => (h / 24) * 2 * Math.PI;
    [0.5, 1].forEach((k) => g.append('circle').attr('r', rs(max * k)).style('fill', 'none').attr('class', 'gl'));
    const arc = d3.arc().innerRadius(r0).outerRadius((r) => rs(r.n)).startAngle((r) => ang(r.h) + 0.02).endAngle((r) => ang(r.h + 1) - 0.02).cornerRadius(3);
    g.append('g').selectAll('path').data(hourly).join('path')
      .attr('class', firstDraw && !reduce ? 'fade' : null).style('animation-delay', (r) => r.h * 25 + 'ms')
      .attr('d', arc).style('fill', (r) => (r === peakHour ? 'var(--gold)' : 'var(--accent)')).style('fill-opacity', (r) => (r === peakHour ? 1 : 0.35 + 0.65 * (r.n / max)))
      .on('pointermove', (ev, r) => showTip(ev, hh(r.h) + '–' + hh((r.h + 1) % 24), [f0(r.n) + ' تبرع', pct(r.n / totalHourly) + ' من الإجمالي']))
      .on('pointerleave', hideTip);
    g.append('g').selectAll('text').data(d3.range(0, 24, 3)).join('text').attr('class', 'tick').attr('text-anchor', 'middle').attr('dy', '0.32em')
      .attr('x', (h) => Math.sin(ang(h)) * (R + 14)).attr('y', (h) => -Math.cos(ang(h)) * (R + 14)).text(hh);
    g.append('text').attr('text-anchor', 'middle').attr('y', -6).style('font-family', 'var(--font-display)').style('font-weight', 800)
      .style('font-size', Math.max(18, r0 * 0.42) + 'px').style('fill', 'var(--ink)').text(hh(peakHour.h));
    g.append('text').attr('text-anchor', 'middle').attr('y', r0 * 0.35).attr('class', 'tick').text('ساعة الذروة');
  },

  hourly(box) {
    const W = Math.max(280, box.clientWidth), H = 240, Bm = 30;
    const svg = svgIn(box, W, H);
    const y = d3.scaleLinear([0, d3.max(hourly, (r) => Math.max(r.rs, r.os))], [H - Bm, 14]).nice();
    const ticks = y.ticks(4);
    const mr = measure(svg, ticks.map(pct0), 'tick') + 12, ml = 8;
    const x = d3.scaleLinear([0, 23], [W - mr - 6, ml]);
    svg.append('g').selectAll('line').data(ticks).join('line').attr('class', (v) => (v === 0 ? 'ax' : 'gl')).attr('x1', ml).attr('x2', W - mr).attr('y1', y).attr('y2', y);
    svg.append('g').selectAll('text').data(ticks).join('text').attr('class', 'tick').attr('x', W - 2).attr('y', y).attr('dy', '0.32em').attr('text-anchor', RIGHT).text(pct0);
    svg.append('g').selectAll('text').data(d3.range(0, 24, W < 420 ? 6 : 3)).join('text').attr('class', 'tick').attr('x', x).attr('y', H - 9).attr('text-anchor', 'middle').text(hh);
    const series = [{ k: 'os', c: 'var(--accent)', id: 'gO' }, { k: 'rs', c: 'var(--gold)', id: 'gR' }];
    const defs = svg.append('defs');
    series.forEach((s) => {
      const lg = defs.append('linearGradient').attr('id', s.id).attr('x1', 0).attr('x2', 0).attr('y1', 0).attr('y2', 1);
      [[0, .28], [.5, .08], [1, 0]].forEach(([o, a]) => lg.append('stop').attr('offset', o).style('stop-color', s.c).style('stop-opacity', a));
      svg.append('path').datum(hourly).style('fill', `url(#${s.id})`).attr('d', d3.area().x((r) => x(r.h)).y0(y(0)).y1((r) => y(r[s.k])));
      svg.append('path').datum(hourly).attr('fill', 'none').style('stroke', s.c).attr('stroke-width', 2.5).attr('stroke-linecap', 'round').attr('stroke-linejoin', 'round')
        .attr('d', d3.line().x((r) => x(r.h)).y((r) => y(r[s.k])));
    });
    const rule = svg.append('line').attr('class', 'ref').attr('y1', 14).attr('y2', H - Bm).style('opacity', 0);
    const dots = series.map((s) => svg.append('circle').attr('r', 4.5).style('fill', s.c).style('stroke', 'var(--surface)').attr('stroke-width', 2).style('opacity', 0));
    svg.append('rect').attr('class', 'hit').attr('x', ml).attr('width', W - mr - ml).attr('y', 0).attr('height', H - Bm)
      .on('pointermove', (ev) => {
        const h = Math.max(0, Math.min(23, Math.round(x.invert(d3.pointer(ev)[0]))));
        const r = hourly[h];
        rule.attr('x1', x(h)).attr('x2', x(h)).style('opacity', 1);
        dots.forEach((dt, i) => dt.attr('cx', x(h)).attr('cy', y(r[series[i].k])).style('opacity', 1));
        showTip(ev, hh(h) + '–' + hh((h + 1) % 24), ['رمضان: ' + pct(r.rs) + ' (' + f1(r.rd) + ' تبرع/يوم)', 'باقي السنة: ' + pct(r.os) + ' (' + f1(r.od) + ' تبرع/يوم)']);
      })
      .on('pointerleave', () => { rule.style('opacity', 0); dots.forEach((dt) => dt.style('opacity', 0)); hideTip(); });
  },

  weekday(box) {
    bars(box, weekday, { cat: (r) => r.wd, val: (r) => r.v, labelTop: true,
      color: (r) => (r === topDay ? 'var(--gold)' : 'var(--accent)'),
      tip: (r) => [r.wd, f1(r.v) + ' متبرع في اليوم', f1(r.n) + ' تبرع في اليوم', 'على ' + f0(r.days) + ' يوماً'] });
  },
  dom(box) {
    const rows = DATA.day_of_month.map((r) => ({ d: +r.dom, v: +r.avg_donors, n: +r.days })).sort((a, b) => a.d - b.d);
    bars(box, rows, { cat: (r) => r.d, val: (r) => r.v,
      color: (r) => (r.d >= PAY_DAYS[0] && r.d <= PAY_DAYS[1] ? 'var(--gold)' : 'var(--bar-muted)'),
      tip: (r) => ['اليوم ' + r.d + ' من الشهر', f1(r.v) + ' متبرع في اليوم', 'على ' + f0(r.n) + ' يوماً'] });
  },
  hijri(box) {
    const rows = DATA.hijri_month.map((r) => ({ m: +r.hijri_month, name: r.hijri_month_name, v: +r.avg_donors, n: +r.days, a: +r.amount })).sort((a, b) => a.m - b.m);
    bars(box, rows, { cat: (r) => r.name, val: (r) => r.v, height: 250, labelTop: true,
      color: (r) => (r.m === 9 ? 'var(--gold)' : r.m === 12 ? 'var(--accent)' : 'var(--bar-muted)'),
      tip: (r) => [r.name, f1(r.v) + ' متبرع في اليوم', f0(r.a) + ' ريال', 'على ' + f0(r.n) + ' يوماً'] });
  },
  ramadan(box) {
    const rows = DATA.ramadan_days.map((r) => ({ d: +r.hijri_day, v: +r.avg_donors, n: +r.days })).sort((a, b) => a.d - b.d);
    bars(box, rows, { cat: (r) => r.d, val: (r) => r.v, height: 250,
      color: (r) => (r.d >= 21 ? 'var(--gold)' : 'var(--accent)'),
      tip: (r) => [r.d + ' رمضان', f1(r.v) + ' متبرع في اليوم', 'متوسط ' + f0(r.n) + ' سنوات'] });
  },

  trend(box) {
    const num = (v) => (v === '' || v == null ? null : +v);
    const rows = DATA.daily.map((r) => ({ t: new Date(r.date), v: num(r.donors), n: num(r.donations), a: num(r.amount), hm: num(r.hijri_month), hd: num(r.hijri_day), hn: r.hijri_month_name })).sort((a, b) => a.t - b.t);
    const W = Math.max(300, box.clientWidth), H = 280, Bm = 42;
    const svg = svgIn(box, W, H);
    const y = d3.scaleLinear([0, d3.max(rows, (r) => r.v)], [H - Bm, 12]).nice();
    const ticks = y.ticks(4);
    const mr = measure(svg, ticks.map(f0), 'tick') + 12, ml = 6;
    const x = d3.scaleUtc(d3.extent(rows, (r) => r.t), [W - mr - 4, ml]);
    const runs = [];
    rows.forEach((r) => { if (r.hm !== 9) return; const L = runs[runs.length - 1]; if (L && r.t - L.end <= 2 * 864e5) L.end = r.t; else runs.push({ start: r.t, end: r.t }); });
    svg.append('g').selectAll('rect').data(runs).join('rect')
      .attr('x', (r) => x(d3.utcDay.offset(r.end, 1))).attr('width', (r) => Math.max(1, x(r.start) - x(d3.utcDay.offset(r.end, 1))))
      .attr('y', 12).attr('height', H - Bm - 12).attr('rx', 4).style('fill', 'var(--gold)').style('fill-opacity', 0.16);
    svg.append('g').selectAll('line').data(ticks).join('line').attr('class', (v) => (v === 0 ? 'ax' : 'gl')).attr('x1', ml).attr('x2', W - mr).attr('y1', y).attr('y2', y);
    svg.append('g').selectAll('text').data(ticks).join('text').attr('class', 'tick').attr('x', W - 2).attr('y', y).attr('dy', '0.32em').attr('text-anchor', RIGHT).text(f0);
    const every = W < 560 ? 6 : 3;
    const months = x.ticks(d3.utcMonth.every(every));
    const xt = svg.append('g').selectAll('g').data(months).join('g').attr('transform', (m) => `translate(${x(m)},0)`);
    xt.append('text').attr('class', 'tick').attr('y', H - Bm + 17).attr('text-anchor', 'middle').text((m) => monFmt.format(m));
    xt.append('text').attr('class', 'tick').attr('y', H - Bm + 33).attr('text-anchor', 'middle').text((m, i) => (i === 0 || m.getUTCMonth() < every ? String(m.getUTCFullYear()) : ''));
    const defs = svg.append('defs'); const lg = defs.append('linearGradient').attr('id', 'gT').attr('x1', 0).attr('x2', 0).attr('y1', 0).attr('y2', 1);
    [[0, .26], [.25, .16], [.5, .08], [.75, .03], [1, 0]].forEach(([o, a]) => lg.append('stop').attr('offset', o).style('stop-color', 'var(--accent)').style('stop-opacity', a));
    const def = (r) => r.v != null;
    svg.append('path').datum(rows).style('fill', 'url(#gT)').attr('d', d3.area().defined(def).x((r) => x(r.t)).y0(y(0)).y1((r) => y(r.v)));
    svg.append('path').datum(rows).attr('fill', 'none').style('stroke', 'var(--accent)').attr('stroke-width', 1.6).attr('stroke-linejoin', 'round')
      .attr('d', d3.line().defined(def).x((r) => x(r.t)).y((r) => y(r.v)));
    const peak = rows.reduce((a, b) => ((b.v || 0) > (a.v || 0) ? b : a));
    svg.append('circle').attr('cx', x(peak.t)).attr('cy', y(peak.v)).attr('r', 4).style('fill', 'var(--gold)');
    const leftSide = x(peak.t) < W / 2;
    svg.append('text').attr('class', 'val').attr('x', x(peak.t) + (leftSide ? 8 : -8)).attr('y', y(peak.v)).attr('dy', '0.32em').attr('text-anchor', leftSide ? 'end' : RIGHT)
      .text('أعلى يوم: ' + f0(peak.v) + ' متبرع (' + peak.hd + ' ' + peak.hn + ')');
    const dot = svg.append('circle').attr('r', 4.5).style('fill', 'var(--accent)').style('stroke', 'var(--surface)').attr('stroke-width', 2).style('opacity', 0);
    const withData = rows.filter(def); const bis = d3.bisector((r) => r.t).center;
    svg.append('rect').attr('class', 'hit').attr('x', ml).attr('width', W - mr - ml).attr('y', 0).attr('height', H - Bm)
      .on('pointermove', (ev) => {
        const r = withData[bis(withData, x.invert(d3.pointer(ev)[0]))]; if (!r) return;
        dot.attr('cx', x(r.t)).attr('cy', y(r.v)).style('opacity', 1);
        showTip(ev, dayFmt.format(r.t), [r.hd + ' ' + r.hn, f0(r.v) + ' متبرع', f0(r.n) + ' تبرع', f0(r.a) + ' ريال']);
      })
      .on('pointerleave', () => { dot.style('opacity', 0); hideTip(); });
  },
};

// Heatmap metric toggle
document.querySelectorAll('.seg button[data-m]').forEach((b) => b.addEventListener('click', () => {
  heatMetric = b.dataset.m;
  document.querySelectorAll('.seg button[data-m]').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
  charts.heat(document.getElementById('heat'));
}));
