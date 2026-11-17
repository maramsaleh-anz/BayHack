function drawAll() {
  Object.entries(charts).forEach(([id, fn]) => { const box = document.getElementById(id); if (box) fn(box); });
  firstDraw = false;
}

// Theme toggle
const btn = document.getElementById('themeBtn');
const isDark = () => document.documentElement.dataset.theme ? document.documentElement.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
const syncBtn = () => { btn.textContent = isDark() ? 'الوضع الفاتح' : 'الوضع الداكن'; };
try { const saved = localStorage.getItem('ehsan-theme'); if (saved) document.documentElement.dataset.theme = saved; } catch (e) {}
syncBtn();
btn.addEventListener('click', () => {
  const next = isDark() ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem('ehsan-theme', next); } catch (e) {}
  syncBtn();
});

// Active nav link
const links = [...document.querySelectorAll('.nav a')];
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => { if (e.isIntersecting) links.forEach((a) => a.classList.toggle('on', a.getAttribute('href') === '#' + e.target.id)); });
}, { rootMargin: '-40% 0px -55% 0px' });
document.querySelectorAll('main section[id]').forEach((s) => io.observe(s));

drawAll();
let lastW = innerWidth;
new ResizeObserver(() => { if (Math.abs(innerWidth - lastW) > 4) { lastW = innerWidth; drawAll(); } }).observe(document.body);
if (document.fonts && document.fonts.ready) document.fonts.ready.then(drawAll);
