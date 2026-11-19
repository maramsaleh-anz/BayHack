// Reminder calendar (the "تقويم التذكيرات" section): draws the calendar, the day detail, the KPIs and the send schedule.
// All the logic (dates, multipliers, send hours) is in planner-core.js; this file only builds the page.
(function planner() {
  const { DAY, utc, LABELS } = PlannerCore;
  const hijri = PlannerCore.createHijri();
  if (!hijri) {
    document.querySelector('#planner .card').replaceChildren(el('p', 'note', 'هذا المتصفح لا يدعم التقويم الهجري (أم القرى)، فتعذّر عرض التقويم.'));
    return;
  }
  const core = PlannerCore.createPlanner({ model, hourly, weekdayHours: wh, hijri, hourLabel: hh,
    todayMs: PlannerCore.parseToday(location.search, new Date()) });
  const { todayMs, ramStart, ramYear, views: VIEWS, FX, info, sendTimes, messageType } = core;

  // ---------- formatting ----------
  const xs = (m) => '⁦×' + (m >= 10 ? f0(m) : f1(m)) + '⁩';   // "×5.8", kept left-to-right inside Arabic text
  const ltr = (text, cls) => el('span', 'ltr' + (cls ? ' ' + cls : ''), text);
  const dateFmt = new Intl.DateTimeFormat('ar-u-nu-latn', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
  const shortFmt = new Intl.DateTimeFormat('ar-u-nu-latn', { day: 'numeric', month: 'short', timeZone: 'UTC' });
  const monthTitleFmt = new Intl.DateTimeFormat('ar-u-nu-latn', { month: 'long', year: 'numeric', timeZone: 'UTC' });
  const hijriText = (h) => h.d + ' ' + h.name + ' ' + h.y;
  const WEEKDAYS = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];
  const WEEKDAY_LETTERS = 'حنثرخجس';
  const appendTimes = (parent, times) => times.forEach((t, n) => { if (n) parent.append(' و '); parent.append(ltr(t)); });
  const timesNode = (times) => {
    const node = el('span');
    if (times) appendTimes(node, times); else node.textContent = '—';
    return node;
  };

  document.getElementById('v-ram').textContent = 'رمضان ' + ramYear;
  let view = 'ram';
  const cells = new Map();   // timestamp -> its button, to mark the selected day

  // ---------- day detail ----------
  function renderDetail(i) {
    const big = el('div', 'big'); big.append(ltr(xs(i.m)));
    const factors = el('ul');
    if (i.parts.length) i.parts.forEach(([name, value]) => { const li = el('li'); li.append(el('span', null, name), ltr(xs(value), 'num')); factors.append(li); });
    else factors.append(el('li', null, 'لا عامل مرتفع واضح في هذا اليوم'));
    const advice = el('div', 'act');
    advice.append(el('b', null, LABELS.action[i.tier]));
    const times = sendTimes(i);
    if (times) { advice.append(document.createElement('br'), 'أرسل: '); appendTimes(advice, times); }
    advice.append(document.createElement('br'), 'الرسالة: ' + messageType(i));
    document.getElementById('plDetail').replaceChildren(
      el('h3', null, dateFmt.format(i.ms)), el('p', 'note', hijriText(i.h) + ' هـ'), big, el('span', 'tier', LABELS.tier[i.tier]),
      factors, advice, el('p', 'note', 'المضاعف مقارنة بيوم عادي (الأحد خارج المواسم وأيام الرواتب).'));
  }
  function select(ms) {
    cells.forEach((button, key) => button.setAttribute('aria-pressed', String(key === ms)));
    renderDetail(info(ms));
  }

  // ---------- calendar ----------
  function monthCard(year, month, v) {
    const first = utc(year, month, 1), last = utc(year, month + 1, 0);
    const startName = hijri(first), endName = hijri(last);
    const title = el('h4');
    title.append(el('span', null, monthTitleFmt.format(new Date(first))),
      el('small', null, startName.name === endName.name ? startName.name + ' ' + startName.y : startName.name + ' – ' + endName.name + ' ' + endName.y));
    const grid = el('div', 'pl-grid');
    WEEKDAYS.forEach((name, n) => { const head = el('div', 'pl-dow', WEEKDAY_LETTERS[n]); head.title = name; grid.append(head); });
    for (let n = new Date(first).getUTCDay(); n > 0; n--) grid.append(el('div', 'pl-blank'));
    for (let d = 1, days = new Date(last).getUTCDate(); d <= days; d++) {
      const ms = utc(year, month, d), i = info(ms);
      const button = el('button', 'pl-day t-' + i.tier + (ms < todayMs ? ' past' : '') + (ms < v.from || ms > v.to ? ' out' : ''));
      button.type = 'button'; button.setAttribute('aria-pressed', 'false');
      button.setAttribute('aria-label', dateFmt.format(ms) + '، ' + hijriText(i.h) + '، ' + xs(i.m) + '، ' + LABELS.tier[i.tier]);
      button.append(el('span', 'g', String(d)), el('span', 'h', i.h.d === 1 ? i.h.name : String(i.h.d)),
        el('i', 'x', i.tier === 'peak' || i.tier === 'high' ? xs(i.m) : ''));
      button.addEventListener('click', () => select(ms));
      button.addEventListener('pointermove', (ev) => showTip(ev, dateFmt.format(ms), [hijriText(i.h) + ' هـ', xs(i.m) + ' · ' + LABELS.tier[i.tier]]));
      button.addEventListener('pointerleave', hideTip);
      cells.set(ms, button); grid.append(button);
    }
    const card = el('div', 'pl-month'); card.append(title, grid);
    return card;
  }

  function monthsOf(v) {
    const a = new Date(v.from), b = new Date(v.to);
    const count = (b.getUTCFullYear() - a.getUTCFullYear()) * 12 + b.getUTCMonth() - a.getUTCMonth() + 1;
    return Array.from({ length: count }, (_, n) => { const d = new Date(utc(a.getUTCFullYear(), a.getUTCMonth() + n, 1)); return [d.getUTCFullYear(), d.getUTCMonth()]; });
  }

  // ---------- KPIs ----------
  function renderKpis(upcoming, topDay) {
    const kpi = (label, value, sub) => {
      const box = el('div', 'pl-kpi'), strong = el('strong');
      if (value instanceof Node) strong.append(value); else strong.textContent = value;
      box.append(el('span', null, label), strong);
      if (sub) box.append(el('small', null, sub));
      return box;
    };
    const daysToRamadan = Math.round((ramStart - todayMs) / DAY);
    const ramadanNow = todayMs >= ramStart && todayMs <= ramStart + 30 * DAY;
    const hot = upcoming.filter((i) => i.m >= 1.4 && !i.eid).length;
    document.getElementById('plKpis').replaceChildren(
      kpi(ramadanNow ? 'نحن في رمضان ' + ramYear : 'أيام على رمضان ' + ramYear,
        ramadanNow ? 'اليوم ' + hijri(todayMs).d : (daysToRamadan > 0 ? daysToRamadan + ' يوماً' : 'اليوم'),
        'بداية الشهر المتوقعة: ' + dateFmt.format(ramStart)),
      kpi('أعلى يوم في الفترة', ltr(xs(topDay.m)), dateFmt.format(topDay.ms)),
      kpi('أيام مرتفعة أو ذروة', hot + ' من ' + upcoming.length, 'يوماً في الفترة المعروضة (بدون أيام العيد)'));
  }

  // ---------- send schedule: consecutive days sharing a window (season / salary), then a recurring Friday row ----------
  function windowsOf(upcoming) {
    const windows = []; let current = null;
    upcoming.forEach((i) => {
      if (i.wkey && current && current.key === i.wkey && i.ms - current.end === DAY) current.end = i.ms;
      else if (i.wkey) { current = { key: i.wkey, start: i.ms, end: i.ms, first: i }; windows.push(current); }
      else current = null;
    });
    return windows;
  }
  function scheduleRow(cells) {
    const row = el('tr');
    cells.forEach((value) => { const td = el('td'); if (value instanceof Node) td.append(value); else td.textContent = value; row.append(td); });
    row.lastChild.className = 'hide-narrow';
    return row;
  }
  function renderSchedule(upcoming) {
    const rows = windowsOf(upcoming).map((w) => {
      const eid = w.key === 'eidf' || w.key === 'eida';
      const when = w.start === w.end ? shortFmt.format(w.start) : shortFmt.format(w.start) + ' – ' + shortFmt.format(w.end);
      return scheduleRow([LABELS.season[w.key], when, eid ? '—' : ltr(xs(FX[w.key])), timesNode(sendTimes(w.first)), messageType(w.first)]);
    });
    if (upcoming.some((i) => i.dow === 5)) {
      rows.push(scheduleRow(['كل جمعة', 'أسبوعياً', ltr(xs(FX.fri)), ltr(core.fridaySendTime), LABELS.message.other]));
    }
    document.getElementById('plAgenda').replaceChildren(...rows);
  }

  // ---------- reminder budget: the best N days of each month, the gain, and the CSV download ----------
  const budgetInput = document.getElementById('plBudget');
  let upcoming = [], picked = new Set();
  const plain = (m) => '×' + (m >= 10 ? f0(m) : f1(m));
  function renderBudget() {
    const n = +budgetInput.value;
    document.getElementById('plBudgetN').textContent = n;
    picked = PlannerCore.pickDays(upcoming, n);
    cells.forEach((button, ms) => button.classList.toggle('pick', picked.has(ms)));
    const g = PlannerCore.budgetGain(upcoming, picked), out = document.getElementById('plGain');
    if (!g) { out.textContent = ''; return; }
    out.replaceChildren(
      g.count + (g.count >= 3 && g.count <= 10 ? ' أيام مختارة' : ' يوماً مختاراً') + ' في الفترة. متوسط المضاعف فيها ', ltr(plain(g.pickedMean)), ' مقابل ', ltr(plain(g.allMean)),
      ' لو وُزّعت الرسائل على أيام الفترة كلها، أي أن كل تذكير يقع في يوم أقوى بـ ', el('strong', null, f1(g.gain) + ' مرة'), '.');
  }
  function downloadCsv() {
    const quote = (v) => '"' + String(v).replace(/"/g, '""') + '"';
    const rows = [['التاريخ', 'اليوم', 'التاريخ الهجري', 'المضاعف المتوقع', 'وقت الإرسال', 'نوع الرسالة', 'السبب']];
    upcoming.filter((i) => picked.has(i.ms)).forEach((i) => {
      const iso = new Date(i.ms).toISOString().slice(0, 10);
      rows.push([iso, WEEKDAYS[i.dow], hijriText(i.h), plain(i.m), (sendTimes(i) || []).join(' و '), messageType(i),
        i.parts.map(([name]) => name).join(' + ') || 'يوم عادي']);
    });
    const blob = new Blob(['\ufeff' + rows.map((r) => r.map(quote).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'bayyin_reminders_' + (view === 'ram' ? 'ramadan_' + ramYear : '12_months') + '.csv';
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  budgetInput.addEventListener('input', renderBudget);
  document.getElementById('plDownload').addEventListener('click', downloadCsv);

  // ---------- page ----------
  function render() {
    const v = VIEWS[view];
    cells.clear();
    document.getElementById('plCal').replaceChildren(...monthsOf(v).map(([year, month]) => monthCard(year, month, v)));
    upcoming = [];
    for (let ms = Math.max(v.from, todayMs); ms <= v.to; ms += DAY) upcoming.push(info(ms));
    const topDay = upcoming.reduce((a, b) => (b.m > a.m ? b : a));
    renderKpis(upcoming, topDay);
    renderSchedule(upcoming);
    renderBudget();
    select(topDay.ms);
  }

  document.querySelectorAll('.seg button[data-v]').forEach((b) => b.addEventListener('click', () => {
    view = b.dataset.v;
    document.querySelectorAll('.seg button[data-v]').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    render();
  }));

  document.getElementById('plNotes').replaceChildren(...[
    'كل مضاعف مقارنة بيوم عادي (الأحد خارج المواسم وأيام الرواتب). هو نسبة متوقعة لعدد المتبرعين وليس عدداً مطلقاً، ولا يشمل نمو المنصة في المستقبل.',
    'القيم من معاملات نموذج بواسون نفسه في «أفضل الفترات». الأثر يتراكم بالضرب كما في النموذج، والقيم العليا (مثل عشر رمضان مع الجمعة ويوم الراتب) افتراض نموذجي لم يُختبر بتجربة.',
    'لا تُضاف العيدان ولا حساب المواطن ولا صرف أول الشهر ولا التقاعد، لأنها لم تثبت أو تتداخل مع الرواتب. الأيام الهجرية بتقويم أم القرى، وقد يتغير بداية الشهر يوماً حسب الرؤية. أيام الرواتب بحسب القاعدة (27، مع تعديل الجمعة والسبت) وتُستبدل بأي إعلان رسمي.',
    'هذا تقويم مرشّح للاختبار وليس دليلاً على السبب: نقترح تجربة عشوائية تقيس أثر التذكير نفسه.',
  ].map((text) => el('li', null, text)));

  render();
})();
