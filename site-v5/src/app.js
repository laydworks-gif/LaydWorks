/* ==========================================================================
   НАЛАШТУВАННЯ СТУДІЇ — редагуйте тут
   ========================================================================== */
const CONFIG = {
  // Заявки йдуть на локальний сервер (serve.py), а він передає їх майстру в Telegram.
  // Токен бота зберігається тільки на сервері (telegram_token.txt), у сторінку він не потрапляє.
  ORDER_ENDPOINT: '/api/order',
  CLASSES: { sedan: 'Седан / хетчбек', cross: 'Кросовер', suv: 'Великий SUV / бус' },
  // Цін на сайті немає: їх називає майстер після перегляду фото.
  SERVICES: [
    { id: 'polish',  title: 'Полірування кузова',  text: 'Прибираємо подряпини й павутинки з лаку' },
    { id: 'ceramic', title: 'Кераміка',            text: 'Захисне покриття лаку, також алькантари' },
    { id: 'clean',   title: 'Хімчистка',           text: 'Глибоке очищення салону, озонація від запахів' },
    { id: 'lights',  title: 'Полірування фар',     text: 'Повертаємо прозорість і світловий потік' },
    { id: 'ppf',     title: 'Антигравійна плівка', text: '' },
    { id: 'advice',  title: 'Потрібна порада',     text: 'Не знаю, що потрібно. Підкаже майстер' }
  ],
  MAPS_URL: 'https://www.google.com/maps/search/?api=1&query=%D0%94%D0%B5%D1%82%D0%B5%D0%B9%D0%BB%D1%96%D0%BD%D0%B3+%D1%86%D0%B5%D0%BD%D1%82%D1%80+AutoPolish+%D0%B2%D1%83%D0%BB.+%D0%A1%D1%82%D0%B0%D1%80%D0%B0+%D0%9F%D1%80%D0%B8%D1%81%D1%82%D0%B0%D0%BD%D1%8C+6+%D0%94%D0%BD%D1%96%D0%BF%D1%80%D0%BE',
  REVIEWS: [
    { name: 'Margo',   when: 'листопад 2026', text: 'Робила у хлопців кераміку на алькантару та повну мийку, залишилась задоволена' },
    { name: 'Anton',   when: '2025', text: 'Замовляв полірування, кераміку, хімчистку, фарбування керма … та ще усілякі детейлінгові дрібнички, типу плівка під ручками та ін. Результати перевищили очікування!' },
    { name: 'Роман',   when: '2025', text: 'Робили полірування Фул-лед фар головного світла на робочому авто Шкода А8. Був приємно здивований не тільки візуально, а збільшенню світлового потоку фар!' },
    { name: 'Віталій', when: '2024', text: 'Авто блищить як зірочка. Відновили фари, відполірували кузов, перекрасили поріг … Все швидко і якісно, постійно були на звʼязку, уважні до дрібниць, Гарні ціни.' }
  ],
  STREET: 'вул. Стара Пристань, 6, Дніпро',
  MAX_PHOTOS: 10
};

(function () {
  var tz = 'Europe/Kyiv';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return [].slice.call((r || document).querySelectorAll(s)); };
  var fD = new Intl.DateTimeFormat('uk-UA', { timeZone: 'UTC', weekday: 'short', day: 'numeric', month: 'long' });
  var STREET = CONFIG.STREET;
  var todayKyiv = new Intl.DateTimeFormat('en-CA', { timeZone: tz }).format(new Date());

  function dateLabel(v) { return v ? fD.format(new Date(v + 'T12:00:00Z')) : 'якнайшвидше'; }
  function el(tag, attrs, text) { var e = document.createElement(tag); for (var k in (attrs || {})) e.setAttribute(k, attrs[k]); if (text != null) e.textContent = text; return e; }

  /* ---------- hours + open now ---------- */
  try {
    var p = new Intl.DateTimeFormat('en-GB', { timeZone: tz, weekday: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(new Date());
    var g = function (t) { return p.filter(function (x) { return x.type === t; })[0].value; };
    var wd = g('weekday'), m = (+g('hour')) * 60 + (+g('minute'));
    var work = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].indexOf(wd) > -1, open = work && m >= 600 && m < 1080, msg;
    if (open) msg = 'Відчинено до 18:00';
    else if (work && m < 600) msg = 'Зачинено, відчинимось сьогодні о 10:00';
    else if (wd === 'Fri' || wd === 'Sat' || wd === 'Sun') msg = 'Зачинено, відчинимось у понеділок о 10:00';
    else msg = 'Зачинено, відчинимось завтра о 10:00';
    $$('[data-openst]').forEach(function (st) { st.setAttribute('data-open', open ? '1' : '0'); st.lastElementChild.textContent = msg; });
  } catch (e) {}
  // рядки графіка вже є в HTML (їх бачать і пошукові боти); тут лише підсвічуємо сьогоднішній день
  if (typeof wd !== 'undefined') $$('#hours tr').forEach(function (tr) { if (tr.getAttribute('data-d') === wd) tr.setAttribute('aria-current', 'date'); });

  /* ---------- reviews ---------- */
  CONFIG.REVIEWS.forEach(function (r) {
    var fig = el('figure'), a = el('a', { 'class': 'rv', href: CONFIG.MAPS_URL, target: '_blank', rel: 'noopener', 'aria-label': 'Відгук від ' + r.name + ' на Google Maps, відкриється в новій вкладці' });
    var cap = el('figcaption'); cap.append(el('b', null, r.name), document.createTextNode(' · Google Maps, ' + r.when));
    a.append(el('blockquote', null, '«' + r.text + '»'), cap); fig.append(a); $('#quotes').append(fig);
  });

  /* ---------- booking wizard ---------- */
  var N = 4, step = 1, photos = [], maxStep = 1;
  var wiz = $('#book'), form = $('#bf'), steps = $$('.wstep'), back = $('#w-back'), nextBtn = $('#w-next');
  var tick = '<svg viewBox="0 0 24 24" fill="none" stroke="#F1F2EF" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5L20 7"/></svg>';
  var radio = function (n) { return ($('input[name="' + n + '"]:checked', form) || {}).value || ''; };
  CONFIG.SERVICES.forEach(function (s, i) {
    var lab = el('label', { 'class': 'opt' }), inp = el('input', { type: 'checkbox', value: s.id, name: 'svc' });
    var box = el('span', { 'class': 'box', 'aria-hidden': 'true' }); box.innerHTML = tick;
    var tx = el('span'); tx.append(el('strong', null, s.title));
    lab.append(inp, box, tx); $('#rows').append(lab);
    inp.addEventListener('change', function () { setErr('svc', ''); });
  });
  function selected() { var ids = $$('input[name="svc"]:checked', form).map(function (i) { return i.value; }); return CONFIG.SERVICES.filter(function (s) { return ids.indexOf(s.id) > -1; }); }

  // working-day chips (Kyiv): "якнайшвидше" + next 5 working days
  (function () {
    var box = $('#days'), DW = ['Нд', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
    var add = function (val, a, b, on) {
      var l = el('label', { 'class': 'chip' }), i = el('input', { type: 'radio', name: 'date', value: val }); if (on) i.checked = true;
      var sp = el('span'); sp.append(document.createTextNode(a)); if (b) sp.append(el('small', null, b)); l.append(i, sp); box.append(l);
    };
    add('', 'Якнайшвидше', 'перший вільний', true);
    var d = new Date(todayKyiv + 'T12:00:00Z'), minutes = 0;
    try { var pp = new Intl.DateTimeFormat('en-GB', { timeZone: tz, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(new Date()); minutes = (+pp[0].value) * 60 + (+pp[2].value); } catch (e) {}
    var isWork = function (x) { var w = x.getUTCDay(); return w > 0 && w < 6; };
    var n = 0, day0 = true;
    while (n < 5) {
      if (isWork(d) && !(day0 && minutes >= 960)) {
        var iso = d.toISOString().slice(0, 10), dd = String(d.getUTCDate()).padStart(2, '0') + '.' + String(d.getUTCMonth() + 1).padStart(2, '0');
        add(iso, day0 ? 'Сьогодні' : DW[d.getUTCDay()], dd, false); n++;
      }
      d.setUTCDate(d.getUTCDate() + 1); day0 = false;
    }
  })();

  /* photos */
  var drop = $('#drop'), file = $('#file');
  function scaled(im, max) {
    var k = Math.min(1, max / Math.max(im.naturalWidth, im.naturalHeight)), c = document.createElement('canvas');
    c.width = Math.round(im.naturalWidth * k); c.height = Math.round(im.naturalHeight * k);
    c.getContext('2d').drawImage(im, 0, 0, c.width, c.height); return c;
  }
  function processFile(f) {
    return new Promise(function (res, rej) {
      if (!/^image\//.test(f.type)) return rej(new Error('type'));
      var url = URL.createObjectURL(f), im = new Image();
      im.onload = function () {
        var big = scaled(im, 1600);
        URL.revokeObjectURL(url);
        big.toBlob(function (b) { b ? res({ blob: b, url: URL.createObjectURL(b) }) : rej(new Error('blob')); }, 'image/jpeg', 0.82);
      };
      im.onerror = function () { URL.revokeObjectURL(url); rej(new Error('decode')); };
      im.src = url;
    });
  }
  async function addFiles(list) {
    var files = [].slice.call(list), msg = '', room = CONFIG.MAX_PHOTOS - photos.length, bad = 0;
    if (files.length > room) { msg = 'Можна додати до ' + CONFIG.MAX_PHOTOS + ' фото, зайві пропущено. '; files = files.slice(0, Math.max(0, room)); }
    for (var i = 0; i < files.length; i++) { try { photos.push(await processFile(files[i])); } catch (e) { bad++; } }
    if (bad) msg += 'Не вдалося відкрити файлів: ' + bad + '. Підійдуть JPG або PNG. ';
    renderThumbs(msg);
  }
  function renderThumbs(msg) {
    var ul = $('#thumbs'); ul.textContent = '';
    photos.forEach(function (p, i) {
      var li = el('li'), img = el('img', { alt: 'Додане фото ' + (i + 1), width: '72', height: '72' }); img.src = p.url;
      var b = el('button', { type: 'button', 'aria-label': 'Видалити фото ' + (i + 1) }, '×');
      b.addEventListener('click', function () { URL.revokeObjectURL(p.url); photos.splice(i, 1); renderThumbs(''); });
      li.append(img, b); ul.append(li);
    });
    $('#ph-count').textContent = (msg || '') + (photos.length ? 'Додано фото: ' + photos.length + ' з ' + CONFIG.MAX_PHOTOS : '');
  }
  file.addEventListener('change', function () { addFiles(file.files); file.value = ''; });
  ['dragenter', 'dragover'].forEach(function (t) { drop.addEventListener(t, function (e) { e.preventDefault(); drop.classList.add('is-over'); }); });
  ['dragleave', 'drop'].forEach(function (t) { drop.addEventListener(t, function (e) { e.preventDefault(); drop.classList.remove('is-over'); }); });
  drop.addEventListener('drop', function (e) { if (e.dataTransfer && e.dataTransfer.files.length) addFiles(e.dataTransfer.files); });
  window.addEventListener('dragover', function (e) { e.preventDefault(); });
  window.addEventListener('drop', function (e) { e.preventDefault(); });

  /* validation */
  var f = { name: $('#f-name'), phone: $('#f-phone'), car: $('#f-car') };
  function setErr(key, msg) {
    $('#e-' + key).textContent = msg || '';
    if (f[key]) { if (msg) f[key].setAttribute('aria-invalid', 'true'); else f[key].removeAttribute('aria-invalid'); }
    return !msg;
  }
  Object.keys(f).forEach(function (k) { f[k].addEventListener('input', function () { setErr(k, ''); status(''); }); });
  function check(n) {
    if (n === 1) { if (selected().length) return null; setErr('svc', 'Оберіть хоча б одну послугу.'); return $('input[name="svc"]', form); }
    if (n === 2) { return setErr('car', f.car.value.trim().length >= 2 ? '' : 'Вкажіть марку й модель авто.') ? null : f.car; }
    if (n === 4) {
      var bad = null;
      if (!setErr('name', f.name.value.trim().length >= 2 ? '' : 'Вкажіть, як до вас звертатися.')) bad = bad || f.name;
      var d = f.phone.value.replace(/\D/g, '');
      if (!setErr('phone', d.length >= 10 && d.length <= 13 ? '' : 'Номер повністю, наприклад +380 50 123 45 67.')) bad = bad || f.phone;
      return bad;
    }
    return null;
  }
  var status = function (msg) { $('#status').textContent = msg || ''; };

  /* navigation */
  function recap() {
    var sel = selected(), parts = [sel.map(function (s) { return s.title; }).join(', ')];
    parts.push((f.car.value.trim() || 'авто') + ' (' + CONFIG.CLASSES[radio('cls')] + ')');
    parts.push(dateLabel(radio('date')) + ', ' + radio('time'));
    if (photos.length) parts.push('фото: ' + photos.length);
    $('#recap').textContent = parts.join(' · ');
  }
  function go(n, focus) {
    step = n; maxStep = Math.max(maxStep, n);
    steps.forEach(function (s, i) { s.hidden = i !== n - 1; });
    $$('#wsteps li').forEach(function (li, i) { li.classList.toggle('is-cur', i === n - 1); li.classList.toggle('is-done', i < n - 1); var b = $('button', li); if (i === n - 1) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current'); });
    back.hidden = n === 1; nextBtn.textContent = n === N ? 'Надіслати заявку' : 'Далі';
    if (n === N) recap();
    status('');
    if (focus) {
      var h = $('h2', steps[n - 1]); h.focus({ preventScroll: true });
      var r = wiz.getBoundingClientRect(); if (r.top < 0 || r.top > innerHeight * 0.4) wiz.scrollIntoView({ block: 'start' });
    }
  }
  function tryGo(target) {
    if (target === step) return;
    if (target < step) return go(target, true);
    for (var s = step; s < target; s++) { var bad = check(s); if (bad) { if (s !== step) go(s, false); bad.focus(); return; } }
    go(target, true);
  }
  $$('#wsteps button').forEach(function (b) { b.addEventListener('click', function () { tryGo(+b.dataset.go); }); });
  back.addEventListener('click', function () { go(step - 1, true); });
  form.addEventListener('keydown', function (e) { if (e.key === 'Enter' && e.target.tagName === 'INPUT' && e.target.type !== 'file' && e.target.type !== 'checkbox' && e.target.type !== 'radio') { /* handled by submit */ } });

  /* Відправка заявки: сторінка нічого не зберігає. Сервер (serve.py) одразу передає заявку майстру в Telegram,
     токен бота при цьому ніколи не потрапляє на сторінку. */
  function blobToData(b) { return new Promise(function (res) { var r = new FileReader(); r.onload = function () { res(r.result); }; r.readAsDataURL(b); }); }
  async function sendOrder() {
    var big = await Promise.all(photos.map(function (p) { return blobToData(p.blob); }));
    var res = await fetch(CONFIG.ORDER_ENDPOINT, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      name: f.name.value.trim(), phone: f.phone.value.trim(), via: radio('via'), car: f.car.value.trim(), cls: CONFIG.CLASSES[radio('cls')],
      svc: selected().map(function (s) { return s.title; }), when: dateLabel(radio('date')) + ' · ' + radio('time'),
      note: $('#f-note').value.trim(), photos: big,
      hp: ($('input[name="hp_url"]', form) || {}).value || '', t: Math.round(performance.now()) }) });
    var j = await res.json().catch(function () { return {}; });
    if (!res.ok || !j.ok) throw new Error(j.error || ('HTTP ' + res.status));
    return j.id || '';
  }
  form.addEventListener('submit', async function (e) {
    e.preventDefault(); status('');
    if (step < N) { var bad = check(step); if (bad) { bad.focus(); return; } go(step + 1, true); return; }
    for (var s = 1; s <= N; s++) { var b = check(s); if (b) { if (s !== step) go(s, true); b.focus(); return; } }
    nextBtn.disabled = true; nextBtn.textContent = 'Надсилання…';
    var id;
    try { id = await sendOrder(); }
    catch (err) {
      if (window.console) console.warn(err);
      nextBtn.disabled = false; nextBtn.textContent = 'Надіслати заявку';
      status('Не вдалося надіслати заявку. Зателефонуйте: +380 68 348 1031.'); return;
    }
    showDone(id);
  });
  function showDone(id) {
    var name = f.name.value.trim(), via = radio('via');
    wiz.textContent = '';
    var box = el('div', { 'class': 'done', role: 'status' });
    var h = el('h2', { tabindex: '-1' }, id ? 'Заявку ' + id + ' надіслано' : 'Заявку надіслано');
    box.append(h, el('p', null, 'Дякуємо, ' + name + '. Студія відповість вам: ' + via.toLowerCase() + '.'));
    var b = el('button', { type: 'button', 'class': 'btn btn--ghost' }, 'Нова заявка'); b.addEventListener('click', function () { location.reload(); });
    box.append(b); wiz.append(box); h.focus({ preventScroll: true }); wiz.scrollIntoView({ block: 'center' });
  }

  /* bottom dock (phones): visible only while the booking card is off screen */
  (function () {
    var bar = $('#bar'); if (!bar || !window.IntersectionObserver) { if (bar) bar.classList.add('is-on'); return; }
    var inView = false;
    new IntersectionObserver(function (en) { inView = en[0].isIntersecting; bar.classList.toggle('is-on', !inView); }, { threshold: 0.15 }).observe(wiz);
  })();

  go(1, false);

  /* ---------- lightbox (site gallery + owner panel photos) ---------- */
  var lb = $('#lb'), lbList = [], lbI = 0, lbFocus = null;
  function lbShow(i) {
    lbI = (i + lbList.length) % lbList.length; var it = lbList[lbI];
    $('#lb-img').src = it.src; $('#lb-img').alt = it.alt || '';
    $('#lb-cap').textContent = (it.cap || '') + (lbList.length > 1 ? (it.cap ? ' · ' : '') + (lbI + 1) + ' / ' + lbList.length : '');
  }
  function openLb(src, alt, cap, list, idx) {
    lbFocus = document.activeElement; lbList = list || [{ src: src, alt: alt, cap: cap }];
    lb.classList.toggle('single', lbList.length < 2); lbShow(idx || 0); lb.hidden = false; document.body.style.overflow = 'hidden'; $('#lb-x').focus();
  }
  function closeLb() { lb.hidden = true; document.body.style.overflow = ''; $('#lb-img').removeAttribute('src'); if (lbFocus && lbFocus.focus) lbFocus.focus(); }
  $('#lb-x').addEventListener('click', closeLb);
  $('#lb-prev').addEventListener('click', function () { lbShow(lbI - 1); });
  $('#lb-next').addEventListener('click', function () { lbShow(lbI + 1); });
  lb.addEventListener('click', function (e) { if (e.target === lb || e.target.tagName === 'FIGURE') closeLb(); });
  document.addEventListener('keydown', function (e) {
    if (lb.hidden) return;
    if (e.key === 'Escape') closeLb();
    else if (lbList.length > 1 && e.key === 'ArrowRight') lbShow(lbI + 1);
    else if (lbList.length > 1 && e.key === 'ArrowLeft') lbShow(lbI - 1);
    else if (e.key === 'Tab') { var b = $$('button', lb).filter(function (x) { return x.offsetParent !== null && getComputedStyle(x).visibility !== 'hidden'; }), i = b.indexOf(document.activeElement); e.preventDefault(); b[(i + (e.shiftKey ? -1 : 1) + b.length) % b.length].focus(); }
  });
  var lsx = null;
  lb.addEventListener('pointerdown', function (e) { lsx = e.clientX; });
  lb.addEventListener('pointerup', function (e) { if (lsx != null && lbList.length > 1 && Math.abs(e.clientX - lsx) > 60) lbShow(lbI + (e.clientX < lsx ? 1 : -1)); lsx = null; });

  /* ---------- reel: drag, momentum, snap, rubber band, spring ---------- */
  var reel = $('[data-reel]');
  // фото каруселі вантажаться відкладено (loading=lazy), а коли секція наближається до екрана — підтягуємо всі,
  // щоб слайди за межею видимості не з’являлися з затримкою під час гортання
  (function () {
    var imgs = $$('img', reel), go = function () { imgs.forEach(function (i) { i.loading = 'eager'; }); };
    if (!window.IntersectionObserver) { go(); return; }
    new IntersectionObserver(function (en, o) { if (en[0].isIntersecting) { go(); o.disconnect(); } }, { rootMargin: '400px 0px' }).observe(reel);
  })();
  var gallery = $$('.reel__slide', reel).map(function (s) { var im = $('img', s); return { src: im.getAttribute('src'), alt: im.alt, cap: $('figcaption', s).textContent }; });
  (function () {
    var view = $('.reel__view', reel), track = $('.reel__track', reel), slides = $$('.reel__slide', reel), thumb = $('.reel__thumb', reel), bar = $('.reel__bar', reel);
    var prev = $('[data-prev]'), next = $('[data-next]'), mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    var x = 0, min = 0, snaps = [0], raf = 0, dragging = false, moved = false, sx = 0, spos = 0, samples = [], settleT = 0, tapIdx = -1;
    reel.classList.add('js'); view.scrollLeft = 0;
    function measure() {
      var padL = parseFloat(getComputedStyle(track).paddingLeft) || 0, vw = view.clientWidth, tw = track.scrollWidth;
      min = Math.min(0, vw - tw);
      snaps = slides.map(function (s) { return Math.max(min, -(s.offsetLeft - padL)); }).filter(function (v, i, a) { return a.indexOf(v) === i; });
      var bw = bar.clientWidth; thumb.style.width = Math.max(48, bw * Math.min(1, vw / tw)) + 'px'; thumb._room = bw - thumb.offsetWidth;
    }
    function nearest(v) { var b = 0, d = 1e9; for (var i = 0; i < snaps.length; i++) { var k = Math.abs(snaps[i] - v); if (k < d) { d = k; b = i; } } return b; }
    function clamp(v) { return Math.max(min, Math.min(0, v)); }
    function render() {
      track.style.transform = 'translate3d(' + x + 'px,0,0)';
      var t = min === 0 ? 0 : Math.min(1, Math.max(0, x / min)); thumb.style.transform = 'translateX(' + (t * (thumb._room || 0)) + 'px)';
      var i = nearest(x); if (prev) prev.setAttribute('aria-disabled', i <= 0 ? 'true' : 'false'); if (next) next.setAttribute('aria-disabled', i >= snaps.length - 1 ? 'true' : 'false');
    }
    function rub(o, d) { return d * (1 - 1 / (o * 0.55 / d + 1)); }
    function band(v) { var d = view.clientWidth; if (v > 0) return rub(v, d); if (v < min) return min - rub(min - v, d); return v; }
    function stop() { cancelAnimationFrame(raf); raf = 0; }
    function springTo(target, v0) {
      stop(); if (mq.matches) { x = target; render(); return; }
      var k = 190, c = 2 * 0.92 * Math.sqrt(k), v = v0 || 0, last = performance.now();
      (function step(now) {
        var dt = Math.min(1 / 30, (now - last) / 1000); last = now;
        var a = -k * (x - target) - c * v; v += a * dt; x += v * dt;
        if (Math.abs(x - target) < 0.3 && Math.abs(v) < 8) { x = target; render(); raf = 0; return; }
        render(); raf = requestAnimationFrame(step);
      })(last);
    }
    function go(i) { springTo(snaps[Math.max(0, Math.min(snaps.length - 1, i))], 0); }
    view.addEventListener('pointerdown', function (e) {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      stop(); dragging = true; moved = false; sx = e.clientX; spos = x; samples = [{ t: e.timeStamp, x: e.clientX }];
      var s = e.target.closest ? e.target.closest('.reel__slide') : null; tapIdx = s ? slides.indexOf(s) : -1;
      try { view.setPointerCapture(e.pointerId); } catch (_) {}
    });
    view.addEventListener('pointermove', function (e) {
      if (!dragging) return; var dx = e.clientX - sx;
      if (!moved) { if (Math.abs(dx) < 5) return; moved = true; reel.classList.add('is-dragging'); }
      x = band(spos + dx); render(); samples.push({ t: e.timeStamp, x: e.clientX });
      while (samples.length > 2 && e.timeStamp - samples[0].t > 100) samples.shift();
    });
    function release(e) {
      if (!dragging) return; dragging = false; reel.classList.remove('is-dragging');
      try { view.releasePointerCapture(e.pointerId); } catch (_) {}
      if (!moved) { if (e.type === 'pointerup' && tapIdx > -1) openLb(null, null, null, gallery, tapIdx); return; }
      var a = samples[0], b = samples[samples.length - 1], v = 0; if (b.t > a.t) v = (b.x - a.x) / (b.t - a.t) * 1000;
      var rate = 0.998, proj = x + (v / 1000) * rate / (1 - rate);
      springTo(snaps[nearest(clamp(proj))], v);
    }
    view.addEventListener('pointerup', release); view.addEventListener('pointercancel', release);
    // keyboard activation of a slide (Enter/Space gives click with detail 0)
    slides.forEach(function (s, i) { $('.open', s).addEventListener('click', function (e) { if (e.detail === 0) openLb(null, null, null, gallery, i); }); });
    view.addEventListener('wheel', function (e) {
      if (Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return; e.preventDefault(); stop(); x = clamp(x - e.deltaX); render();
      clearTimeout(settleT); settleT = setTimeout(function () { springTo(snaps[nearest(x)], 0); }, 140);
    }, { passive: false });
    view.addEventListener('keydown', function (e) {
      if (e.target !== view) return; var i = nearest(x);
      if (e.key === 'ArrowRight') { e.preventDefault(); go(i + 1); } else if (e.key === 'ArrowLeft') { e.preventDefault(); go(i - 1); }
      else if (e.key === 'Home') { e.preventDefault(); go(0); } else if (e.key === 'End') { e.preventDefault(); go(snaps.length - 1); }
    });
    if (prev) prev.addEventListener('click', function () { go(nearest(x) - 1); }); if (next) next.addEventListener('click', function () { go(nearest(x) + 1); });
    measure(); render();
    if (window.ResizeObserver) new ResizeObserver(function () { measure(); x = clamp(x); render(); }).observe(view); else window.addEventListener('resize', function () { measure(); x = clamp(x); render(); });
    window.addEventListener('load', function () { measure(); render(); });
  })();
