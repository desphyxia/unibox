import sys, os

OUT = sys.argv[1]


def creature(p, scale=1.0, tx=0, ty=0, uid="a"):
    """A layered creature: every part is its own group so traits can be swapped."""
    ol = p.get("ol")
    ow = p.get("ow", 0)
    stroke = (f'stroke="{ol}" stroke-width="{ow}" stroke-linejoin="round" stroke-linecap="round"'
              if ol else '')
    f = f'filter="url(#{uid}wob)"' if p.get("wob") else ''
    body, mane, horn, hoof = p["body"], p["mane"], p["horn"], p["hoof"]
    belly = p.get("belly", body)
    muzzle = p.get("muzzle", body)
    blush = p.get("blush", "#ff9bb3")
    eye = p.get("eye", "#2a1a3a")
    g = []
    g.append(f'<g transform="translate({tx},{ty}) scale({scale})" {f}>')
    g.append(f'<ellipse cx="4" cy="64" rx="86" ry="9" fill="{p["shadow"]}" opacity="{p.get("shadow_o", 0.25)}"/>')
    g.append(f'<g class="tail"><path d="M-54 -6 C-96 -34 -112 6 -92 34 C-84 18 -70 14 -56 20 Z" fill="{mane}" {stroke}/></g>')
    for x in (-42, -22):
        g.append(f'<g class="leg"><rect x="{x}" y="22" width="15" height="40" rx="7" fill="{belly}" {stroke}/>'
                 f'<rect x="{x}" y="54" width="15" height="10" rx="5" fill="{hoof}" {stroke}/></g>')
    g.append(f'<g class="body"><ellipse cx="0" cy="0" rx="62" ry="42" fill="{body}" {stroke}/></g>')
    for x in (20, 40):
        g.append(f'<g class="leg"><rect x="{x}" y="22" width="15" height="40" rx="7" fill="{body}" {stroke}/>'
                 f'<rect x="{x}" y="54" width="15" height="10" rx="5" fill="{hoof}" {stroke}/></g>')
    g.append(f'<g class="mane"><path d="M36 -70 C8 -92 -14 -70 -8 -42 C-4 -22 -18 -10 -4 4 '
             f'C12 -6 18 -22 30 -34 C36 -44 40 -56 36 -70 Z" fill="{mane}" {stroke}/></g>')
    g.append('<g class="head">')
    g.append(f'<circle cx="58" cy="-46" r="35" fill="{body}" {stroke}/>')
    g.append(f'<ellipse cx="80" cy="-33" rx="17" ry="13" fill="{muzzle}" {stroke}/>')
    g.append(f'<path d="M40 -76 L34 -98 L56 -82 Z" fill="{body}" {stroke}/>')
    g.append(f'<path d="M62 -80 L72 -126 L84 -76 Z" fill="{horn}" {stroke}/>')
    g.append(f'<path d="M58 -64 C66 -76 78 -76 86 -66 C74 -70 66 -68 58 -64 Z" fill="{mane}" {stroke}/>')
    g.append(f'<circle cx="68" cy="-50" r="8.5" fill="{eye}"/><circle cx="71" cy="-53" r="3.2" fill="#fff"/>'
             f'<circle cx="66" cy="-47" r="1.6" fill="#fff"/>')
    g.append(f'<circle cx="62" cy="-32" r="7" fill="{blush}" opacity="0.5"/>')
    g.append(f'<path d="M90 -36 q4 3 0 6" fill="none" stroke="{eye}" stroke-width="2" stroke-linecap="round"/>')
    g.append(f'<path d="M84 -24 q6 4 12 -1" fill="none" stroke="{eye}" stroke-width="2" stroke-linecap="round"/>')
    g.append('</g></g>')
    return "".join(g)


def apple_tree(p, x, y):
    t = [f'<g transform="translate({x},{y})">']
    t.append(f'<rect x="-9" y="-70" width="18" height="74" rx="7" fill="{p["trunk"]}" {p["stk"]}/>')
    for cx, cy, r in ((0, -96, 38), (-30, -76, 28), (30, -76, 28), (-8, -118, 24)):
        t.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{p["leaf"]}" {p["stk"]}/>')
    for cx, cy in ((-20, -88), (14, -104), (26, -78), (-34, -72), (2, -124)):
        t.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="{p["apple"]}" {p["stk"]}/>')
    t.append('</g>')
    return "".join(t)


def flowers(p):
    out = []
    for x, y, c in ((40, 318, p["fl1"]), (120, 336, p["fl2"]), (300, 330, p["fl1"]),
                    (420, 322, p["fl2"]), (360, 346, p["fl1"]), (190, 344, p["fl2"])):
        out.append(f'<g transform="translate({x},{y})"><circle cx="0" cy="0" r="5" fill="{c}" {p["stk"]}/>'
                   f'<circle cx="0" cy="0" r="2" fill="{p["fc"]}"/></g>')
    return "".join(out)


def scene(name, p, uid):
    stk = (f'stroke="{p["ol"]}" stroke-width="{p["ow"]}" stroke-linejoin="round"' if p.get("ol") else "")
    p = dict(p, stk=stk)
    defs = [
        f'<linearGradient id="{uid}sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{p["sky1"]}"/>'
        f'<stop offset="1" stop-color="{p["sky2"]}"/></linearGradient>',
        f'<linearGradient id="{uid}pond" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{p["pond1"]}"/>'
        f'<stop offset="1" stop-color="{p["pond2"]}"/></linearGradient>',
    ]
    if p.get("soft"):
        defs.append(f'<filter id="{uid}glow" x="-50%" y="-50%" width="200%" height="200%">'
                    f'<feGaussianBlur stdDeviation="9"/></filter>')
    if p.get("wob"):
        defs.append(f'<filter id="{uid}wob" x="-10%" y="-10%" width="120%" height="120%">'
                    f'<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="3" seed="4" result="n"/>'
                    f'<feDisplacementMap in="SourceGraphic" in2="n" scale="5" xChannelSelector="R" yChannelSelector="G"/></filter>')
        defs.append(f'<filter id="{uid}grain" x="0" y="0" width="100%" height="100%">'
                    f'<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="9"/>'
                    f'<feColorMatrix type="matrix" values="0 0 0 0 0.45  0 0 0 0 0.35  0 0 0 0 0.25  0 0 0 0.55 -0.12"/></filter>')
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 360" role="img" '
         f'aria-label="{name} style sample: a baby unicorn in a meadow beside a pond and an apple tree">']
    s.append("<defs>" + "".join(defs) + "</defs>")
    wob = f'filter="url(#{uid}wob)"' if p.get("wob") else ''
    s.append(f'<rect width="480" height="360" fill="url(#{uid}sky)"/>')
    if p.get("soft"):
        s.append(f'<circle cx="404" cy="62" r="46" fill="{p["sun"]}" opacity="0.55" filter="url(#{uid}glow)"/>')
    s.append(f'<g {wob}>')
    s.append(f'<circle cx="404" cy="62" r="28" fill="{p["sun"]}" {stk}/>')
    s.append(f'<ellipse cx="90" cy="70" rx="46" ry="14" fill="{p["cloud"]}" {stk}/>'
             f'<ellipse cx="120" cy="60" rx="30" ry="14" fill="{p["cloud"]}" {stk}/>')
    s.append(f'<path d="M0 230 C70 170 150 180 230 215 C310 180 400 170 480 220 L480 360 L0 360 Z" fill="{p["hill1"]}" {stk}/>')
    s.append(f'<path d="M0 270 C90 240 200 250 280 268 C360 250 430 252 480 270 L480 360 L0 360 Z" fill="{p["hill2"]}" {stk}/>')
    s.append(f'<ellipse cx="372" cy="306" rx="96" ry="30" fill="url(#{uid}pond)" {stk}/>')
    s.append(f'<path d="M330 304 q14 -6 28 0 M380 312 q16 -6 32 0" fill="none" stroke="{p["ripple"]}" '
             f'stroke-width="2.4" stroke-linecap="round"/>')
    s.append(apple_tree(p, 74, 288))
    s.append(flowers(p))
    s.append('</g>')
    s.append(creature(p["c"], 1.0, 232, 238, uid))
    if p.get("wob"):
        s.append(f'<rect width="480" height="360" filter="url(#{uid}grain)" opacity="0.5" '
                 f'style="mix-blend-mode:multiply" pointer-events="none"/>')
    s.append('</svg>')
    return "".join(s)


def variants(p, vs, uid):
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 130" role="img" '
         'aria-label="Three trait variants of the same creature built from swapped colour and mane layers">']
    if p.get("wob"):
        s.append(f'<defs><filter id="{uid}wob" x="-10%" y="-10%" width="120%" height="120%">'
                 f'<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="3" seed="4" result="n"/>'
                 f'<feDisplacementMap in="SourceGraphic" in2="n" scale="4" xChannelSelector="R" yChannelSelector="G"/>'
                 f'</filter></defs>')
    s.append(f'<rect width="480" height="130" fill="{p["strip"]}"/>')
    for i, (b, m, h) in enumerate(vs):
        c = dict(p["c"], body=b, mane=m, belly=b, muzzle=b, horn=h)
        s.append(creature(c, 0.5, 90 + i * 150, 84, uid))
    s.append('</svg>')
    return "".join(s)


pastel = dict(sky1="#e9e1ff", sky2="#ffe9ee", sun="#ffe9a8", cloud="#ffffff", hill1="#cfeedd", hill2="#b8e3c9",
              pond1="#cfeaff", pond2="#a9d3f5", ripple="#ffffff", trunk="#d9b69a", leaf="#bfe7c5", apple="#ff9fb2",
              fl1="#ffb7d1", fl2="#cdbbff", fc="#fff3a6", soft=True, strip="#f7f2ff",
              c=dict(body="#fff5f8", belly="#fff5f8", muzzle="#ffe4ec", mane="#c9b6f2", horn="#ffe08a",
                     hoof="#e9d5f5", shadow="#8aa8a0", shadow_o=0.22, blush="#ff9bb3", eye="#4b3a6b"))
bold = dict(sky1="#6fd6ff", sky2="#6fd6ff", sun="#ffd23f", cloud="#ffffff", hill1="#2fbf71", hill2="#8be04a",
            pond1="#34a8ff", pond2="#34a8ff", ripple="#ffffff", trunk="#a05a2c", leaf="#33b864", apple="#ff3b5c",
            fl1="#ff4fa3", fl2="#ffd23f", fc="#ffffff", ol="#2a1648", ow=4, strip="#ffe9f6",
            c=dict(body="#ffffff", belly="#ffffff", muzzle="#fff0f6", mane="#ff4fa3", horn="#ffd23f",
                   hoof="#7b3fe4", shadow="#2a1648", shadow_o=0.25, blush="#ff6fa8", eye="#2a1648",
                   ol="#2a1648", ow=4))
paint = dict(sky1="#f3dfc4", sky2="#e8c8b4", sun="#f2b868", cloud="#fbf0e0", hill1="#a9b98c", hill2="#8ea272",
             pond1="#9cb8b4", pond2="#6f938f", ripple="#e9f0e6", trunk="#7a5236", leaf="#7d9163", apple="#b2493f",
             fl1="#c97b8e", fl2="#d9a24f", fc="#fbf0e0", ol="#4a3426", ow=1.6, wob=True, strip="#efe2cf",
             c=dict(body="#f4e9da", belly="#f4e9da", muzzle="#ecd9c4", mane="#b9718a", horn="#d9a24f",
                    hoof="#7a5236", shadow="#4a3426", shadow_o=0.3, blush="#c97b8e", eye="#3a2a24",
                    ol="#4a3426", ow=1.6, wob=True))

vs = {"pastel": [("#fff5f8", "#c9b6f2", "#ffe08a"), ("#fff6e3", "#f7b9c8", "#ffd1a8"), ("#eaf7ff", "#a9e0d0", "#fff1a8")],
      "bold": [("#ffffff", "#ff4fa3", "#ffd23f"), ("#ffe066", "#7b3fe4", "#ff7a00"), ("#8fe3ff", "#ff7a00", "#ffffff")],
      "paint": [("#f4e9da", "#b9718a", "#d9a24f"), ("#e8d8c0", "#6e8f7a", "#c6955b"), ("#dce3e8", "#c6955b", "#8f6a3a")]}

for key, p, name in (("pastel", pastel, "Soft pastel"), ("bold", bold, "Bold graphic"),
                     ("paint", paint, "Painterly storybook")):
    with open(os.path.join(OUT, f"{key}-scene.svg"), "w", encoding="utf-8") as fh:
        fh.write(scene(name, p, key[0]))
    with open(os.path.join(OUT, f"{key}-variants.svg"), "w", encoding="utf-8") as fh:
        fh.write(variants(p, vs[key], key[0] + "v"))
print("ok")
