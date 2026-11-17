// ---------- header ----------
const lead = document.getElementById('lead');
const B = (t) => el('b', 'num', t);
lead.append('أكثر ساعة تأتي فيها التبرعات هي ', B(hh(peakHour.h)), ' (', B(pct(peakHour.n / totalHourly)), ' من كل التبرعات)، و',
  B(topDay.wd), ' أعلى أيام الأسبوع بمتوسط ', B(f1(topDay.v)), ' متبرعاً في اليوم. وفي العشر الأواخر من رمضان يرتفع عدد المتبرعين اليومي بنحو ',
  B(signed0(last10.c)), ' مقارنة بالأيام المماثلة.');
document.getElementById('metaLine').textContent =
  `من ${monthFmt.format(new Date(S.start))} إلى ${monthFmt.format(new Date(S.end))} · تبرعات يدوية فقط (بدون الاستقطاعات الآلية) · الأوقات كما سُجّلت في النظام`;
const kpis = [['عدد التبرعات', f0(+S.donations)], ['عدد المتبرعين', f0(+S.donors)], ['إجمالي المبالغ (ريال)', f0(+S.amount)],
  ['متوسط المتبرعين في اليوم', f1(+S.avg_donors_per_day)], ['أيام فيها تبرعات', f0(+S.days_with_data)]];
document.getElementById('kpis').replaceChildren(...kpis.map(([l, v]) => { const k = el('div', 'kpi'); k.append(el('span', null, l), el('strong', null, v)); return k; }));
document.getElementById('payRange').textContent = PAY_DAYS[0] + '–' + PAY_DAYS[1];

// ---------- ranked periods ----------
const ranked = model.filter((r) => r.rank != null).sort((a, b) => a.rank - b.rank);
const ciMax = d3.max(ranked, (r) => r.hi);
document.getElementById('ranks').replaceChildren(...ranked.map((r, i) => {
  const c = el('div', 'rank' + (i === 0 ? ' first' : ''));
  const top = el('div', 'rank-top'); top.append(el('span', 'rank-n', String(r.rank)), el('span', 'pill', r.type));
  const track = el('div', 'ci-track'); const band = el('i'); const pt = el('b');
  band.style.right = (Math.max(0, r.lo) / ciMax) * 100 + '%'; band.style.width = ((r.hi - Math.max(0, r.lo)) / ciMax) * 100 + '%';
  pt.style.right = `calc(${(r.c / ciMax) * 100}% - 2px)`;
  track.append(band, pt);
  c.append(top, el('div', 'rank-name', r.factor), el('div', 'rank-val', signed0(r.c)), track,
    el('div', 'rank-ci', 'على الأقل ' + signed0(r.lo) + ' وقد يصل إلى ' + signed0(r.hi)));
  return c;
}));

// ---------- tables ----------
const td = (t, cls) => el('td', cls, t);
const slots = [...wh].sort((a, b) => b.donations - a.donations).slice(0, 5);
document.getElementById('slots').replaceChildren(...slots.map((r, i) => {
  const tr = el('tr'); const n = td(''); n.append(el('span', 'slot-n', String(i + 1)));
  tr.append(n, td(r.wd), td(hh(r.h) + '–' + hh((r.h + 1) % 24), 'num'), td(f0(r.donations), 'num'), td(f0(r.donors), 'num hide-narrow'), td(f0(r.amount), 'num hide-narrow'));
  return tr;
}));
const proj = DATA.top_projects.map((r) => ({ p: r.project, n: +r.donations, u: +r.donors, a: +r.amount }));
const pmax = d3.max(proj, (r) => r.n);
document.getElementById('proj').replaceChildren(...proj.map((r) => {
  const tr = el('tr'); const c = td(''); const w = el('div', 'cellbar'); const bar = el('i');
  bar.style.width = Math.max(3, (r.n / pmax) * 140) + 'px'; w.append(bar, el('span', 'num', f0(r.n))); c.append(w);
  tr.append(td(r.p), c, td(f0(r.u), 'num hide-narrow'), td(f0(r.a), 'num'));
  return tr;
}));
const notes = [
  `استُبعدت ${f0(+S.excluded_recurring)} عملية استقطاع آلي (التبرع الدوري)، لأن وقتها يحدده النظام لا المتبرع.`,
  `دُمجت ${f0(+S.merged_duplicates)} نسخة مكررة من نفس العملية، فبقيت ${f0(+S.donations)} عملية من ${f0(+S.donors)} متبرع.`,
  'نتائج «أفضل الفترات» من نموذج بواسون في دفتر كولاب: يقارن كل يوم بأيام مماثلة بعد ضبط يوم الأسبوع ونمو المنصة والمواسم وأيام الرواتب، مع أخطاء معيارية HAC. «ارتفاع واضح» يعني أن مدى الثقة ٩٥٪ كله فوق الصفر وأن التحقق الثاني يوافقه.',
  'هذه علاقة في البيانات وليست دليلاً على السبب. هي ترشّح فترات لتجربة الحملات فيها، ولا تثبت أفضل وقت للإعلان لعدم وجود بيانات حملات.',
  'الأوقات كما سُجّلت في النظام (يُفترض أنها بتوقيت السعودية؛ نمط السحور وقبيل الإفطار في رمضان يدعم ذلك).',
];
document.getElementById('notes').replaceChildren(...notes.map((n) => el('li', null, n)));
