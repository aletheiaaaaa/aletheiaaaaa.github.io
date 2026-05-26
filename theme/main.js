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

(function () {
  var C = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#%&*_+-=<>[]{}|;:.,?/\\~^`';
  function rand() { return C[Math.floor(Math.random() * C.length)]; }

  var SKIP = new Set(['script', 'style', 'noscript', 'title']);

  function walk(root) {
    var out = [];
    var tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        var p = n.parentElement;
        while (p) {
          if (SKIP.has(p.tagName.toLowerCase())) return NodeFilter.FILTER_REJECT;
          if (p.getAttribute('aria-hidden') === 'true') return NodeFilter.FILTER_REJECT;
          if (p.classList && p.classList.contains('hero-type')) return NodeFilter.FILTER_REJECT;
          p = p.parentElement;
        }
        if (!n.textContent.trim()) return NodeFilter.FILTER_SKIP;
        if (/[$]/.test(n.textContent)) return NodeFilter.FILTER_SKIP;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var n;
    while ((n = tw.nextNode())) out.push(n);
    return out;
  }

  document.addEventListener('DOMContentLoaded', function () {
    var isIndex = document.body.dataset.page === 'index';
    var firstVisit = !sessionStorage.getItem('scramble-done');
    if (isIndex) sessionStorage.setItem('scramble-done', '1');
    if (!isIndex || !firstVisit) return;

    var main = document.querySelector('main');
    if (main) {
      main.style.cssText = 'opacity:0;transform:translate(-10px,-10px);transition:opacity 0.45s ease,transform 0.45s ease';
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          main.style.opacity = '1';
          main.style.transform = 'translate(0,0)';
        });
      });
    }

    var heroType = document.querySelector('.hero-type');
    if (heroType) {
      var _full = heroType.textContent;
      heroType.textContent = '';
      var _i = 0;
      function _typeNext() {
        if (_i < _full.length) { heroType.textContent = _full.slice(0, ++_i); setTimeout(_typeNext, 110); }
      }
      setTimeout(_typeNext, 80);
    }

    var nodes = walk(document.body);
    var total = nodes.length;

    var entries = nodes.map(function (node, idx) {
      var orig = node.textContent;
      var base = (idx / total) * 0.4;
      var thresh = orig.split('').map(function (_, i) {
        return base + (i / (orig.length || 1)) * 0.3 + Math.random() * 0.15;
      });
      node.textContent = orig.split('').map(function (c) {
        return (c === ' ' || c === '\n' || c === '\t') ? c : rand();
      }).join('');
      return { node: node, orig: orig, thresh: thresh };
    });

    var dur = 2000, t0 = null;
    requestAnimationFrame(function tick(ts) {
      if (!t0) t0 = ts;
      var p = (ts - t0) / dur;
      var done = p >= 1;
      entries.forEach(function (e) {
        if (done) { e.node.textContent = e.orig; return; }
        var s = '', len = e.orig.length;
        for (var i = 0; i < len; i++) {
          var ch = e.orig[i];
          if (ch === ' ' || ch === '\n' || ch === '\t') { s += ch; }
          else { s += (p > e.thresh[i]) ? ch : rand(); }
        }
        e.node.textContent = s;
      });
      if (!done) requestAnimationFrame(tick);
    });
  });
})();

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
