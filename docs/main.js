/* ── Index: animated dot-grid background ──
   Flat full-viewport heightfield of dots, gently domed outward, rippling as two
   slow sine waves. The cursor locally disrupts the waves and they ease back. */
(function () {
  if (document.body.dataset.page !== 'index') return;
  var cv = document.getElementById('dotfield');
  if (!cv) return;
  var ctx = cv.getContext('2d');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var t = 0, raf = 0, inside = false, hover = 0, px = -9999, py = -9999;

  function resize() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    cv.width = window.innerWidth * dpr;
    cv.height = window.innerHeight * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    cv._w = window.innerWidth; cv._h = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);
  window.addEventListener('pointermove', function (e) { px = e.clientX; py = e.clientY; inside = true; });
  window.addEventListener('pointerleave', function () { inside = false; });

  var gap = 30;
  function draw() {
    var W = cv._w, H = cv._h;
    ctx.clearRect(0, 0, W, H);
    hover += ((inside ? 1 : 0) - hover) * 0.07;
    var light = document.documentElement.getAttribute('data-theme') === 'light' ||
      (!document.documentElement.getAttribute('data-theme') &&
        window.matchMedia('(prefers-color-scheme: light)').matches);
    var col = light ? '99,102,241' : '171,184,252';
    var cx = W / 2, cy = H / 2;
    var cols = Math.ceil(W / gap) + 4, rows = Math.ceil(H / gap) + 4;
    var ox = (W - (cols - 1) * gap) / 2, oy = (H - (rows - 1) * gap) / 2;
    var R2 = 2 * 72 * 72;
    for (var j = 0; j < rows; j++) {
      for (var i = 0; i < cols; i++) {
        var gx = ox + i * gap, gy = oy + j * gap;
        var nx = (gx - cx) / cx, ny = (gy - cy) / cy, r2 = nx * nx + ny * ny;
        var curve = 1 - 0.11 * r2;
        var x = cx + (gx - cx) * curve, y = cy + (gy - cy) * curve;
        y += Math.sin(gx * 0.017 + gy * 0.011 + t * 0.9) * 4.4 +
             Math.sin(gx * 0.009 - gy * 0.02 + t * 0.6) * 3.0;
        if (hover > 0.004) {
          var dx = x - px, dy = y - py, d2 = dx * dx + dy * dy, infl = Math.exp(-d2 / R2);
          if (infl > 0.006) {
            var dist = Math.sqrt(d2) + 0.001;
            var ripple = Math.sin(dist * 0.12 - t * 3.4);
            var push = hover * infl * (7 + 4 * ripple);
            x += dx / dist * push; y += dy / dist * push;
          }
        }
        var a = (light ? 0.6 : 0.5) * (1 - 0.72 * r2);
        if (a <= 0.02) continue;
        var rad = Math.max(0.5, 1.8 * curve);
        ctx.beginPath();
        ctx.arc(x, y, rad, 0, 6.2832);
        ctx.fillStyle = 'rgba(' + col + ',' + a.toFixed(3) + ')';
        ctx.fill();
      }
    }
    t += 0.012;
    if (!reduce) raf = requestAnimationFrame(draw);
  }
  if (reduce) { t = 3.2; draw(); } else { draw(); }
})();


/* ── TOC drawer (mobile) ── */
(function () {
  var toggle = document.getElementById('toc-toggle');
  var toc = document.querySelector('.post-toc');
  if (!toggle || !toc) return;

  var backdrop = document.createElement('div');
  backdrop.style.cssText =
    'position:fixed;inset:0;z-index:39;background:rgba(0,0,0,0.4);' +
    'opacity:0;pointer-events:none;transition:opacity 0.25s ease';
  document.body.appendChild(backdrop);

  function open() {
    toc.classList.add('is-open');
    backdrop.style.opacity = '1';
    backdrop.style.pointerEvents = 'auto';
    toggle.setAttribute('aria-expanded', 'true');
  }

  function close() {
    toc.classList.remove('is-open');
    backdrop.style.opacity = '0';
    backdrop.style.pointerEvents = 'none';
    toggle.setAttribute('aria-expanded', 'false');
  }

  toggle.addEventListener('click', function () {
    toc.classList.contains('is-open') ? close() : open();
  });
  backdrop.addEventListener('click', close);
})();

/* ── Mobile nav hamburger ── */
(function () {
  var btn = document.getElementById('nav-menu-btn');
  var links = document.querySelector('nav.site-nav .nav-links');
  if (!btn || !links) return;
  btn.addEventListener('click', function () {
    var open = links.classList.toggle('is-open');
    btn.classList.toggle('is-open', open);
    btn.setAttribute('aria-expanded', open);
  });
  document.addEventListener('click', function (e) {
    if (!btn.contains(e.target) && !links.contains(e.target)) {
      links.classList.remove('is-open');
      btn.classList.remove('is-open');
      btn.setAttribute('aria-expanded', 'false');
    }
  });
})();

/* ── Theme toggle ── */
(function () {
  var btn = document.getElementById('theme-toggle');
  if (btn) {
    function _theme() {
      return document.documentElement.getAttribute('data-theme') ||
        (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    }
    btn.addEventListener('click', function () {
      var next = _theme() === 'light' ? 'dark' : 'light';
      document.documentElement.classList.add('theme-transitioning');
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      setTimeout(function () { document.documentElement.classList.remove('theme-transitioning'); }, 400);
    });
  }
})();

/* ── TOC scroll spy ── */
(function () {
  var headings = Array.from(document.querySelectorAll('.post-body h1, .post-body h2, .post-body h3, .post-body h4'));
  if (!headings.length) return;
  var links = {};
  document.querySelectorAll('.toc-inner a').forEach(function (a) {
    links[decodeURIComponent(a.getAttribute('href').slice(1))] = a;
  });
  var cur = null;
  function update() {
    var cut = window.scrollY + 112;
    var next = null;
    for (var i = 0; i < headings.length; i++) {
      if (headings[i].getBoundingClientRect().top + window.scrollY <= cut) next = headings[i].id;
    }
    if (next === cur) return;
    if (links[cur]) links[cur].classList.remove('toc-active');
    cur = next;
    if (links[cur]) links[cur].classList.add('toc-active');
  }
  window.addEventListener('scroll', update, { passive: true });
  update();
})();
