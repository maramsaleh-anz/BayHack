/* Reminder-calendar logic: Hijri dates, payday windows, expected multipliers, send hours.
 *
 * Pure functions with no DOM and no d3, so the same file runs in the page and in Node (tests/js/planner-core.test.mjs).
 * Every number comes from the fitted model (model_results.csv) and the hourly profile of the data; nothing is typed by hand.
 * The rules mirror the Python analysis (bayyin/config.py): seasons by Hijri date, state salaries on the 27th shifted off
 * Friday/Saturday, window = payday + 3 days.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.PlannerCore = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const DAY = 86400000;
  const utc = (y, m, d) => Date.UTC(y, m, d);

  const FRIDAY = 5, SATURDAY = 6;                 // Date#getUTCDay (Sunday = 0)
  const SALARY_DAY = 27, PAYDAY_WINDOW_DAYS = 3;  // state salaries: 27th, window = payday + 3 days
  const CLEAR_EFFECTS = ['ارتفاع واضح', 'انخفاض واضح'];  // only effects the analysis confirmed are used
  const TIER_LIMITS = { peak: 3, high: 1.4, norm: 0.95 }; // multiplier thresholds of the colour tiers

  const LABELS = {
    season: { ram1: 'رمضان (1–20)', ram2: 'العشر الأواخر من رمضان', dhh: 'ذو الحجة 1–9 (مع عرفة)',
      eidf: 'عيد الفطر', eida: 'عيد الأضحى والتشريق', sal: 'رواتب الدولة (يوم الصرف + 3 أيام)' },
    tier: { peak: 'يوم ذروة', high: 'يوم مرتفع', norm: 'يوم عادي', low: 'يوم منخفض', eid: 'العيد' },
    action: { peak: 'أطلق الحملة وأرسل التذكير في هذا اليوم.', high: 'يستحق تذكيراً.', norm: 'لا حاجة لحملة خاصة.',
      low: 'أجّل الرسائل غير العاجلة.', eid: 'لا ارتفاع في البيانات، فلا تعتمد عليه.' },
    message: { eid: 'لا حملة خاصة', season: 'جذب متبرعين جدد', other: 'تذكير للمتبرعين السابقين' },
  };

  // ------------------------------------------------------------ dates
  /** Hijri date (Umm al-Qura, the calendar of the notebook's hijridate) of a UTC-midnight timestamp, or null if unsupported. */
  function createHijri() {
    let numeric, monthName;
    try {
      numeric = new Intl.DateTimeFormat('en-u-ca-islamic-umalqura-nu-latn', { day: 'numeric', month: 'numeric', year: 'numeric', timeZone: 'UTC' });
      monthName = new Intl.DateTimeFormat('ar-SA-u-ca-islamic-umalqura-nu-latn', { month: 'long', timeZone: 'UTC' });
    } catch (e) { return null; }
    const cache = new Map();
    const hijri = (ms) => {
      let h = cache.get(ms);
      if (!h) {
        const p = {};
        numeric.formatToParts(new Date(ms)).forEach((x) => { p[x.type] = +x.value; });
        h = { y: p.year, m: p.month, d: p.day, name: monthName.format(new Date(ms)) };
        cache.set(ms, h);
      }
      return h;
    };
    try { return hijri(utc(2026, 0, 1)).y > 1400 ? hijri : null; } catch (e) { return null; }
  }

  /** "Today" as a UTC-midnight timestamp. `?today=YYYY-MM-DD` in the URL freezes it (for demos and tests). */
  function parseToday(search, now) {
    const q = new URLSearchParams(search).get('today');
    const fromUrl = q && /^\d{4}-\d{2}-\d{2}$/.test(q) ? Date.parse(q + 'T00:00:00Z') : NaN;
    return Number.isFinite(fromUrl) ? fromUrl : utc(now.getFullYear(), now.getMonth(), now.getDate());
  }

  /** First day (1 Ramadan) of the Ramadan that is running now or comes next. */
  function findRamadanStart(hijri, todayMs) {
    for (let i = -30; i < 420; i++) {
      const ms = todayMs + i * DAY, h = hijri(ms);
      if (h.m === 9 && h.d === 1) return ms;
    }
    return null;
  }

  // ------------------------------------------------------------ rules
  /** Season of a Hijri date: ram1 (1-20), ram2 (last 10), dhh (Dhu al-Hijjah 1-9), eidf, eida, or null. */
  function seasonOf(h) {
    if (h.m === 9) return h.d >= 21 ? 'ram2' : 'ram1';
    if (h.m === 12 && h.d <= 9) return 'dhh';
    if (h.m === 10 && h.d <= 3) return 'eidf';
    if (h.m === 12 && h.d >= 10 && h.d <= 13) return 'eida';
    return null;
  }

  /** Payday of state salaries for a month (month 0-11): the 27th, moved to Thursday if Friday, to Sunday if Saturday. */
  function salaryPayday(year, month) {
    let pay = utc(year, month, SALARY_DAY);
    const dow = new Date(pay).getUTCDay();
    if (dow === FRIDAY) pay -= DAY; else if (dow === SATURDAY) pay += DAY;
    return pay;
  }

  /** Every day inside a salary window (payday + 3 days) from 3 months before to 17 months after `todayMs`. */
  function salaryWindowDays(todayMs) {
    const ref = new Date(todayMs), days = new Set();
    for (let k = -3; k <= 17; k++) {
      const pay = salaryPayday(ref.getUTCFullYear(), ref.getUTCMonth() + k);
      for (let i = 0; i <= PAYDAY_WINDOW_DAYS; i++) days.add(pay + i * DAY);
    }
    return days;
  }

  /** Multiplier of every clear effect in the model, as 1 + change%/100 (1 when the effect is not clear). */
  function effectsFrom(model) {
    const effect = (key) => {
      const r = model.find((x) => x.key === key);
      return r && CLEAR_EFFECTS.includes(r.conclusion) ? 1 + r.c / 100 : 1;
    };
    return { ram1: effect('ramadan_1_20'), ram2: effect('ramadan_last10'), dhh: effect('dhul_hijjah_1_9'),
      fri: effect('friday'), sat: effect('saturday'), sal: effect('salary_27') };
  }

  /** Peak hours measured in the data: iftar and suhoor in Ramadan, overall, and on Friday. */
  function peakHours(hourly, weekdayHours) {
    const peak = (rows, value, lo, hi) => rows.filter((r) => r.h >= lo && r.h <= hi).reduce((a, b) => (value(b) > value(a) ? b : a)).h;
    return {
      ramIftar: peak(hourly, (r) => r.rd, 12, 20),
      ramSuhoor: peak(hourly, (r) => r.rd, 0, 6),
      other: peak(hourly, (r) => r.os, 0, 23),
      friday: peak(weekdayHours.filter((r) => r.wd === 'الجمعة'), (r) => r.donations, 0, 23),
    };
  }

  // ------------------------------------------------------------ the planner
  /**
   * @param {object} o
   * @param {Array}  o.model        rows of model_results.csv ({key, c, conclusion, ...})
   * @param {Array}  o.hourly       rows {h, rd, os, ...}
   * @param {Array}  o.weekdayHours rows {wd, h, donations, ...}
   * @param {number} o.todayMs      UTC-midnight timestamp
   * @param {Function} o.hijri      from createHijri()
   * @param {Function} o.hourLabel  hour number -> "HH:00"
   */
  function createPlanner({ model, hourly, weekdayHours, todayMs, hijri, hourLabel }) {
    const FX = effectsFrom(model);
    const salaryDays = salaryWindowDays(todayMs);
    const peaks = peakHours(hourly, weekdayHours);
    const oneHourBefore = (h) => hourLabel((h + 23) % 24);   // send an hour before the peak
    const ramStart = findRamadanStart(hijri, todayMs);
    const t = new Date(todayMs);

    /** Everything about one day: Hijri date, season, the factors that apply, the multiplier and its tier. */
    function info(ms) {
      const dow = new Date(ms).getUTCDay(), h = hijri(ms), s = seasonOf(h);
      const parts = []; let m = 1;
      if (s === 'ram1' || s === 'ram2' || s === 'dhh') { parts.push([LABELS.season[s], FX[s]]); m *= FX[s]; }
      if (dow === FRIDAY && FX.fri !== 1) { parts.push(['الجمعة', FX.fri]); m *= FX.fri; }
      if (dow === SATURDAY && FX.sat !== 1) { parts.push(['السبت', FX.sat]); m *= FX.sat; }
      const sal = salaryDays.has(ms);
      if (sal && FX.sal !== 1) { parts.push(['رواتب الدولة', FX.sal]); m *= FX.sal; }
      const eid = s === 'eidf' || s === 'eida';
      const tier = eid ? 'eid' : m >= TIER_LIMITS.peak ? 'peak' : m >= TIER_LIMITS.high ? 'high' : m >= TIER_LIMITS.norm ? 'norm' : 'low';
      return { ms, dow, h, s, parts, m, tier, eid, sal, wkey: s || (sal ? 'sal' : null) };
    }

    /** Suggested send times for a day (an hour before each peak), or null on Eid. */
    function sendTimes(i) {
      if (i.eid) return null;
      if (i.s === 'ram1' || i.s === 'ram2') return [oneHourBefore(peaks.ramSuhoor), oneHourBefore(peaks.ramIftar)];
      if (i.dow === FRIDAY) return [oneHourBefore(peaks.friday)];
      return [oneHourBefore(peaks.other)];
    }

    /** Suggested kind of message: season -> attract new donors (the season raises how many give, not how much). */
    function messageType(i) {
      if (i.eid) return LABELS.message.eid;
      return i.s === 'ram1' || i.s === 'ram2' || i.s === 'dhh' ? LABELS.message.season : LABELS.message.other;
    }

    return {
      todayMs, hijri, FX, peaks, ramStart, ramYear: hijri(ramStart).y,
      fridaySendTime: oneHourBefore(peaks.friday),
      // the two views of the calendar: around the next Ramadan, and the next 12 months
      views: {
        ram: { from: ramStart - 7 * DAY, to: ramStart + 34 * DAY },
        year: { from: utc(t.getUTCFullYear(), t.getUTCMonth(), 1), to: utc(t.getUTCFullYear(), t.getUTCMonth() + 12, 0) },
      },
      info, sendTimes, messageType,
    };
  }

  // ------------------------------------------------------------ reminder budget
  /**
   * The best `perMonth` days of every Gregorian month (highest multiplier first, earlier day on ties), never on Eid.
   * @param {Array} days  results of planner.info() for the days that can still be used
   * @returns {Set<number>} the chosen timestamps
   */
  function pickDays(days, perMonth) {
    const byMonth = new Map();
    days.filter((i) => !i.eid).forEach((i) => {
      const d = new Date(i.ms), key = d.getUTCFullYear() * 12 + d.getUTCMonth();
      if (!byMonth.has(key)) byMonth.set(key, []);
      byMonth.get(key).push(i);
    });
    const picked = new Set();
    byMonth.forEach((list) => list.slice().sort((a, b) => b.m - a.m || a.ms - b.ms).slice(0, perMonth).forEach((i) => picked.add(i.ms)));
    return picked;
  }

  /** Mean multiplier of the chosen days, of all usable days, and how many times better the chosen days are. */
  function budgetGain(days, picked) {
    const usable = days.filter((i) => !i.eid);
    const mean = (list) => list.reduce((a, i) => a + i.m, 0) / list.length;
    const chosen = usable.filter((i) => picked.has(i.ms));
    if (!chosen.length) return null;
    const pickedMean = mean(chosen), allMean = mean(usable);
    return { pickedMean, allMean, gain: pickedMean / allMean, count: chosen.length };
  }

  return { DAY, utc, LABELS, pickDays, budgetGain, createHijri, parseToday, findRamadanStart, seasonOf, salaryPayday, salaryWindowDays,
    effectsFrom, peakHours, createPlanner };
}));
