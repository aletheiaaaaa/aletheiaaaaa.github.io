#import "@preview/droplet:0.3.1": dropcap
#import "@preview/ctheorems:1.1.3": thmrules
#import "theorems.typ": make-theorems

#let _text         = rgb("#1a1a1a")
#let _heading      = rgb("#0a0a0a")
#let _muted        = rgb("#6b6b6b")
#let _subtle       = rgb("#9a9a9a")
#let _rule         = rgb("#d4d4d4")
#let _code-bg      = luma(245)
#let _accent       = rgb("#c026d3")
#let _accent-light = rgb("#a21caf")
#let _tag-bg       = _accent.lighten(90%)

#let opening(body) = dropcap(height: 2, gap: 4pt, hanging-indent: 0pt, body)

#let blogpost(
  title: none,
  subtitle: none,
  author: "aletheiaaaaa",
  date: none,
  read-time: none,
  tags: none,
  font: "Fira Code",
  size: 10pt,
  body,
) = {
  set text(
    font: font,
    size: size,
    weight: 300,
    fill: _text,
    kerning: true,
    ligatures: true,
    hyphenate: false,
  )
  set par(justify: true, leading: 0.9em, spacing: 1.35em, linebreaks: "optimized")

  set page(
    paper: "iso-b5",
    fill: white,
    margin: 0.5in,
    footer-descent: 30%,
    footer: context {
      let n = counter(page).display()
      let total = counter(page).final().first()
      if total > 1 {
        align(center, text(size: size - 1.5pt, fill: _subtle, n))
      }
    },
  )

  // links
  show link: set text(fill: _accent-light)

  // headings
  set heading(numbering: none)
  show heading: set text(fill: _heading)
  show heading: it => {
    if it.level == 1 {
      v(0.8em, weak: true)
      block(above: 3.2em, below: 1.3em, text(size: 1.25em, weight: 600, it.body))
    } else if it.level == 2 {
      block(above: 2.8em, below: 1.0em, text(size: 1.1em, weight: 500, it.body))
    } else if it.level == 3 {
      block(above: 2.2em, below: 0.85em, text(size: 1em, weight: 500, it.body))
    } else {
      block(above: 1.8em, below: 0.65em, text(size: 1em, weight: 400, emph(it.body)))
    }
  }
  show strong: set text(fill: _heading, weight: 500)

  // inline code
  show raw.where(block: false): it => box(
    fill: _code-bg, radius: 2pt,
    inset: (x: 3.5pt), outset: (y: 2.5pt),
    text(size: 0.9em, it),
  )

  // code blocks
  show raw.where(block: true): it => block(
    width: 100%, fill: _code-bg, radius: 4pt,
    inset: (x: 1.1em, y: 0.9em),
    above: 1.6em, below: 1.6em,
    text(size: 0.87em, it),
  )

  // blockquotes
  show quote.where(block: true): it => block(
    width: 100%,
    stroke: (left: 2.5pt + _rule),
    inset: (left: 1.1em, top: 0.5em, bottom: 0.5em, right: 0em),
    above: 1.5em, below: 1.5em,
    text(style: "italic", fill: _muted, it.body),
  )

  // figures: don't float, center, subtle caption
  set figure(placement: none, gap: 0.9em)
  show figure.caption: it => text(size: 0.82em, fill: _muted, style: "italic", it.body)

  show: thmrules

  // ── Title block ──────────────────────────────────────────────────────────────
  block(width: 100%, {
    if title != none {
      text(size: 2.25em, weight: 600, fill: _heading, title)
    }
    if subtitle != none {
      v(0.3em)
      text(size: 0.95em, fill: _muted, subtitle)
    }
    let parts = ()
    if author    != none and author != ""    { parts.push(author) }
    if date      != none                     { parts.push(str(date)) }
    if read-time != none and read-time != "" { parts.push(read-time) }
    if parts.len() > 0 {
      v(0.25em)
      text(size: 0.78em, fill: _subtle, parts.join("  ·  "))
    }
    if tags != none and tags.len() > 0 {
      v(0.2em)
      for tag in tags {
        box(
          inset: (x: 4pt, y: 2pt), radius: 2pt,
          fill: _tag-bg,
        )[#text(size: 0.72em, fill: _accent-light)[#tag]]
        h(4pt, weak: false)
      }
    }
  })
  v(0.6em)
  line(length: 100%, stroke: 0.5pt + _rule)
  v(1.2em)

  body
}
