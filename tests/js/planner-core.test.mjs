// Tests of the reminder-calendar logic (dashboard/src/js/planner-core.js).   Run:  node --test tests/js
// The Hijri dates and salary paydays are compared with what the Python analysis (hijridate, bayyin.paydays) gives.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';

const require = createRequire(import.meta.url);
const core = require('../../dashboard/src/js/planner-core.js');
const fx = JSON.parse(readFileSync(new URL('../fixtures/planner_fixtures.json', import.meta.url), 'utf8'));
const ms = (iso) => Date.parse(iso + 'T00:00:00Z');
const hourLabel = (h) => String(h).padStart(2, '0') + ':00';
const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) < eps, `${a} != ${b}`);

const hijri = core.createHijri();
const planner = (today) => core.createPlanner({ model: fx.model, hourly: fx.hourly, weekdayHours: fx.weekday_hours,
  todayMs: ms(today), hijri, hourLabel });

test('Hijri calendar is available in this Node', () => assert.ok(hijri, 'Intl islamic-umalqura missing'));

test('Hijri dates match hijridate for every day of 2026-2028', () => {
  const wrong = fx.hijri.filter(([iso, y, m, d]) => { const h = hijri(ms(iso)); return h.y !== y || h.m !== m || h.d !== d; });
  assert.equal(wrong.length, 0, 'first mismatches: ' + JSON.stringify(wrong.slice(0, 3)));
});

test('salary paydays match the Python payday calendar (27th, Friday -> 26, Saturday -> 28)', () => {
  const js = [];
  for (let y = 2026; y <= 2028; y++) for (let m = 0; m < 12; m++) js.push(new Date(core.salaryPayday(y, m)).toISOString().slice(0, 10));
  const python = fx.salary_paydays.filter((iso) => iso >= '2026-01-01' && iso <= '2028-12-31');
  assert.deepEqual(js.filter((d) => python.includes(d)), python);
  assert.equal(python.length, 36);
});

test('seasons by Hijri date', () => {
  const cases = [[9, 1, 'ram1'], [9, 20, 'ram1'], [9, 21, 'ram2'], [9, 30, 'ram2'], [10, 1, 'eidf'], [10, 3, 'eidf'], [10, 4, null],
    [12, 1, 'dhh'], [12, 9, 'dhh'], [12, 10, 'eida'], [12, 13, 'eida'], [12, 14, null], [1, 5, null], [5, 15, null]];
  cases.forEach(([m, d, expected]) => assert.equal(core.seasonOf({ m, d }), expected, `${m}/${d}`));
});

test('Ramadan 1448 starts on 8 February 2027 and is found from any day before it', () => {
  const p = planner('2026-11-19');
  assert.equal(new Date(p.ramStart).toISOString().slice(0, 10), '2027-02-08');
  assert.equal(p.ramYear, 1448);
  assert.equal(Math.round((p.ramStart - p.todayMs) / core.DAY), 81);
});

test('the Ramadan that is running now is found, then the next one after it ends', () => {
  assert.equal(new Date(planner('2027-02-20').ramStart).toISOString().slice(0, 10), '2027-02-08');
  assert.equal(planner('2027-04-10').ramYear, 1449);
});

test('multipliers are the product of the clear effects in the model', () => {
  const p = planner('2026-11-19'), { FX } = p;
  const day = p.info(ms('2027-03-05'));                       // 26 Ramadan 1448, a Friday, outside a salary window
  assert.equal(day.s, 'ram2');
  near(day.m, FX.ram2 * FX.fri);
  near(day.m, (1 + 484.0 / 100) * (1 + 53.9 / 100), 1e-6);   // numbers of the analysis (model_results.csv)
  assert.equal(day.tier, 'peak');
  const ordinary = p.info(ms('2026-12-14'));                  // an ordinary Monday
  near(ordinary.m, 1);
  assert.equal(ordinary.tier, 'norm');
  const saturday = p.info(ms('2026-12-12'));
  assert.ok(saturday.m < 1 && saturday.tier === 'low');
});

test('Eid days never get a campaign and keep the Eid tier', () => {
  const p = planner('2026-11-19'), eid = p.info(ms('2027-03-09'));   // 1 Shawwal 1448
  assert.equal(eid.tier, 'eid');
  assert.equal(p.sendTimes(eid), null);
  assert.equal(p.messageType(eid), core.LABELS.message.eid);
});

test('the salary window adds its effect only inside payday + 3 days', () => {
  const p = planner('2026-11-19');
  // 27 Dec 2026 is a Sunday: payday, then three more days
  [['2026-12-27', true], ['2026-12-30', true], ['2026-12-31', false], ['2026-12-26', false]].forEach(([iso, inside]) => {
    const day = p.info(ms(iso));
    assert.equal(day.sal, inside, iso);
    assert.equal(day.parts.some(([name]) => name === 'رواتب الدولة'), inside, iso);
  });
});

test('send times come an hour before the peaks measured in the data', () => {
  const p = planner('2026-11-19');
  assert.equal(p.peaks.other, 17);                    // 17:00 is the busiest hour of the year
  assert.deepEqual(p.sendTimes(p.info(ms('2027-03-05'))), [hourLabel(p.peaks.ramSuhoor - 1), hourLabel(p.peaks.ramIftar - 1)]);
  assert.deepEqual(p.sendTimes(p.info(ms('2026-12-04'))), [hourLabel(p.peaks.friday - 1)]);   // an ordinary Friday
  assert.deepEqual(p.sendTimes(p.info(ms('2026-12-14'))), ['16:00']);                         // an ordinary Monday
});

test('?today=YYYY-MM-DD freezes the date, anything else falls back to the real day', () => {
  const now = new Date(2030, 4, 6);
  assert.equal(core.parseToday('?today=2026-11-19', now), ms('2026-11-19'));
  assert.equal(core.parseToday('?today=nonsense', now), Date.UTC(2030, 4, 6));
  assert.equal(core.parseToday('', now), Date.UTC(2030, 4, 6));
});

test('the two views: around Ramadan, and the next 12 months', () => {
  const { views } = planner('2026-11-19');
  assert.equal(new Date(views.year.from).toISOString().slice(0, 10), '2026-11-01');
  assert.equal(new Date(views.year.to).toISOString().slice(0, 10), '2027-10-31');
  assert.ok(views.ram.from < views.ram.to);
});
