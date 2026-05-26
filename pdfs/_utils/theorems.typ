#import "@preview/ctheorems:1.1.3": *

#let make-theorems(
  accent: rgb("#c026d3"),
  alt:    rgb("#7c3aed"),
  minimal: false,
) = {
  let tint        = accent.lighten(93%)
  let border      = rgb("#e5e5e5")
  let box-inset   = (left: 0.9em, top: 0.45em, bottom: 0.45em, right: 0.9em)
  let radius      = 4pt

  let mk-plain(color) = if minimal {
    thmplain.with(
      titlefmt: strong,
      namefmt: x => [(#x)],
      separator: [. ],
      bodyfmt: emph,
      inset: (top: 0em, left: 0em, right: 0em),
    )
  } else {
    (id, head, ..args) => thmbox(
      id, head,
      titlefmt: it => smallcaps(strong(it)),
      namefmt: x => [(#x)],
      separator: [#h(0.4em)],
      bodyfmt: emph,
      fill: tint,
      stroke: (left: 1.5pt + color),
      radius: radius,
      inset: box-inset,
      breakable: true,
      ..args,
    )
  }

  let plain = mk-plain(accent)
  let plain-alt = mk-plain(alt)

  let def = if minimal {
    thmplain.with(
      titlefmt: strong,
      namefmt: x => [(#x)],
      separator: [. ],
      inset: (top: 0em, left: 0em, right: 0em),
    )
  } else {
    (id, head, ..args) => thmbox(
      id, head,
      titlefmt: strong,
      namefmt: x => [(#x)],
      separator: [#h(0.4em)],
      fill: white,
      stroke: (left: 1.5pt + border),
      inset: (x: 0.8em, y: 0.55em),
      radius: radius,
      breakable: true,
      ..args,
    )
  }

  let rmk = if minimal {
    thmplain.with(
      titlefmt: emph,
      namefmt: x => [(#x)],
      separator: [. ],
      inset: (top: 0em, left: 0em, right: 0em),
    )
  } else {
    (id, head, ..args) => thmplain(
      id, head,
      titlefmt: it => text(size: 0.9em, emph(it)),
      namefmt: x => [(#x)],
      separator: [#h(0.4em)],
      bodyfmt: body => text(size: 0.9em, body),
      inset: (top: 0em, left: 0em, right: 0em),
      ..args,
    )
  }

  let proof-like = if minimal {
    (id, label) => thmproof(
      id, label,
      inset: (top: 0em, left: 0em, right: 0em),
      separator: [. ],
    )
  } else {
    (id, label) => thmproof(
      id, label,
      titlefmt: emph,
      separator: [#h(0.4em)],
      fill: none,
      stroke: (left: 0.5pt + border),
      inset: box-inset,
      breakable: true,
      bodyfmt: body => [#body #h(1fr) $qed$],
    )
  }

  (
    theorem:     plain("theorem", "Theorem",     base_level: 1),
    lemma:       plain-alt("theorem", "Lemma",   base_level: 1),
    proposition: plain("theorem", "Proposition", base_level: 1),
    corollary:   plain-alt("theorem", "Corollary", base_level: 1),
    claim:       plain("claim",   "Claim",       base_level: 1),

    definition:  def("theorem", "Definition", base_level: 1),
    example:     def("theorem", "Example",    base_level: 1),
    algorithm:   def("theorem", "Algorithm",  base_level: 1),
    axiom:       def("theorem", "Axiom",      base_level: 1),
    assumption:  def("theorem", "Assumption", base_level: 1),

    remark:   rmk("theorem", "Remark",   base_level: 1),
    notation: rmk("theorem", "Notation", base_level: 1),

    exercise: rmk("exercise", "Exercise", base_level: 1),
    solution: proof-like("solution", "Solution"),

    proof: proof-like("proof", "Proof"),
  )
}

