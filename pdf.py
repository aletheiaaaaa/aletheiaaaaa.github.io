#!/usr/bin/env python3
"""
pdf.py — PDF generator for blog posts using Typst

Usage:
  python pdf.py build              build all posts → pdfs/out/
  python pdf.py build <slug>...    build specific post(s)

Requires: typst, pandoc >= 3.1

Source layout mirrors ssg.py:
  pages/YYYY-MM-DD-slug/index.md   post content (same frontmatter)
  pdfs/_utils/style.typ            page template
  pdfs/_utils/theorems.typ         theorem environments
  pdfs/out/                        compiled PDFs (output)

Markdown extras supported:
  :::theorem / :::proof / :::definition / etc.  → ctheorems environments
  $...$ and $$...$$                             → Typst math (via pandoc)
  ```lang fenced code                           → typst raw blocks
  ![alt](path)                                  → typst figures
"""

import sys, re, shutil, subprocess, datetime
from pathlib import Path
import yaml

ROOT      = Path(__file__).parent
PAGES_DIR = ROOT / 'pages'
PDFS_DIR  = ROOT / 'pdfs'
OUT_DIR   = PDFS_DIR / 'out'

TYPST_ENVS = {
    'theorem':     'thm.theorem',
    'lemma':       'thm.lemma',
    'proposition': 'thm.proposition',
    'corollary':   'thm.corollary',
    'claim':       'thm.claim',
    'definition':  'thm.definition',
    'example':     'thm.example',
    'algorithm':   'thm.algorithm',
    'axiom':       'thm.axiom',
    'assumption':  'thm.assumption',
    'remark':      'thm.remark',
    'notation':    'thm.notation',
    'proof':       'thm.proof',
    'exercise':    'thm.exercise',
    'solution':    'thm.solution',
}


# ── Shared helpers (mirrors ssg.py) ───────────────────────────────────────────

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


def date_from_slug(slug):
    m = re.match(r'^(\d{4}-\d{2}-\d{2})', slug)
    if m:
        try:
            return datetime.date.fromisoformat(m.group(1))
        except ValueError:
            pass
    return None


def find_posts():
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
            'slug': slug,
            'path': md_file,
            'dir':  md_file.parent,
            'meta': meta,
            'date': date,
        })
    posts.sort(key=lambda p: p['date'], reverse=True)
    return posts


# ── Utilities ─────────────────────────────────────────────────────────────────

def read_time(text):
    words = len(re.findall(r'\w+', text))
    return f'{max(1, round(words / 200))} min read'


# ── Markdown → Typst conversion ────────────────────────────────────────────────

def preprocess_divs(text):
    """Convert :::class fenced divs to pandoc raw-typst blocks."""
    lines = text.split('\n')
    out = []
    for line in lines:
        m = re.match(r'^:::(\w+)\s*$', line)
        if m:
            env = TYPST_ENVS.get(m.group(1))
            if env:
                out += ['', '```{=typst}', f'#{env}[', '```', '']
            else:
                out.append(line)
        elif re.match(r'^:::\s*$', line):
            out += ['', '```{=typst}', ']', '```', '']
        else:
            out.append(line)
    return '\n'.join(out)


def md_to_typst(body):
    preprocessed = preprocess_divs(body)
    result = subprocess.run(
        ['pandoc', '-f', 'markdown+tex_math_dollars+fenced_divs', '-t', 'typst', '--wrap=none'],
        input=preprocessed.encode(),
        capture_output=True,
        check=True,
    )
    return result.stdout.decode()


# ── .typ source generation ─────────────────────────────────────────────────────

def _tstr(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


def make_typ(meta, body_typst, slug, rtime=''):
    title    = meta.get('title', slug)
    subtitle = meta.get('description', meta.get('subtitle', ''))
    author   = meta.get('author', 'aletheiaaaaa')
    if isinstance(author, list):
        author = ', '.join(a['name'] if isinstance(a, dict) else a for a in author)

    date = meta.get('date', '')
    if isinstance(date, datetime.date):
        date = date.strftime('%b %-d, %Y')
    elif date:
        try:
            date = datetime.date.fromisoformat(str(date)[:10]).strftime('%b %-d, %Y')
        except ValueError:
            date = str(date)

    tags = meta.get('tags', [])
    if isinstance(tags, str):
        tags = tags.split()

    args = [f'  title: {_tstr(title)},']
    if subtitle:
        args.append(f'  subtitle: {_tstr(subtitle)},')
    if author:
        args.append(f'  author: {_tstr(author)},')
    if date:
        args.append(f'  date: {_tstr(date)},')
    if tags:
        args.append(f'  tags: ({", ".join(_tstr(t) for t in tags)},),')
    if rtime:
        args.append(f'  read-time: {_tstr(rtime)},')

    return '\n'.join([
        '#import "_utils/style.typ": blogpost',
        '#import "_utils/theorems.typ": make-theorems',
        '',
        '#let thm = make-theorems()',
        '#show: blogpost.with(',
        *args,
        ')',
        '',
        body_typst,
    ])


# ── Build ──────────────────────────────────────────────────────────────────────

def build_post(post):
    text = post['path'].read_text()
    meta, body = parse_frontmatter(text)

    try:
        body_typst = md_to_typst(body)
    except subprocess.CalledProcessError as e:
        print(f'  ERROR  pandoc failed for {post["slug"]}:')
        print(e.stderr.decode().strip())
        return False

    rtime = read_time(body)
    typ_src = make_typ(meta, body_typst, post['slug'], rtime=rtime)

    # Use a build dir inside pdfs/ so snap typst can access it
    tmp = PDFS_DIR / f'.build-{post["slug"]}'
    try:
        tmp.mkdir(exist_ok=True)

        # _utils/ symlinked so #import "_utils/..." resolves
        utils_link = tmp / '_utils'
        if not utils_link.exists():
            utils_link.symlink_to(PDFS_DIR / '_utils')

        # copy post assets (diagrams, images, etc.)
        for item in post['dir'].iterdir():
            if item.name == 'index.md':
                continue
            dst = tmp / item.name
            if item.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(item, dst)
            else:
                shutil.copy2(item, dst)

        (tmp / 'post.typ').write_text(typ_src)

        out_pdf = OUT_DIR / f'{post["slug"]}.pdf'
        result = subprocess.run(
            ['typst', 'compile', str(tmp / 'post.typ'), str(out_pdf)],
            capture_output=True,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if result.returncode != 0:
        print(f'  ERROR  typst failed for {post["slug"]}:')
        print(result.stderr.decode().strip())
        return False

    print(f'  pdf  → out/{post["slug"]}.pdf')
    return True


def cmd_build(slugs=None):
    posts = find_posts()
    if slugs:
        posts = [p for p in posts if p['slug'] in slugs]
        if not posts:
            print(f'No posts found matching: {slugs}')
            sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = sum(build_post(p) for p in posts)
    print(f'\nBuilt {ok}/{len(posts)} PDF(s) → {OUT_DIR}/')


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args or args[0] == 'build':
        cmd_build(args[1:] or None)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
