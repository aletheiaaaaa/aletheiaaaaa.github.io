#!/usr/bin/env python3
"""
ssg.py — minimal static site generator

Usage:
  python ssg.py build          build site → docs/
  python ssg.py serve [port]   build + serve locally (default 8080)
  python ssg.py new "Title"    scaffold a new post

Source layout:
  config.yml                   site metadata + nav
  pages/about.md               static pages
  _posts/YYYY-MM-DD-slug/      post directory
    index.md                   post content (YAML frontmatter + markdown)
    assets/                    images, diagrams, etc.

Markdown extras:
  :::theorem / :::proof / :::definition / :::remark / :::example / :::lemma
    → styled callout blocks (content is processed as markdown)
  $...$  and  $$...$$          → rendered by MathJax
  ```lang  fenced code         → syntax-highlighted via Pygments
"""

import os, sys, re, json, shutil, datetime, http.server, socketserver
from pathlib import Path
import yaml
import markdown
from markdown.preprocessors import Preprocessor
from markdown.extensions import Extension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.toc import TocExtension
from markdown.extensions.footnotes import FootnoteExtension
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.md_in_html import MarkdownInHtmlExtension

ROOT       = Path(__file__).parent
PAGES_DIR  = ROOT / "pages"
STATIC_DIR = ROOT / "static"
OUT_DIR    = ROOT / "docs"

# ── CSS ───────────────────────────────────────────────────────────────────────

THEME_CSS = ROOT / 'theme.css'

def load_css():
    if THEME_CSS.exists():
        return THEME_CSS.read_text()
    raise FileNotFoundError(f'theme.css not found at {THEME_CSS}')

# ── Markdown extension: fenced divs (:::class ... :::) ────────────────────────

class FencedDivPreprocessor(Preprocessor):
    """Convert :::class\n...\n::: to <div class='class' markdown='1'>...</div>."""

    OPEN  = re.compile(r'^:::(\w+)\s*$')
    CLOSE = re.compile(r'^:::\s*$')

    def run(self, lines):
        new_lines, i = [], 0
        while i < len(lines):
            m = self.OPEN.match(lines[i])
            if m:
                cls = m.group(1)
                new_lines.append(f'<div class="{cls}" markdown="1">')
                new_lines.append('')
                i += 1
                depth = 1
                while i < len(lines) and depth > 0:
                    if self.OPEN.match(lines[i]):
                        depth += 1
                        new_lines.append(lines[i])
                    elif self.CLOSE.match(lines[i]):
                        depth -= 1
                        if depth > 0:
                            new_lines.append(lines[i])
                    else:
                        new_lines.append(lines[i])
                    i += 1
                new_lines.append('')
                new_lines.append('</div>')
            else:
                new_lines.append(lines[i])
                i += 1
        return new_lines


class FencedDivExtension(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(FencedDivPreprocessor(md), 'fenced_div', 175)


# ── Math protection ────────────────────────────────────────────────────────────

_PLACEHOLDER = 'SSGMATH{}ENDMATH'

def protect_math(text):
    """Replace LaTeX math with placeholders so markdown can't mangle it."""
    stash = []

    def store(m):
        stash.append(m.group(0))
        return _PLACEHOLDER.format(len(stash) - 1)

    text = re.sub(r'\$\$[\s\S]+?\$\$', store, text)
    text = re.sub(r'\$[^\$\n]+?\$',    store, text)
    return text, stash


def restore_math(html, stash):
    for i, orig in enumerate(stash):
        html = html.replace(_PLACEHOLDER.format(i), orig)
    return html


# ── Markdown rendering ─────────────────────────────────────────────────────────

def make_md():
    return markdown.Markdown(
        extensions=[
            FencedCodeExtension(),
            FencedDivExtension(),
            TableExtension(),
            TocExtension(permalink=False),
            FootnoteExtension(),
            CodeHiliteExtension(css_class='codehilite', guess_lang=False),
            MarkdownInHtmlExtension(),
            'nl2br',
        ]
    )


def render_markdown(text):
    text, stash = protect_math(text)
    md = make_md()
    html = md.convert(text)
    html = restore_math(html, stash)
    return html, md.toc


def has_math(text):
    return bool(re.search(r'\$', text))


# ── Frontmatter ───────────────────────────────────────────────────────────────

def parse_frontmatter(text):
    if not text.startswith('---'):
        return {}, text
    end = text.find('\n---', 3)
    if end == -1:
        return {}, text
    raw  = text[4:end].strip()
    body = text[end + 4:].lstrip('\n')
    try:
        meta = yaml.safe_load(raw) or {}
    except Exception:
        meta = {}
    return meta, body


# ── Config ────────────────────────────────────────────────────────────────────

def load_config():
    cfg_file = ROOT / 'config.yml'
    cfg = {}
    if cfg_file.exists():
        with open(cfg_file) as f:
            cfg = yaml.safe_load(f) or {}
    cfg.setdefault('title', 'untitled')
    cfg.setdefault('description', '')
    cfg.setdefault('author', '')
    cfg.setdefault('base_url', '')
    cfg.setdefault('nav', [
        {'text': 'Home',  'href': 'index.html'},
        {'text': 'About', 'href': 'about.html'},
    ])
    return cfg


# ── HTML templates ─────────────────────────────────────────────────────────────

def nav_items_html(cfg, root_rel):
    items = ''
    for item in cfg['nav']:
        href = root_rel + item['href']
        items += f'<li><a href="{href}">{item["text"]}</a></li>'
    return items


def render_page(title, body_html, cfg, root_rel='', math=False):
    math_snippet = ''
    if math:
        math_snippet = (
            '<script>MathJax={tex:{inlineMath:[["$","$"],["\\\\(","\\\\)"]]},'
            'options:{skipHtmlTags:["script","noscript","style","textarea","pre"]}};</script>'
            '<script id="MathJax-script" async '
            'src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>'
        )
    site_title = cfg['title']
    full_title = f'{title} — {site_title}' if title != site_title else site_title
    brand      = f'{site_title}<span class="cursor" aria-hidden="true">▎</span>'
    year       = datetime.date.today().year
    author     = cfg.get('author', '')
    footer_left = f'&copy; {year} {site_title}'
    if author:
        footer_left += f' &middot; {author}'
    footer_links = ''.join(
        f'<a href="{root_rel}{item["href"]}">{item["text"].lower()}</a>'
        for item in cfg.get('nav', [])
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{full_title}</title>
  <link rel="stylesheet" href="{root_rel}style.css">
  {math_snippet}
  <script>(function(){{var t=localStorage.getItem('theme');if(t)document.documentElement.setAttribute('data-theme',t);}})();</script>
</head>
<body>
  <header class="site-header">
    <nav class="site-nav">
      <div class="nav-brand"><a href="{root_rel}index.html">{brand}</a></div>
      <ul class="nav-links">{nav_items_html(cfg, root_rel)}</ul>
      <button class="theme-toggle" id="theme-toggle" aria-label="Toggle light/dark mode">◑</button>
    </nav>
  </header>
  <main>
    {body_html}
  </main>
  <footer class="site-footer">
    <div class="footer-inner">
      <span>{footer_left}</span>
      <nav class="footer-links">{footer_links}</nav>
    </div>
  </footer>
  <script>
(function () {{
  var btn = document.getElementById('theme-toggle');
  if (btn) {{
    function _theme() {{
      return document.documentElement.getAttribute('data-theme') ||
        (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    }}
    btn.addEventListener('click', function () {{
      var next = _theme() === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
    }});
  }}
}})();
(function () {{
  var C = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#%&*_+-=<>[]{{}}|;:.,?/\\~^`';
  function rand() {{ return C[Math.floor(Math.random() * C.length)]; }}

  var SKIP = new Set(['script', 'style', 'noscript', 'title']);

  function walk(root) {{
    var out = [];
    var tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {{
      acceptNode: function (n) {{
        var p = n.parentElement;
        while (p) {{
          if (SKIP.has(p.tagName.toLowerCase())) return NodeFilter.FILTER_REJECT;
          if (p.getAttribute('aria-hidden') === 'true') return NodeFilter.FILTER_REJECT;
          if (p.classList && p.classList.contains('hero-type')) return NodeFilter.FILTER_REJECT;
          p = p.parentElement;
        }}
        if (!n.textContent.trim()) return NodeFilter.FILTER_SKIP;
        if (/[$]/.test(n.textContent)) return NodeFilter.FILTER_SKIP;
        return NodeFilter.FILTER_ACCEPT;
      }}
    }});
    var n;
    while ((n = tw.nextNode())) out.push(n);
    return out;
  }}

  document.addEventListener('DOMContentLoaded', function () {{
    var main = document.querySelector('main');
    if (main) {{
      main.style.cssText = 'opacity:0;transform:translate(-10px,-10px);transition:opacity 0.45s ease,transform 0.45s ease';
      requestAnimationFrame(function () {{
        requestAnimationFrame(function () {{
          main.style.opacity = '1';
          main.style.transform = 'translate(0,0)';
        }});
      }});
    }}

    var heroType = document.querySelector('.hero-type');
    if (heroType) {{
      var _full = heroType.textContent;
      heroType.textContent = '';
      var _i = 0;
      function _typeNext() {{
        if (_i < _full.length) {{ heroType.textContent = _full.slice(0, ++_i); setTimeout(_typeNext, 110); }}
      }}
      setTimeout(_typeNext, 80);
    }}

    var nodes = walk(document.body);
    var total = nodes.length;

    // Pre-compute per-character reveal thresholds and scramble immediately
    var entries = nodes.map(function (node, idx) {{
      var orig = node.textContent;
      var base = (idx / total) * 0.4;
      var thresh = orig.split('').map(function (_, i) {{
        return base + (i / (orig.length || 1)) * 0.3 + Math.random() * 0.15;
      }});
      node.textContent = orig.split('').map(function (c) {{
        return (c === ' ' || c === '\\n' || c === '\\t') ? c : rand();
      }}).join('');
      return {{ node: node, orig: orig, thresh: thresh }};
    }});

    var dur = 1100, t0 = null;
    requestAnimationFrame(function tick(ts) {{
      if (!t0) t0 = ts;
      var p = (ts - t0) / dur;
      var done = p >= 1;
      entries.forEach(function (e) {{
        if (done) {{ e.node.textContent = e.orig; return; }}
        var s = '', len = e.orig.length;
        for (var i = 0; i < len; i++) {{
          var ch = e.orig[i];
          if (ch === ' ' || ch === '\\n' || ch === '\\t') {{ s += ch; }}
          else {{ s += (p > e.thresh[i]) ? ch : rand(); }}
        }}
        e.node.textContent = s;
      }});
      if (!done) requestAnimationFrame(tick);
    }});
  }});
}})();
(function () {{
  var headings = Array.from(document.querySelectorAll('.post-body h2, .post-body h3, .post-body h4'));
  if (!headings.length) return;
  var links = {{}};
  document.querySelectorAll('.toc-inner a').forEach(function (a) {{
    links[decodeURIComponent(a.getAttribute('href').slice(1))] = a;
  }});
  var cur = null;
  function update() {{
    var cut = window.scrollY + 112;
    var next = null;
    for (var i = 0; i < headings.length; i++) {{
      if (headings[i].getBoundingClientRect().top + window.scrollY <= cut) next = headings[i].id;
    }}
    if (next === cur) return;
    if (links[cur]) links[cur].classList.remove('toc-active');
    cur = next;
    if (links[cur]) links[cur].classList.add('toc-active');
  }}
  window.addEventListener('scroll', update, {{ passive: true }});
  update();
}})();
  </script>
</body>
</html>"""


# ── Utilities ─────────────────────────────────────────────────────────────────

def read_time(text):
    """Estimate reading time in minutes (200 wpm)."""
    words = len(re.findall(r'\w+', text))
    minutes = max(1, round(words / 200))
    return f'{minutes} min read'


def tags_html(tags):
    if not tags:
        return ''
    if isinstance(tags, str):
        tags = tags.split()
    chips = ''.join(f'<span class="tag">{t}</span>' for t in tags)
    return f'<div class="tag-list">{chips}</div>'


def projects_grid_html(projects, full=False):
    """Render a grid of project cards. full=True for the standalone projects page."""
    cards = ''
    for proj in projects:
        name  = proj.get('name', '')
        desc  = proj.get('description', '')
        href  = proj.get('href', '#')
        lang  = proj.get('lang', '')
        links = proj.get('links', [])

        lang_tag = f'<span class="card-tag">{lang}</span>' if lang else ''

        gh_label = ''
        for lnk in links:
            if 'github' in lnk.get('href', '').lower():
                gh_label = '<span class="card-gh-link">GitHub ↗</span>'
                break

        footer = f'<div class="card-footer">{lang_tag}{gh_label}</div>' if (lang_tag or gh_label) else ''
        card_class = 'project-card project-card--full' if full else 'project-card'
        cards += (
            f'<a class="{card_class}" href="{href}" target="_blank" rel="noopener">'
            f'<h3>{name}</h3>'
            f'<p class="card-desc">{desc}</p>'
            f'{footer}'
            f'</a>'
        )
    grid_class = 'projects-page-grid' if full else 'projects-grid'
    return f'<div class="{grid_class}">{cards}</div>'


# ── Post discovery ─────────────────────────────────────────────────────────────

def date_from_slug(slug):
    """Extract date from YYYY-MM-DD-slug or return None."""
    m = re.match(r'^(\d{4}-\d{2}-\d{2})', slug)
    if m:
        try:
            return datetime.date.fromisoformat(m.group(1))
        except ValueError:
            pass
    return None


def find_posts():
    """Return list of post dicts sorted newest first.

    Posts are dated subdirectories inside pages/ (name starts with YYYY-MM-DD).
    """
    posts = []
    if not PAGES_DIR.exists():
        return posts

    for entry in PAGES_DIR.iterdir():
        if not entry.is_dir():
            continue
        slug = entry.name
        if not re.match(r'^\d{4}-\d{2}-\d{2}', slug):
            continue

        md_file = entry / 'index.md'
        if not md_file.exists():
            candidates = sorted(entry.glob('*.md'))
            if not candidates:
                continue
            md_file = candidates[0]

        if not md_file.exists():
            continue

        text = md_file.read_text()
        meta, _ = parse_frontmatter(text)

        date = None
        if 'date' in meta:
            raw = meta['date']
            if isinstance(raw, datetime.date):
                date = raw
            else:
                try:
                    date = datetime.date.fromisoformat(str(raw)[:10])
                except ValueError:
                    pass
        if date is None:
            date = date_from_slug(slug) or datetime.date(1970, 1, 1)

        posts.append({
            'slug':  slug,
            'path':  md_file,
            'dir':   md_file.parent,
            'meta':  meta,
            'date':  date,
        })

    posts.sort(key=lambda p: p['date'], reverse=True)
    return posts


def out_path_for_post(post):
    """Return (out_dir, root_rel) for a post."""
    slug = post['slug']
    out_dir = OUT_DIR / 'posts' / slug
    return out_dir, '../../'


# ── Builders ──────────────────────────────────────────────────────────────────

def build_post(post, cfg, older=None, newer=None):
    text = post['path'].read_text()
    meta, body = parse_frontmatter(text)

    content_html, toc_html = render_markdown(body)
    math = has_math(body)

    title    = meta.get('title', post['slug'])
    subtitle = meta.get('description', meta.get('subtitle', ''))
    author   = meta.get('author', cfg.get('author', ''))
    if isinstance(author, list):
        author = ', '.join(
            a['name'] if isinstance(a, dict) else a for a in author
        )
    date_str = post['date'].strftime('%b %-d, %Y') if post['date'].year > 1970 else ''
    rtime    = read_time(body)

    byline_parts = [x for x in [date_str, rtime] if x]
    sep = '<span class="sep">&middot;</span>'
    byline_html = sep.join(f'<span>{p}</span>' for p in byline_parts)
    if author:
        byline_html = f'<span>{author}</span>{sep}' + byline_html

    header  = '<header class="post-header">'
    header += f'<h1>{title}</h1>'
    if subtitle:
        header += f'<p class="subtitle">{subtitle}</p>'
    if byline_html:
        header += f'<p class="byline">{byline_html}</p>'
    header += tags_html(meta.get('tags', []))
    header += '</header>'

    toc_sidebar = ''
    if toc_html and toc_html.strip():
        toc_sidebar = (
            f'<aside class="post-toc">'
            f'<div class="toc-inner">'
            f'<p class="toc-label">Contents</p>'
            f'{toc_html}'
            f'</div>'
            f'</aside>'
        )
    post_nav = ''
    if older or newer:
        older_html = ''
        newer_html = ''
        if older:
            older_title = older['meta'].get('title', older['slug'])
            older_href  = f'../{older["slug"]}/index.html'
            older_html  = (
                f'<a class="post-nav-item post-nav-older" href="{older_href}">'
                f'<span class="post-nav-label">← Previous</span>'
                f'<span class="post-nav-title">{older_title}</span>'
                f'</a>'
            )
        if newer:
            newer_title = newer['meta'].get('title', newer['slug'])
            newer_href  = f'../{newer["slug"]}/index.html'
            newer_html  = (
                f'<a class="post-nav-item post-nav-newer" href="{newer_href}">'
                f'<span class="post-nav-label">Next →</span>'
                f'<span class="post-nav-title">{newer_title}</span>'
                f'</a>'
            )
        post_nav = f'<nav class="post-nav">{older_html}{newer_html}</nav>'

    body_html = (
        f'<div class="post-layout">'
        f'{toc_sidebar}'
        f'<article class="post-wrap">{header}<div class="post-body">{content_html}</div>{post_nav}</article>'
        f'</div>'
    )

    out_dir, root_rel = out_path_for_post(post)
    out_dir.mkdir(parents=True, exist_ok=True)

    for asset in post['dir'].iterdir():
        if asset.name == 'index.md':
            continue
        dst = out_dir / asset.name
        if asset.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(asset, dst)
        else:
            shutil.copy2(asset, dst)

    html = render_page(title, body_html, cfg, root_rel=root_rel, math=math)
    (out_dir / 'index.html').write_text(html)
    print(f'  post  → posts/{post["slug"]}/index.html')


def build_index(posts, cfg):
    hero = cfg.get('hero', {})
    hero_html = ''
    if hero:
        h_title    = hero.get('title', cfg['title'])
        h_tagline  = hero.get('tagline', hero.get('subtitle', ''))
        h_body     = hero.get('body', cfg.get('description', ''))
        brand      = f'<span class="hero-type">{h_title}</span><span class="cursor" aria-hidden="true">▎</span>'
        hero_html  = f'<section class="content-width hero"><h1>{brand}</h1>'
        if h_tagline:
            hero_html += f'<p class="hero-tagline">{h_tagline}</p>'
        if h_body:
            hero_html += f'<p class="hero-body">{h_body}</p>'
        hero_html += '</section>'

    items = ''
    for p in posts[:3]:
        title     = p['meta'].get('title', p['slug'])
        desc      = p['meta'].get('description', p['meta'].get('subtitle', ''))
        date_str  = p['date'].strftime('%b %-d, %Y') if p['date'].year > 1970 else ''
        rtime     = read_time(p['path'].read_text())
        post_tags = p['meta'].get('tags', [])
        href      = f'posts/{p["slug"]}/index.html'
        sep = '<span class="sep">&middot;</span>'
        meta_parts = [x for x in [date_str, rtime] if x]
        meta_html = sep.join(f'<span>{x}</span>' for x in meta_parts)
        items += f'''
<a class="post-item" href="{href}">
  <div class="post-meta">{meta_html}</div>
  <h3>{title}</h3>
  {f'<p class="post-desc">{desc}</p>' if desc else ''}
  {tags_html(post_tags)}
</a>'''

    section_label = cfg.get('posts_label', 'Latest Posts')
    section_hdr = f'<div class="section-row"><span class="section-label">{section_label}</span><a class="section-link" href="blog.html">all →</a></div>'
    posts_col = f'<div class="posts-section">{section_hdr}<div class="posts-list">{items}</div></div>'

    projects = cfg.get('projects', [])
    projects_col = ''
    if projects:
        grid_html = projects_grid_html(projects[:4], full=False)
        projects_col = (
            f'<div class="projects-col">'
            f'<div class="section-row">'
            f'<span class="section-label">Projects</span>'
            f'<a class="section-link" href="projects.html">all →</a>'
            f'</div>'
            f'{grid_html}'
            f'</div>'
        )

    index_grid = f'<div class="content-width"><div class="index-grid">{posts_col}{projects_col}</div></div>'
    body = hero_html + index_grid
    html = render_page(cfg['title'], body, cfg, root_rel='')
    (OUT_DIR / 'index.html').write_text(html)
    print(f'  index → index.html')


def build_page(md_file, cfg, posts=None):
    """Build a static page from pages/name.md."""
    text = md_file.read_text()
    meta, body = parse_frontmatter(text)

    content_html, _ = render_markdown(body)
    math = has_math(body)
    title = meta.get('title', md_file.stem.replace('-', ' ').title())

    if meta.get('layout') == 'projects':
        intro = f'<div class="page-intro">{content_html}</div>' if body.strip() else ''
        grid  = projects_grid_html(cfg.get('projects', []), full=True)
        body_html = f'<div class="page-wrap"><h1 class="page-title">{title}</h1>{intro}{grid}</div>'
    elif meta.get('layout') == 'blog':
        items = ''
        for p in (posts or []):
            ptitle    = p['meta'].get('title', p['slug'])
            desc      = p['meta'].get('description', p['meta'].get('subtitle', ''))
            date_str  = p['date'].strftime('%b %-d, %Y') if p['date'].year > 1970 else ''
            rtime     = read_time(p['path'].read_text())
            post_tags = p['meta'].get('tags', [])
            href      = f'posts/{p["slug"]}/index.html'
            sep = '<span class="sep">&middot;</span>'
            meta_parts = [x for x in [date_str, rtime] if x]
            meta_html = sep.join(f'<span>{x}</span>' for x in meta_parts)
            items += f'''
<a class="post-item" href="{href}">
  <div class="post-meta">{meta_html}</div>
  <h3>{ptitle}</h3>
  {f'<p class="post-desc">{desc}</p>' if desc else ''}
  {tags_html(post_tags)}
</a>'''
        intro = f'<div class="page-intro">{content_html}</div>' if body.strip() else ''
        body_html = (
            f'<div class="page-wrap">'
            f'<h1 class="page-title">{title}</h1>'
            f'{intro}'
            f'<div class="posts-list">{items}</div>'
            f'</div>'
        )
    else:
        body_html = f'<div class="page-wrap"><h1 class="page-title">{title}</h1>{content_html}</div>'

    html = render_page(title, body_html, cfg, root_rel='', math=math)

    out_name = md_file.stem + '.html'
    (OUT_DIR / out_name).write_text(html)
    print(f'  page  → {out_name}')


# ── Build ─────────────────────────────────────────────────────────────────────

def cmd_build():
    cfg = load_config()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Write CSS
    (OUT_DIR / 'style.css').write_text(load_css())
    print(f'  css   → style.css  (from theme.css)')

    # Copy static/ if it exists
    if STATIC_DIR.exists():
        for item in STATIC_DIR.iterdir():
            dst = OUT_DIR / item.name
            if item.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(item, dst)
            else:
                shutil.copy2(item, dst)
        print(f'  static → copied')

    # Find posts first so blog page can reference them
    posts = find_posts()

    # Build pages
    if PAGES_DIR.exists():
        for md_file in sorted(PAGES_DIR.glob('*.md')):
            build_page(md_file, cfg, posts=posts)

    # Build posts (sorted newest-first, so older = higher index, newer = lower index)
    for i, post in enumerate(posts):
        build_post(
            post, cfg,
            older=posts[i + 1] if i + 1 < len(posts) else None,
            newer=posts[i - 1] if i > 0 else None,
        )

    # Build index
    build_index(posts, cfg)

    print(f'\nBuilt {len(posts)} post(s) → {OUT_DIR}/')


# ── Serve ─────────────────────────────────────────────────────────────────────

def cmd_serve(port=8080):
    cmd_build()
    os.chdir(OUT_DIR)
    handler = http.server.SimpleHTTPRequestHandler

    class QuietHandler(handler):
        def log_message(self, fmt, *args):
            pass  # suppress request logs

    with socketserver.TCPServer(('', port), QuietHandler) as httpd:
        print(f'\nServing at http://localhost:{port}/  (Ctrl+C to stop)\n')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nStopped.')


# ── New post scaffold ─────────────────────────────────────────────────────────

def cmd_new(title):
    today = datetime.date.today().isoformat()
    slug  = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    name  = f'{today}-{slug}'
    post_dir = POSTS_DIR / name
    post_dir.mkdir(parents=True, exist_ok=True)
    md_file = post_dir / 'index.md'
    if md_file.exists():
        print(f'Already exists: {md_file}')
        return
    md_file.write_text(f"""---
title: "{title}"
description: |
  One-line summary of the post.
author: ""
date: {today}
tags: []
---

Write your post here. The first paragraph gets a drop cap automatically.

## Section heading

Body text. Inline math: $E = mc^2$. Display math:

$$
\\int_0^\\infty e^{{-x^2}} \\, dx = \\frac{{\\sqrt{{\\pi}}}}{{2}}
$$

:::theorem
State a theorem here. *Markdown* works inside.
:::

:::proof
Proof follows.
:::
""")
    print(f'Created: {md_file}')


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args or args[0] == 'build':
        cmd_build()
    elif args[0] == 'serve':
        port = int(args[1]) if len(args) > 1 else 8080
        cmd_serve(port)
    elif args[0] == 'new':
        if len(args) < 2:
            print('Usage: python ssg.py new "Post Title"')
            sys.exit(1)
        cmd_new(' '.join(args[1:]))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
