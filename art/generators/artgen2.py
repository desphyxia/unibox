import sys, os

OUT = sys.argv[1]

# ---- shared geometry (viewBox 0 0 600 520) -------------------------------------------------
BODY = "M150 330 C150 268 222 238 300 243 C382 248 432 280 432 342 C432 402 382 434 300 436 C220 438 150 402 150 330 Z"
NECK = "M352 262 C336 292 330 318 332 346 L430 350 C446 336 456 310 460 288 Z"
HEAD = "M350 200 C348 150 392 112 444 116 C490 120 520 150 524 190 C526 214 540 230 540 252 C540 282 516 302 486 304 C452 306 420 298 396 278 C366 254 351 232 350 200 Z"
EAR_BACK = "M368 136 C352 92 362 58 388 46 C404 80 410 108 408 130 Z"
EAR_BACK_IN = "M376 128 C366 98 372 74 386 62 C396 86 399 106 398 124 Z"
EAR_FRONT = "M448 113 C456 72 480 52 504 54 C504 88 494 110 482 126 Z"
EAR_FRONT_IN = "M456 112 C462 84 478 68 494 68 C494 92 486 108 476 120 Z"
HORN = "M410 120 C414 84 422 54 432 22 C440 54 446 86 448 120 Z"
HORN_LINES = ["M413 104 Q430 96 446 104", "M415 86 Q430 78 444 86", "M419 68 Q431 61 441 68", "M423 50 Q432 44 438 50"]
MANE_BACK = "M374 116 C322 86 250 118 214 190 C188 242 200 292 178 334 C230 324 272 292 292 256 C316 214 352 192 376 172 Z"
MANE_S1 = "M366 130 C312 110 256 148 232 204 C220 238 222 270 214 302 C246 284 272 252 288 224 C310 188 340 170 364 160 Z"
MANE_S2 = "M356 150 C314 140 276 170 262 210 C254 236 256 258 250 278 C272 264 288 238 298 216 C316 192 336 180 354 172 Z"
FORELOCK = "M374 108 C400 92 436 94 458 108 C444 118 430 134 422 164 C412 140 394 128 374 122 Z"
CURL = "M442 108 C478 98 508 122 512 156 C494 138 472 134 452 140 Z"
TAIL = "M170 302 C122 280 60 290 44 342 C30 388 62 428 100 432 C80 410 78 380 96 358 C112 338 142 330 174 336 Z"
TAIL_S1 = "M164 308 C126 292 80 304 66 344 C56 376 74 404 98 412 C90 392 92 372 106 356 C120 340 146 336 168 340 Z"
LEG_FAR_FRONT = "M326 398 C322 430 324 458 326 476 L354 476 C356 458 358 430 356 398 Z"
LEG_FRONT = "M362 394 C358 430 360 458 362 476 L398 476 C400 458 402 430 400 394 Z"
LEG_BACK_A = "M190 396 C186 430 188 458 190 476 L224 476 C226 458 228 430 226 396 Z"
LEG_BACK_B = "M236 400 C232 430 234 458 236 476 L266 476 C268 458 270 430 268 400 Z"
HOOF = lambda x, w: f"M{x-2} 470 Q{x+w/2} 460 {x+w+2} 470 L{x+w} 486 Q{x+w/2} 492 {x} 486 Z"


def star(x, y, r, fill, op=1.0):
    return (f'<path d="M{x} {y-r} Q{x+r*0.15} {y-r*0.15} {x+r} {y} Q{x+r*0.15} {y+r*0.15} {x} {y+r} '
            f'Q{x-r*0.15} {y+r*0.15} {x-r} {y} Q{x-r*0.15} {y-r*0.15} {x} {y-r} Z" fill="{fill}" opacity="{op}"/>')


def build(P, uid):
    u = uid
    ol = P.get("ol")
    stroke = (f'stroke="{ol}" stroke-width="{P["ow"]}" stroke-linejoin="round" stroke-linecap="round"' if ol else "")
    defs = []

    def lg(id_, stops, x1=0, y1=0, x2=0, y2=1):
        s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
        defs.append(f'<linearGradient id="{u}{id_}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{s}</linearGradient>')

    def rg(id_, stops, cx=0.5, cy=0.4, r=0.7):
        s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
        defs.append(f'<radialGradient id="{u}{id_}" cx="{cx}" cy="{cy}" r="{r}">{s}</radialGradient>')

    lg("bg", P["bg"])
    rg("body", P["body_g"], 0.42, 0.3, 0.8)
    rg("head", P["head_g"], 0.5, 0.35, 0.75)
    lg("mane1", P["mane1"], 0, 0, 1, 1)
    lg("mane2", P["mane2"], 0, 0, 1, 1)
    lg("mane3", P["mane3"], 0, 0, 1, 1)
    lg("horn", P["horn_g"], 0, 0, 0, 1)
    lg("hoof", P["hoof_g"], 0, 0, 0, 1)
    rg("iris", P["iris_g"], 0.5, 0.35, 0.7)
    rg("ground", [(0, P["ground1"]), (1, P["ground2"])], 0.5, 0.5, 0.6)
    defs.append(f'<filter id="{u}b8" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="8"/></filter>')
    defs.append(f'<filter id="{u}b14" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="14"/></filter>')
    defs.append(f'<filter id="{u}b3" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3"/></filter>')
    defs.append(f'<clipPath id="{u}cbody"><path d="{BODY}"/></clipPath>')
    defs.append(f'<clipPath id="{u}chead"><path d="{HEAD}"/></clipPath>')
    if P.get("paint"):
        # watercolour: wobbly edges, darker pooled edge, paper grain
        defs.append(
            f'<filter id="{u}wc" x="-5%" y="-5%" width="110%" height="110%" color-interpolation-filters="sRGB">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="3" seed="7" result="n"/>'
            f'<feDisplacementMap in="SourceGraphic" in2="n" scale="9" xChannelSelector="R" yChannelSelector="G" result="d"/>'
            f'<feMorphology in="d" operator="erode" radius="2.2" result="e"/>'
            f'<feGaussianBlur in="e" stdDeviation="2.4" result="eb"/>'
            f'<feComposite in="d" in2="eb" operator="out" result="edge"/>'
            f'<feColorMatrix in="edge" type="matrix" values="0.55 0 0 0 0  0 0.45 0 0 0  0 0 0.4 0 0  0 0 0 0.85 0" result="edgeDark"/>'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves="3" seed="3" result="g"/>'
            f'<feColorMatrix in="g" type="matrix" values="0 0 0 0 0.45  0 0 0 0 0.36  0 0 0 0 0.28  0 0 0 0.5 -0.12" result="grain"/>'
            f'<feComposite in="grain" in2="d" operator="in" result="grainIn"/>'
            f'<feMerge><feMergeNode in="d"/><feMergeNode in="edgeDark"/><feMergeNode in="grainIn"/></feMerge></filter>')
        defs.append(
            f'<filter id="{u}paper" x="0" y="0" width="100%" height="100%">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed="11"/>'
            f'<feColorMatrix type="matrix" values="0 0 0 0 0.5  0 0 0 0 0.4  0 0 0 0 0.3  0 0 0 0.45 -0.1"/></filter>')
        defs.append(
            f'<filter id="{u}blotch" x="0" y="0" width="100%" height="100%">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.006" numOctaves="2" seed="21"/>'
            f'<feColorMatrix type="matrix" values="0 0 0 0 0.55  0 0 0 0 0.35  0 0 0 0 0.3  0 0 0 0.9 -0.35"/></filter>')
    wc = f'filter="url(#{u}wc)"' if P.get("paint") else ""

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 520" role="img" aria-label="{P["label"]}">']
    s.append("<defs>" + "".join(defs) + "</defs>")
    s.append(f'<rect width="600" height="520" fill="url(#{u}bg)"/>')
    if P.get("paint"):
        s.append(f'<rect width="600" height="520" filter="url(#{u}blotch)" opacity="0.35" style="mix-blend-mode:multiply"/>')
    # ground and soft shadow
    s.append(f'<ellipse cx="300" cy="484" rx="270" ry="36" fill="url(#{u}ground)" opacity="{P["ground_o"]}"/>')
    s.append(f'<ellipse cx="296" cy="484" rx="170" ry="15" fill="{P["shadow"]}" opacity="{P["shadow_o"]}" filter="url(#{u}b8)"/>')

    s.append(f'<g {wc}>')
    # tail
    s.append(f'<path d="{TAIL}" fill="url(#{u}mane1)" {stroke}/>')
    s.append(f'<path d="{TAIL_S1}" fill="url(#{u}mane2)" opacity="0.9"/>')
    s.append(f'<path d="M168 318 C130 308 96 320 84 346" fill="none" stroke="{P["strand"]}" stroke-width="3" stroke-linecap="round" opacity="0.7"/>')
    s.append(f'<path d="M160 326 C132 322 108 334 100 356" fill="none" stroke="{P["strand"]}" stroke-width="2.4" stroke-linecap="round" opacity="0.6"/>')
    # far legs (darker)
    for path, x in ((LEG_BACK_A, 190), (LEG_FAR_FRONT, 326)):
        s.append(f'<path d="{path}" fill="{P["far_leg"]}" {stroke}/>')
        s.append(f'<path d="{HOOF(x, 30 if x < 300 else 28)}" fill="url(#{u}hoof)" {stroke}/>')
    # neck (under the body so its edge is hidden)
    s.append(f'<path d="{NECK}" fill="url(#{u}body)" {stroke}/>')
    # near legs (under the body so the tops are hidden)
    for path, x, w in ((LEG_BACK_B, 236, 30), (LEG_FRONT, 362, 36)):
        s.append(f'<path d="{path}" fill="url(#{u}body)" {stroke}/>')
        s.append(f'<path d="{HOOF(x, w)}" fill="url(#{u}hoof)" {stroke}/>')
        s.append(f'<path d="M{x+4} 468 Q{x+w/2} 462 {x+w-4} 468" fill="none" stroke="{P["hi"]}" stroke-width="2.2" stroke-linecap="round" opacity="0.8"/>')
    # body
    s.append(f'<path d="{BODY}" fill="url(#{u}body)" {stroke}/>')
    s.append(f'<g clip-path="url(#{u}cbody)">')
    s.append(f'<ellipse cx="292" cy="438" rx="150" ry="46" fill="{P["belly_shade"]}" opacity="0.7" filter="url(#{u}b14)"/>')
    s.append(f'<ellipse cx="272" cy="260" rx="110" ry="14" fill="{P["hi"]}" opacity="0.85" filter="url(#{u}b8)"/>')
    s.append(f'<ellipse cx="176" cy="340" rx="30" ry="70" fill="{P["belly_shade"]}" opacity="0.5" filter="url(#{u}b14)"/>')
    s.append('</g>')
    # back ear (scaled with the head)
    s.append('<g transform="translate(440 210) scale(0.88) translate(-440 -210)">')
    s.append(f'<path d="{EAR_BACK}" fill="url(#{u}body)" {stroke}/><path d="{EAR_BACK_IN}" fill="{P["ear_in"]}" opacity="0.85"/>')
    s.append('</g>')
    # mane behind head
    s.append(f'<path d="{MANE_BACK}" fill="url(#{u}mane1)" {stroke}/>')
    s.append(f'<path d="{MANE_S1}" fill="url(#{u}mane2)" opacity="0.92"/>')
    s.append(f'<path d="{MANE_S2}" fill="url(#{u}mane3)" opacity="0.9"/>')
    for d in ("M350 140 C300 134 262 170 244 220", "M340 156 C304 154 278 182 266 222", "M330 170 C300 172 284 196 276 228"):
        s.append(f'<path d="{d}" fill="none" stroke="{P["strand"]}" stroke-width="2.6" stroke-linecap="round" opacity="0.65"/>')
    # head
    s.append('<g transform="translate(440 210) scale(0.88) translate(-440 -210)">')
    s.append(f'<path d="{HEAD}" fill="url(#{u}head)" {stroke}/>')
    s.append(f'<g clip-path="url(#{u}chead)">')
    s.append(f'<ellipse cx="430" cy="318" rx="100" ry="20" fill="{P["belly_shade"]}" opacity="0.65" filter="url(#{u}b8)"/>')
    s.append(f'<ellipse cx="456" cy="132" rx="70" ry="12" fill="{P["hi"]}" opacity="0.8" filter="url(#{u}b8)"/>')
    s.append(f'<ellipse cx="498" cy="246" rx="24" ry="20" fill="{P["blush"]}" opacity="{P["blush_o"]}" filter="url(#{u}b8)"/>')
    s.append(f'<ellipse cx="414" cy="244" rx="20" ry="15" fill="{P["blush"]}" opacity="{P["blush_o"]*0.8}" filter="url(#{u}b8)"/>')
    s.append('</g>')
    # muzzle detail (inside the outline)
    s.append(f'<ellipse cx="525" cy="258" rx="5.5" ry="4" fill="{P["nostril"]}" opacity="0.85"/>')
    s.append(f'<path d="M498 284 C508 293 522 292 531 282" fill="none" stroke="{P["nostril"]}" stroke-width="2.6" stroke-linecap="round"/>')
    # front ear
    s.append(f'<path d="{EAR_FRONT}" fill="url(#{u}body)" {stroke}/><path d="{EAR_FRONT_IN}" fill="{P["ear_in"]}" opacity="0.85"/>')
    # eyes: the same construction twice, the far eye narrower for the 3/4 view
    def eye(cx, cy, rx, ry, hx):
        o = []
        o.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{P["eye_white"]}"/>')
        o.append(f'<ellipse cx="{cx + 2}" cy="{cy + 2}" rx="{rx * 0.78}" ry="{ry * 0.84}" fill="url(#{u}iris)"/>')
        o.append(f'<ellipse cx="{cx + 3}" cy="{cy + 4}" rx="{rx * 0.4}" ry="{ry * 0.5}" fill="{P["pupil"]}"/>')
        o.append(f'<circle cx="{cx + hx}" cy="{cy - ry * 0.35}" r="{rx * 0.3}" fill="#fff"/>')
        o.append(f'<circle cx="{cx - rx * 0.28}" cy="{cy + ry * 0.55}" r="{rx * 0.15}" fill="#fff" opacity="0.9"/>')
        o.append(f'<path d="M{cx - rx - 2} {cy - ry * 0.4} Q{cx} {cy - ry - 9} {cx + rx + 2} {cy - ry * 0.4}" fill="none" stroke="{P["lash"]}" stroke-width="4" stroke-linecap="round"/>')
        o.append(f'<path d="M{cx + rx + 2} {cy - ry * 0.4} q8 -3 11 -11" fill="none" stroke="{P["lash"]}" stroke-width="2.6" stroke-linecap="round"/>')
        o.append(f'<path d="M{cx + rx * 0.4} {cy - ry - 4} q5 -6 5 -13" fill="none" stroke="{P["lash"]}" stroke-width="2.6" stroke-linecap="round"/>')
        return "".join(o)
    s.append(eye(404, 198, 14, 22, 5))
    s.append(eye(466, 200, 19, 26, 7))
    # horn
    s.append(f'<path d="{HORN}" fill="url(#{u}horn)" {stroke}/>')
    for d in HORN_LINES:
        s.append(f'<path d="{d}" fill="none" stroke="{P["horn_line"]}" stroke-width="2.4" stroke-linecap="round" opacity="0.8"/>')
    s.append(f'<path d="M424 112 C426 84 430 60 432 36" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity="0.6"/>')
    # forelock and curl
    s.append(f'<path d="{FORELOCK}" fill="url(#{u}mane2)" {stroke}/>')
    s.append(f'<path d="{CURL}" fill="url(#{u}mane1)" {stroke}/>')
    s.append(f'<path d="M386 112 C408 102 432 104 446 114" fill="none" stroke="{P["strand"]}" stroke-width="2.6" stroke-linecap="round" opacity="0.7"/>')
    s.append('</g>')
    s.append('</g>')
    # sparkles
    for x, y, r, op in ((470, 56, 12, 0.95), (500, 96, 7, 0.8), (396, 36, 8, 0.8), (540, 40, 6, 0.7)):
        s.append(star(x, y, r, P["spark"], op))
    if P.get("paint"):
        s.append(f'<rect width="600" height="520" filter="url(#{u}paper)" opacity="0.55" style="mix-blend-mode:multiply" pointer-events="none"/>')
    s.append("</svg>")
    return "".join(s)


pastel = dict(
    label="Soft pastel unicorn foal, detailed study",
    bg=[(0, "#ece4ff"), (0.6, "#fde8f1"), (1, "#e6f5ee")],
    ground1="#cdeedd", ground2="#b5e0c8", ground_o=0.9, shadow="#6f8f86", shadow_o=0.35,
    body_g=[(0, "#ffffff"), (0.55, "#fff1f6"), (1, "#f6d9e7")],
    head_g=[(0, "#ffffff"), (0.6, "#fff1f6"), (1, "#f3d3e4")],
    mane1=[(0, "#e7dcff"), (0.5, "#b69df3"), (1, "#8f74e0")],
    mane2=[(0, "#fbd6ee"), (0.6, "#e5a9e8"), (1, "#b78bf0")],
    mane3=[(0, "#d9f1ff"), (0.6, "#a8d2f7"), (1, "#8fb4ee")],
    horn_g=[(0, "#fff7c9"), (0.6, "#ffe08a"), (1, "#f4be5a")], horn_line="#e7a93f",
    hoof_g=[(0, "#ead9f7"), (1, "#c8aee8")],
    iris_g=[(0, "#b7a2ff"), (0.55, "#7a5fe0"), (1, "#3b2a85")],
    pupil="#1d1245", eye_white="#ffffff", lash="#3a2a6e", nostril="#c78aa8", blush="#ff9fc0", blush_o=0.75,
    ear_in="#ffc4d8", far_leg="#f3d6e3", belly_shade="#f0c3da", hi="#ffffff", strand="#ffffff", spark="#fff3a8",
    ol=None)
paint = dict(
    label="Painterly storybook unicorn foal, detailed study",
    bg=[(0, "#f4e2c6"), (0.7, "#ecd0b6"), (1, "#d7c59f")],
    ground1="#a9b98c", ground2="#8ea272", ground_o=0.85, shadow="#4a3426", shadow_o=0.32,
    body_g=[(0, "#fbf3e6"), (0.55, "#f0e2cd"), (1, "#d9c0a2")],
    head_g=[(0, "#fbf3e6"), (0.6, "#f0e2cd"), (1, "#d6bc9c")],
    mane1=[(0, "#c78aa0"), (0.5, "#a45f7e"), (1, "#74405c")],
    mane2=[(0, "#e0a9b7"), (0.6, "#bf7790"), (1, "#8e506b")],
    mane3=[(0, "#e8c27a"), (0.6, "#c7954a"), (1, "#8f6a3a")],
    horn_g=[(0, "#f1d089"), (0.6, "#d9a24f"), (1, "#a8742e")], horn_line="#8f5f24",
    hoof_g=[(0, "#9a6a46"), (1, "#5c3b25")],
    iris_g=[(0, "#9a6a58"), (0.55, "#5b3a31"), (1, "#2a1a17")],
    pupil="#1b100e", eye_white="#fbf3e6", lash="#3a2a24", nostril="#8e5a4a", blush="#d88b9a", blush_o=0.7,
    ear_in="#d7a0a5", far_leg="#dcc6a8", belly_shade="#cdb08e", hi="#fffaf0", strand="#f7e7d4", spark="#fbe3a2",
    ol="#4a3426", ow=1.8, paint=True)

for key, P in (("pastel", pastel), ("paint", paint)):
    with open(os.path.join(OUT, f"{key}-detail.svg"), "w", encoding="utf-8") as fh:
        fh.write(build(P, key + "d"))
print("ok")
