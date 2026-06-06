/* ── Page transition: fade out on navigation ── */
(function () {
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a');
    if (!a) return;
    var href = a.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('mailto') ||
        a.target === '_blank' || e.metaKey || e.ctrlKey || e.shiftKey) return;
    e.preventDefault();
    document.querySelector('main').style.cssText =
      'animation:none;opacity:0;transition:opacity 0.05s ease';
    setTimeout(function () { window.location.href = href; }, 60);
  });
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
  var headings = Array.from(document.querySelectorAll('.post-body h2, .post-body h3, .post-body h4'));
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
