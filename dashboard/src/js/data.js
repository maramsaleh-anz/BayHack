// ---------- data ----------
const S = DATA.summary[0];
const wh = DATA.weekday_hour.map((r) => ({ wo: +r.weekday_order, wd: r.weekday, h: +r.hour, donations: +r.donations, donors: +r.donors, amount: +r.amount }));
const hourly = DATA.hourly.map((r) => ({ h: +r.hour, rs: +r.ramadan_share, os: +r.other_share, rd: +r.ramadan_per_day, od: +r.other_per_day, n: +r.all_donations }));
const weekday = DATA.weekday.map((r) => ({ o: +r.weekday_order, wd: r.weekday, v: +r.avg_donors, n: +r.avg_donations, days: +r.days })).sort((a, b) => a.o - b.o);
const model = DATA.model_results.map((r) => ({ ...r, c: +r.change_pct, lo: +r.ci_low, hi: +r.ci_high, rank: r.rank === '' || r.rank == null ? null : +r.rank }));
const totalHourly = d3.sum(hourly, (r) => r.n);
const peakHour = hourly.reduce((a, b) => (b.n > a.n ? b : a));
const topDay = weekday.reduce((a, b) => (b.v > a.v ? b : a));
const last10 = model.find((r) => r.key === 'ramadan_last10');
