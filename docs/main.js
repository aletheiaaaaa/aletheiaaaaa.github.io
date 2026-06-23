/* ── Index: hero title typewriter ── */
(function () {
  if (document.body.dataset.page !== 'index') return;
  var heroType = document.querySelector('.hero-type');
  if (!heroType) return;
  var full = heroType.textContent;
  heroType.textContent = '';
  var i = 0;
  function typeNext() {
    if (i < full.length) { heroType.textContent = full.slice(0, ++i); setTimeout(typeNext, 80); }
  }
  setTimeout(typeNext, 200);
})();

/* ── Index: whole-page letter descramble ── */
(function () {
  if (document.body.dataset.page !== 'index') return;
  var main = document.querySelector('main');
  if (!main) return;

  /* Character set for scrambling. NOTE: '$' is intentionally excluded so it
     never collides with MathJax's inline-math delimiters. */
  var CHARS = '!<>-_\\/[]{}=+*^?#&@abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  function rand() { return CHARS.charAt(Math.floor(Math.random() * CHARS.length)); }

  var DURATION = 1500; // ms — the whole page descrambles within this window

  /* Collect every visible text node in <main>, skipping the hero title
     (which has its own typewriter effect) and whitespace-only nodes. */
  var walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT, {
    acceptNode: function (node) {
      if (!node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
      if (node.parentElement && node.parentElement.closest('.hero-type'))
        return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  });

  var nodes = [];
  for (var n = walker.nextNode(); n; n = walker.nextNode()) {
    var full = n.nodeValue;
    // Per-character resolve time: random across the window so the page
    // descrambles as a whole rather than left-to-right.
    var resolveAt = new Array(full.length);
    for (var c = 0; c < full.length; c++) resolveAt[c] = Math.random() * DURATION;
    nodes.push({ node: n, full: full, resolveAt: resolveAt });
  }
  if (!nodes.length) return;

  var start = null;
  function tick(now) {
    if (start === null) start = now;
    var elapsed = now - start;
    var done = elapsed >= DURATION;
    for (var i = 0; i < nodes.length; i++) {
      var item = nodes[i];
      if (item.locked) continue;
      var full = item.full, out = '', allDone = true;
      for (var c = 0; c < full.length; c++) {
        var ch = full[c];
        if (ch === ' ' || ch === '\n' || ch === '\t' || elapsed >= item.resolveAt[c]) {
          out += ch;
        } else {
          out += rand();
          allDone = false;
        }
      }
      item.node.nodeValue = out;
      if (allDone) { item.node.nodeValue = full; item.locked = true; }
    }
    if (!done) requestAnimationFrame(tick);
    else for (var j = 0; j < nodes.length; j++) nodes[j].node.nodeValue = nodes[j].full;
  }
  requestAnimationFrame(tick);
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
