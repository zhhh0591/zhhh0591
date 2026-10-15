#!/usr/bin/env python3
"""Builds assets/zutomayo.svg, the moving banner at the top of github.com/zhhh0591.

Four official ZUTOMAYO MV frames (YouTube's own stills of each video) take turns like shots
in a music video: a hard cut, a quick push that settles into a slow camera move, the song's
name in the corner. A GitHub README can only show images, and an <img> SVG loads nothing from
outside, so the frames are embedded. The README points at this file through jsDelivr pinned
to a tag, which GitHub proxies through camo (whose CSP allows the embedded data: images).

Frames are read from frames/<video id>-<frame>.jpg (git-ignored); `--urls` prints where each
comes from. `--preview` writes assets/zutomayo-preview.svg with the frames hotlinked instead,
for looking at it inline in a browser. Song titles are outlines from Hiragino (macOS), so
they look the same everywhere.

usage: python3 -I tools/banner.py [--preview | --urls]
"""
import base64
import pathlib
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTCollection

ROOT = pathlib.Path(__file__).resolve().parent.parent
W, H, R = 1280, 640, 9          # R 9 draws about GitHub's own 6 px card corner at README width
HOLD = 4.0                      # seconds per shot
SNAP, SNAP_K = .6, .022         # each shot opens with a quick push of this much scale, then drifts
IW, IX = 1328, -24              # frames are laid 24 px wider than the card on each side, so a
IH = IW * 9 / 16                # drifting frame never shows the card's edge
TITLE = ('/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc', 0)
BAND = ('/System/Library/Fonts/ヒラギノ角ゴシック W5.ttc', 0)

# (song, video id, frame, image y, camera focus x/y, scale from→to, drift x from→to)
# Picked for faces with no burned-in lyrics, logos or letterboxing; the first is also the one
# that stays when motion is reduced.
SLIDES = [
    ('イチジク煙', '4LDQXYTfWjA', 'maxres3', -40, 534, 300, (1.0, 1.06), (8, -10)),
    ('嘘じゃない', 'GfDXqY-V0EY', 'maxresdefault', -15, 547, 388, (1.06, 1.0), (-8, 10)),
    ('イチジク煙', '4LDQXYTfWjA', 'maxres2', -40, 481, 371, (1.0, 1.06), (10, -8)),
    ('勘冴えて悔しいわ', '4QePrv24TBU', 'maxres2', -50, 773, 323, (1.06, 1.0), (-10, 8)),
]
N = len(SLIDES)
CYCLE = N * HOLD


def num(v):
    s = f'{v:.1f}'
    s = s[:-2] if s.endswith('.0') else s
    return '0' if s == '-0' else s


_faces = {}


def outline(key, text, size, x, y, track=0.0):
    """Path data for `text` set at `size` from baseline-left (x, y), and where it ends."""
    if key not in _faces:
        col = TTCollection(key[0])
        f = col.fonts[key[1]]
        _faces[key] = (col, f, f.getGlyphSet(), f.getBestCmap())
    _, f, gs, cmap = _faces[key]
    s = size / f['head'].unitsPerEm
    pen = SVGPathPen(gs, ntos=num)
    for ch in text:
        g = cmap[ord(ch)]
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, x, y)))
        x += f['hmtx'][g][0] * s + track
    return pen.getCommands(), x - track


def pct(t):
    return '0%' if t <= 0 else '100%' if t >= CYCLE else f'{t / CYCLE * 100:.3f}'.rstrip('0').rstrip('.') + '%'


def tf(s, dx):
    return f'transform:translateX({num(dx)}px) scale({round(s, 4)})'


def shot_css(i):
    """Shot i is on screen for [i*HOLD, (i+1)*HOLD) and hidden otherwise (step-end makes each
    change land exactly on its keyframe: a cut, never a crossfade). It opens with a quick
    eased push of SNAP_K, then moves at a constant rate to the end of its time."""
    *_, (s0, s1), (d0, d1) = SLIDES[i]
    a, b = i * HOLD, (i + 1) * HOLD
    sign = 1 if s1 >= s0 else -1
    sq, dq = s0 + sign * SNAP_K, d0 + (d1 - d0) * SNAP / HOLD
    ease, lin = 'animation-timing-function:cubic-bezier(.2,.75,.35,1)', 'animation-timing-function:linear'
    kb = (f'@keyframes kb{i}{{0%,{pct(a)}{{{tf(s0, d0)};{ease}}}{pct(a + SNAP)}{{{tf(sq, dq)};{lin}}}'
          f'{pct(b)},100%{{{tf(s1, d1)}}}}}')
    vis = (f'@keyframes on{i}{{0%{{visibility:{"visible" if i == 0 else "hidden"}}}'
           + (f'{pct(a)}{{visibility:visible}}' if i else '')
           + (f'{pct(b)},100%{{visibility:hidden}}' if i < N - 1 else '100%{visibility:visible}') + '}')
    return kb + vis


def credit_css(i):
    """Shot i's credit rises in just after its cut and goes with it."""
    a, b = i * HOLD, (i + 1) * HOLD
    return (f'@keyframes cr{i}{{0%,{pct(a + .08)}{{opacity:0;transform:translateY(8px)}}'
            f'{pct(a + .5)},100%{{opacity:1;transform:none}}}}')


def src(vid, frame, preview):
    if preview:
        return f'https://i.ytimg.com/vi/{vid}/{frame}.jpg'
    return 'data:image/jpeg;base64,' + base64.b64encode((ROOT / 'frames' / f'{vid}-{frame}.jpg').read_bytes()).decode()


def build(preview=False):
    a = []
    p = a.append
    p(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t">')
    p('<title id="t">ZUTOMAYO (ずっと真夜中でいいのに。): frames from the official music videos for '
      + ', '.join(dict.fromkeys(s[0] for s in SLIDES)) + '.</title>')
    css = ['@keyframes show{from{opacity:0}to{opacity:1}}.show{animation:show .7s ease-out both}']
    for i, (*_, fx, fy, _s, _d) in enumerate(SLIDES):
        css.append(shot_css(i) + credit_css(i))
        css.append(f'.s{i}{{transform-origin:{fx}px {fy}px;animation:kb{i} {CYCLE}s infinite,on{i} {CYCLE}s step-end infinite}}')
        css.append(f'.c{i}{{animation:on{i} {CYCLE}s step-end infinite}}.c{i}>g{{animation:cr{i} {CYCLE}s ease-out infinite}}')
    # phones: the README is ~330 px wide there, so the credit is drawn 2.2x and the band dropped
    # (an <img> SVG's media queries see its own width)
    css.append('@media (max-width:560px){.credits{transform:translate(40px,600px) scale(2.2) translate(-40px,-600px)}.band{display:none}}')
    # with reduced motion the first shot and its credit simply stay
    hidden = ','.join(f'.s{i},.c{i}' for i in range(1, N))
    css.append(f'@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}{hidden}{{display:none}}}}')
    p('<style>' + ''.join(css) + '</style>')

    p('<defs>')
    p(f'<clipPath id="card"><rect width="{W}" height="{H}" rx="{R}"/></clipPath>')
    # edges darkened by narrow strips rather than a full-card vignette: same frame on a white page,
    # far less to fill on every animation frame
    for gid, (x1, y1, x2, y2), op in (('top', (0, 0, 0, 80), .34), ('lft', (0, 0, 70, 0), .26), ('rgt', (W, 0, W - 70, 0), .26)):
        p(f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" gradientUnits="userSpaceOnUse">'
          f'<stop offset="0" stop-color="#0d0a16" stop-opacity="{op}"/><stop offset="1" stop-color="#0d0a16" stop-opacity="0"/></linearGradient>')
    p(f'<linearGradient id="foot" x1="0" y1="{H - 190}" x2="0" y2="{H}" gradientUnits="userSpaceOnUse">'
      '<stop offset="0" stop-color="#0d0a16" stop-opacity="0"/><stop offset="1" stop-color="#0d0a16" stop-opacity=".62"/></linearGradient>')
    p('</defs>')
    p(f'<g class="show" clip-path="url(#card)"><rect width="{W}" height="{H}" fill="#14111d"/>')
    for i, (song, vid, frame, iy, *_r) in enumerate(SLIDES):
        p(f'<g class="s{i}"><image href="{src(vid, frame, preview)}" x="{IX}" y="{iy}" width="{IW}" height="{num(IH)}" preserveAspectRatio="xMidYMid slice"/></g>')
    p(f'<rect width="{W}" height="80" fill="url(#top)"/><rect width="70" height="{H}" fill="url(#lft)"/>'
      f'<rect x="{W - 70}" width="70" height="{H}" fill="url(#rgt)"/><rect y="{H - 190}" width="{W}" height="190" fill="url(#foot)"/>')
    p('<g class="credits">')
    for i, (song, *_r) in enumerate(SLIDES):
        d, end = outline(TITLE, song, 22, 40, H - 40, track=.6)
        d2, _ = outline(BAND, 'ずっと真夜中でいいのに。', 14.5, end + 14, H - 41, track=.4)
        p(f'<g class="c{i}"><g><path d="{d}" fill="#fff"/><path class="band" d="{d2}" fill="#fff" fill-opacity=".72"/></g></g>')
    p('</g></g>')
    p(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="{R - .5}" fill="none" stroke="#fff" stroke-opacity=".08"/>')
    p('</svg>')
    return '\n'.join(a)


if __name__ == '__main__':
    if '--urls' in sys.argv:
        for song, vid, frame, *_ in SLIDES:
            print(f'frames/{vid}-{frame}.jpg  https://i.ytimg.com/vi/{vid}/{frame}.jpg  ({song})')
        sys.exit()
    preview = '--preview' in sys.argv
    out = ROOT / 'assets' / ('zutomayo-preview.svg' if preview else 'zutomayo.svg')
    svg = build(preview)
    out.write_text(svg, encoding='utf-8')
    print(out.relative_to(ROOT), f'{len(svg.encode()) / 1024:.1f} KB')
