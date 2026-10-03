"""Render the reactor (base, arm, pendulum STLs placed as in the URDF) to a dark SVG with annotations."""
import math, struct, sys
import numpy as np

AZ = float(sys.argv[1]) if len(sys.argv) > 1 else -58
EL = float(sys.argv[2]) if len(sys.argv) > 2 else 20
THETA = math.radians(float(sys.argv[3]) if len(sys.argv) > 3 else 28)
ALPHA = math.radians(float(sys.argv[4]) if len(sys.argv) > 4 else 28)

def load(fn):
    b = open(fn, 'rb').read()
    n = struct.unpack('<I', b[80:84])[0]
    a = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('x', '<u2')]))
    return a['v'].astype(float) / 1000.0   # mm -> m (URDF scale 0.001)

def Rz(t): c, s = math.cos(t), math.sin(t); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
def Rx(t): c, s = math.cos(t), math.sin(t); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

# URDF chain
T_arm_R, T_arm_p = Rz(THETA), np.array([0, 0, 0.305])
piv_local = np.array([0.250, 0, 0.045])
R_pend = T_arm_R @ Rx(ALPHA)
p_piv = T_arm_p + T_arm_R @ piv_local
def place(v, R, p): return v @ R.T + p

parts = [
    ('base', place(load('base.stl'), np.eye(3), np.zeros(3)), (96, 102, 114)),
    ('arm', place(load('arm.stl'), T_arm_R, T_arm_p), (150, 158, 170)),
    ('pendulum', place(load('pendulum.stl') + np.array([0, 0, 0.150]), R_pend, p_piv), (214, 218, 224)),
]

# camera (orthographic)
az, el = math.radians(AZ), math.radians(EL)
d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])  # towards camera
f = -d
r = np.cross(f, [0, 0, 1]); r /= np.linalg.norm(r)
u = np.cross(r, f)
light = np.array([0.35, -0.55, 0.9]); light /= np.linalg.norm(light)

W, H = 1000, 640
allv = np.concatenate([v.reshape(-1, 3) for _, v, _ in parts] + [np.array([[0, 0, 0.62], [0, 0, 0], p_piv + [0, 0, 0.40]])])
sx, sy = allv @ r, allv @ u
BOX = (60, 112, 600, 522)   # x0, y0, x1, y1 available for the model
SCALE = min((BOX[2] - BOX[0]) / (sx.max() - sx.min()), (BOX[3] - BOX[1]) / (sy.max() - sy.min()))
OX = (BOX[0] + BOX[2]) / 2 - SCALE * (sx.max() + sx.min()) / 2
OY = (BOX[1] + BOX[3]) / 2 + SCALE * (sy.max() + sy.min()) / 2

def proj(p):
    p = np.atleast_2d(p)
    return np.stack([OX + SCALE * (p @ r), OY - SCALE * (p @ u)], axis=-1)

tris = []
for name, v, col in parts:
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    ln = np.linalg.norm(n, axis=1); ok = ln > 1e-12
    v, n = v[ok], n[ok] / ln[ok][:, None]
    vis = n @ d > 0
    v, n = v[vis], n[vis]
    shade = 0.28 + 0.72 * np.clip(n @ light, 0, 1) ** 0.9
    depth = (v.mean(1) @ d)
    for tri, s, z in zip(v, shade, depth):
        c = tuple(int(min(255, ch * s)) for ch in col)
        tris.append((z, tri, c))
tris.sort(key=lambda t: t[0])

def hexc(c): return '#%02x%02x%02x' % c
paths, cur, curc = [], [], None
for z, tri, c in tris:
    q = (round(c[0] / 6) * 6, round(c[1] / 6) * 6, round(c[2] / 6) * 6)
    q = tuple(min(255, x) for x in q)
    pts = proj(tri)
    if abs((pts[1][0]-pts[0][0])*(pts[2][1]-pts[0][1])-(pts[2][0]-pts[0][0])*(pts[1][1]-pts[0][1])) < 0.6: continue
    seg = 'M' + 'L'.join(f'{x:.1f} {y:.1f}'.replace('.0 ', ' ') for x, y in pts) + 'Z'
    if q != curc and cur:
        paths.append((curc, ''.join(cur))); cur = []
    curc = q; cur.append(seg)
if cur: paths.append((curc, ''.join(cur)))
mesh = '\n'.join(f'<path d="{d_}" fill="{hexc(c)}" stroke="{hexc(c)}"/>' for c, d_ in paths)

# ---------------- annotations (all from the URDF geometry) ----------------
def P(p): x, y = proj(np.array(p))[0]; return x, y
YEL, ORA, TXT, MUT = '#ffd21f', '#ff7a2e', '#ededed', '#9c9c9c'
ann = []
# motor axis (world z) through the base
a0, a1 = P([0, 0, 0.0]), P([0, 0, 0.62])
ann.append(f'<line x1="{a0[0]:.1f}" y1="{a0[1]:.1f}" x2="{a1[0]:.1f}" y2="{a1[1]:.1f}" stroke="{YEL}" stroke-width="2" stroke-dasharray="7 6"/>')
ann.append(f'<path d="M{a1[0]:.1f} {a1[1]:.1f} l-6 12 l12 0 Z" fill="{YEL}"/>')
ann.append(f'<text x="{a1[0] + 12:.1f}" y="{a1[1] + 8:.1f}" fill="{YEL}" font-size="17" font-weight="600">+z · motor axis</text>')
# theta arc at the arm height, from world +x to the arm direction
rad = 0.16
pts = [P([rad * math.cos(t), rad * math.sin(t), 0.305]) for t in np.linspace(0, THETA, 24)]
ann.append('<polyline points="' + ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts) + f'" fill="none" stroke="{YEL}" stroke-width="2.5"/>')
x0 = P([0, 0, 0.305]); xr = P([0.2, 0, 0.305])
ann.append(f'<line x1="{x0[0]:.1f}" y1="{x0[1]:.1f}" x2="{xr[0]:.1f}" y2="{xr[1]:.1f}" stroke="{MUT}" stroke-width="1.5" stroke-dasharray="4 5"/>')
tm = P([rad * 1.25 * math.cos(THETA / 2), rad * 1.25 * math.sin(THETA / 2), 0.305])
ann.append(f'<text x="{tm[0]:.1f}" y="{tm[1] + 6:.1f}" fill="{YEL}" font-size="22" font-weight="700" font-style="italic">θ</text>')
# arm radius r (motor axis -> pivot), drawn just above the arm
r0 = P(list(T_arm_p + T_arm_R @ np.array([0, 0, 0.085]))); r1 = P(list(T_arm_p + T_arm_R @ np.array([0.25, 0, 0.085])))
ann.append(f'<line x1="{r0[0]:.1f}" y1="{r0[1]:.1f}" x2="{r1[0]:.1f}" y2="{r1[1]:.1f}" stroke="{MUT}" stroke-width="1.5"/>')
for q in (r0, r1):
    ann.append(f'<circle cx="{q[0]:.1f}" cy="{q[1]:.1f}" r="3" fill="{MUT}"/>')
rm = ((r0[0] + r1[0]) / 2, (r0[1] + r1[1]) / 2)
ann.append(f'<text x="{r0[0] - 10:.1f}" y="{r0[1] + 5:.1f}" fill="{TXT}" font-size="16" text-anchor="end">arm radius r</text>')
# hinge axis (arm-local +x) through the pivot
h0 = P(list(p_piv)); h1 = P(list(p_piv + T_arm_R @ np.array([0.14, 0, 0])))
ann.append(f'<line x1="{h0[0]:.1f}" y1="{h0[1]:.1f}" x2="{h1[0]:.1f}" y2="{h1[1]:.1f}" stroke="{YEL}" stroke-width="2.5"/>')
hd = np.array(h1) - np.array(h0); hd /= np.linalg.norm(hd); hn = np.array([-hd[1], hd[0]])
tip = np.array(h1); bl = tip - 12 * hd + 6 * hn; br = tip - 12 * hd - 6 * hn
ann.append(f'<path d="M{tip[0]:.1f} {tip[1]:.1f} L{bl[0]:.1f} {bl[1]:.1f} L{br[0]:.1f} {br[1]:.1f} Z" fill="{YEL}"/>')
ann.append(f'<text x="{h1[0] + 10:.1f}" y="{h1[1] + 6:.1f}" fill="{YEL}" font-size="17" font-weight="600">+x · hinge axis</text>')
# upright reference (alpha = 0) and the pendulum's own axis
up = P(list(p_piv + np.array([0, 0, 0.40])))
ann.append(f'<line x1="{h0[0]:.1f}" y1="{h0[1]:.1f}" x2="{up[0]:.1f}" y2="{up[1]:.1f}" stroke="{MUT}" stroke-width="1.5" stroke-dasharray="4 5"/>')
ann.append(f'<text x="{up[0] - 40:.1f}" y="{up[1] - 10:.1f}" fill="{MUT}" font-size="15">α = 0 (upright)</text>')
# alpha arc in the pendulum's swing plane
pts = [P(list(p_piv + T_arm_R @ Rx(t) @ np.array([0, 0, 0.21]))) for t in np.linspace(0, ALPHA, 30)]
ann.append('<polyline points="' + ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts) + f'" fill="none" stroke="{YEL}" stroke-width="2.5"/>')
am = P(list(p_piv + T_arm_R @ Rx(ALPHA / 2) @ np.array([0, 0, 0.25])))
ann.append(f'<text x="{am[0] - 4:.1f}" y="{am[1] + 2:.1f}" fill="{YEL}" font-size="22" font-weight="700" font-style="italic">α</text>')
# pivot and COM (0.15 m from the pivot along pendulum-local +z)
ann.append(f'<circle cx="{h0[0]:.1f}" cy="{h0[1]:.1f}" r="5" fill="{YEL}" stroke="#000" stroke-width="1.5"/>')
com = P(list(p_piv + R_pend @ np.array([0, 0, 0.150])))
ann.append(f'<circle cx="{com[0]:.1f}" cy="{com[1]:.1f}" r="7" fill="{ORA}" stroke="#000" stroke-width="2"/>')
ann.append(f'<line x1="{com[0] + 9:.1f}" y1="{com[1]:.1f}" x2="{com[0] + 60:.1f}" y2="{com[1] - 18:.1f}" stroke="{ORA}" stroke-width="1.5"/>')
ann.append(f'<text x="{com[0] + 64:.1f}" y="{com[1] - 14:.1f}" fill="{ORA}" font-size="16" font-weight="600">COM · l from the pivot</text>')
lab_b = P([0.05, -0.12, 0.08])

# ---------------- side panel + control loop ----------------
side = f'''
<text x="640" y="330" fill="{TXT}" font-size="22" font-weight="700">Swing up → balance</text>
<text x="640" y="366" fill="{TXT}" font-size="16"><tspan fill="{YEL}" font-style="italic" font-weight="700">θ</tspan>: arm rotation about +z</text>
<text x="640" y="392" fill="{TXT}" font-size="16"><tspan fill="{YEL}" font-style="italic" font-weight="700">α</tspan>: pendulum rotation about the arm's +x</text>
<text x="640" y="418" fill="{TXT}" font-size="16">α = 0 upright · α = π hanging down</text>
<text x="640" y="454" fill="{MUT}" font-size="15">Meshes and joint origins from the reference URDF;</text>
<text x="640" y="474" fill="{MUT}" font-size="15">shown at θ = {math.degrees(THETA):.0f}°, α = {math.degrees(ALPHA):.0f}°.</text>
'''
by = 548
def box(x, w, title, sub, stroke):
    return (f'<rect x="{x}" y="{by}" width="{w}" height="70" rx="10" fill="#0d0d0d" stroke="{stroke}" stroke-width="1.5"/>'
            f'<text x="{x + w / 2}" y="{by + 30}" fill="{TXT}" font-size="18" font-weight="700" text-anchor="middle">{title}</text>'
            f'<text x="{x + w / 2}" y="{by + 54}" fill="{MUT}" font-size="14" text-anchor="middle">{sub}</text>')
loop = (box(40, 250, 'Your policy node', 'joint state → current', YEL) + box(375, 250, 'Simulator', 'current → equations → state', '#3a3a3a')
        + box(710, 250, 'RViz', 'URDF + joint transforms', '#3a3a3a') +
        f'''<defs><marker id="ar" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" fill="{MUT}"/></marker></defs>
<line x1="296" y1="{by + 22}" x2="368" y2="{by + 22}" stroke="{MUT}" stroke-width="2" marker-end="url(#ar)"/>
<text x="332" y="{by + 14}" fill="{MUT}" font-size="12" text-anchor="middle">current [A]</text>
<line x1="368" y1="{by + 50}" x2="296" y2="{by + 50}" stroke="{MUT}" stroke-width="2" marker-end="url(#ar)"/>
<text x="332" y="{by + 66}" fill="{MUT}" font-size="12" text-anchor="middle">joint states</text>
<line x1="631" y1="{by + 35}" x2="703" y2="{by + 35}" stroke="{MUT}" stroke-width="2" marker-end="url(#ar)"/>
<text x="667" y="{by + 27}" fill="{MUT}" font-size="12" text-anchor="middle">joint states</text>''')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="'DIN Pro', 'DINPro', Barlow, 'Helvetica Neue', Arial, sans-serif">
<rect width="{W}" height="{H}" fill="#000000"/>
<text x="40" y="52" fill="{TXT}" font-size="28" font-weight="700">Mr. Melon's reactor stabiliser</text>
<text x="40" y="80" fill="{MUT}" font-size="16">Furuta pendulum · frames, angles and control loop</text>
<g stroke-width="0.7" stroke-linejoin="round">{mesh}</g>
<g>{''.join(ann)}</g>
{side}
{loop}
</svg>'''
open('reactor.svg', 'w').write(svg)
print('triangles', len(tris), 'paths', len(paths), 'bytes', len(svg))
