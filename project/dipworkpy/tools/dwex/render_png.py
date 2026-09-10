"""DDL -> PNG via matplotlib."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch
from matplotlib.path import Path as MplPath

from dipworkpy.tools.dwex.model import DwexDocument

# Orthogonal visual system:
#   - Arrow-tip / marker shape  -> order type     (mve / hsup / msup / con)
#   - Line style (solid|dashed) -> success / fail (! marker in DDL source)
#   - Color                     -> nation         (also the colour of the unit badge)
#
# Russia is traditionally rendered white in Diplomacy; bumped to khaki/tan
# here so it stays visible on a white page.

# Convention follows the classic Diplomacy palette, shifted away from any
# pure signal-red/yellow/white tone:
#   Au red       -> dark red       (avoids stop-sign red)
#   En dark blue -> kept as is
#   Fr light blue-> dark cyan/teal (no longer washes out on white)
#   Ge black     -> warm brown     (less harsh than pure black on a diagram)
#   It green     -> dark green
#   Ru white     -> tan/khaki      (visible on white)
#   Tu yellow    -> orange         (more readable, still warm)
NATION_COLORS: Dict[str, str] = {
    "Au": "#8b1a1a",  # Austria-Hungary - dark red
    "En": "#3a5ba0",  # England         - dark blue
    "Fr": "#0e7490",  # France          - dark cyan
    "Ge": "#6d4c41",  # Germany         - warm brown
    "It": "#1b5e20",  # Italy           - dark green
    "Ru": "#c8a878",  # Russia          - tan / khaki
    "Tu": "#e67e22",  # Turkey          - orange
    "Xx": "#888888",  # neutral         - mid grey
}

FIELD_COLORS = {
    "LA": "#E8D9B5",
    "L": "#D6E8B5",
    "LCB": "#E8E0B5",
    "LC": "#E8E0B5",
    "LCA": "#E8E0B5",
    "LCF": "#E8E0B5",
    "O": "#B5D6E8",
    "COL": "#CCCCCC",
}


def _nation_color(nation: str) -> str:
    return NATION_COLORS.get(nation, "#888888")


def _line_style(expected_failed: bool, expected_dislodged: bool = False) -> str:
    """solid for success; dashed for failure (! marker) OR dislodgement (> marker).

    Dislodgement is treated as 'unsuccessful' from the order's point of view:
    even if the order's intent was carried out (e.g. a hold), the unit ending
    up booted from its field is the visual opposite of a successful outcome.
    """
    return "dashed" if (expected_failed or expected_dislodged) else "solid"


_DEFAULT_JITTER = 0.2


def _cross(p1, p2, p3, p4) -> bool:
    """True if segment p1-p2 properly crosses segment p3-p4 (touching and
    collinear cases do not count)."""

    def orient(a, b, c) -> float:
        return float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

    o1: float = orient(p1, p2, p3)
    o2: float = orient(p1, p2, p4)
    o3: float = orient(p3, p4, p1)
    o4: float = orient(p3, p4, p2)
    return bool(o1 * o2 < 0 and o3 * o4 < 0)


def _arrow_segments(doc, idx) -> List:
    """Index pairs of the STRAIGHT arrow types (mve, hsup). Curved order
    types (msup, con) are excluded — bending is their visual identity;
    mve/hsup must stay straight, so the layout keeps nodes off their lines."""
    segs = []
    for o in doc.orders:
        if o.order in ("mve", "hsup") and o.current in idx and o.dest in idx:
            segs.append((idx[o.current], idx[o.dest]))
    return segs


def _move_creates_crossing_or_obstruction(
    pts: np.ndarray,
    idx: Dict[str, int],
    edges: List,
    arrow_segs: List,
    clearance: float,
    i: int,
    cand: np.ndarray,
) -> bool:
    """Would moving node i to `cand` make any adjacency edge properly cross
    another one, or put node i within `clearance` of a straight arrow line
    (mve/hsup)? Only node i's relations can change, so only those are
    tested."""
    inc = [(e.a, e.b) for e in edges if idx.get(e.a) == i or idx.get(e.b) == i]
    old = pts[i].copy()
    pts[i] = cand
    try:
        for a, b in inc:
            p1, p2 = pts[idx[a]], pts[idx[b]]
            for e2 in edges:
                if e2.a in (a, b) or e2.b in (a, b):
                    continue
                q1, q2 = pts[idx[e2.a]], pts[idx[e2.b]]
                if _cross(p1, p2, q1, q2):
                    return True
        for a, b in arrow_segs:
            if i in (a, b):
                continue
            if _point_seg_dist(cand, pts[a], pts[b]) < clearance:
                return True
        return False
    finally:
        pts[i] = old


def _deobstruct(
    pts: np.ndarray,
    idx: Dict[str, int],
    edges: List,
    arrow_segs: List,
    clearance: float,
    box: Tuple[float, float, float, float],
    rounds: int = 15,
) -> None:
    """Push nodes off straight arrow lines (mve/hsup). Arrows never bend, so
    a node sitting on an arrow's line is a LAYOUT defect: the node is nudged
    perpendicular off the line. A nudge is accepted only if it removes an
    obstruction without creating an edge crossing or a new obstruction;
    monotone, so this terminates."""
    x_lo, y_lo, x_hi, y_hi = box

    def _obstructions() -> List:
        out = []
        for n, i in idx.items():
            for a, b in arrow_segs:
                if i in (a, b):
                    continue
                if _point_seg_dist(pts[i], pts[a], pts[b]) < clearance:
                    out.append((i, a, b))
        return out

    for _ in range(rounds):
        obs = _obstructions()
        if not obs:
            return
        improved = False
        for i, a, b in obs:
            p = pts[i]
            ax, ay = pts[a]
            bx, by = pts[b]
            dx, dy = bx - ax, by - ay
            seg2 = dx * dx + dy * dy
            if seg2 < 1e-12:
                continue
            t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / seg2))
            cx, cy = ax + t * dx, ay + t * dy
            ux, uy = dx / math.sqrt(seg2), dy / math.sqrt(seg2)
            nx, ny = -uy, ux  # perpendicular of the arrow line
            dist = _point_seg_dist(p, pts[a], pts[b])
            before = len(_obstructions())
            best: Tuple[np.ndarray, int] | None = None
            for side in (1.0, -1.0):
                for extra in (0.30, 0.55, 0.85):
                    step = clearance - dist + extra
                    cand = np.clip((cx + nx * side * step, cy + ny * side * step), [x_lo, y_lo], [x_hi, y_hi])
                    old = pts[i].copy()
                    pts[i] = cand
                    after = len(_obstructions())
                    this_cleared = _point_seg_dist(cand, pts[a], pts[b]) >= clearance
                    crossed = bool(_crossing_pairs(pts, idx, edges))
                    pts[i] = old
                    if this_cleared and after <= before and not crossed and (best is None or after < best[1]):
                        best = (cand, after)
                        break
            if best is not None:
                pts[i] = best[0]
                improved = True
        if not improved:
            return


def _fill_positions(doc: DwexDocument) -> Dict[str, Tuple[float, float]]:
    """`layout-fill`: stretch + CROSSING-GUARDED Lloyd relaxation.

    1. The document's coordinates are stretched anisotropically into the
       target box (figsize minus margin) — the map shape is the starting
       configuration.
    2. A bounded Lloyd relaxation (centroidal Voronoi, grid-approximated)
       moves every node toward the centroid of its Voronoi cell: dense
       clusters spread into empty space. CONSTRAINT: moves are applied
       greedily one node at a time, and a move that would make any
       adjacency edge properly cross another one is dampened (1/2, 1/4,
       1/8) or rejected — the layout can never introduce an edge crossing
       that the source geometry does not have.

    Fully deterministic (no randomness). Degenerate axes (all nodes on one
    line) keep their single coordinate; <3 nodes skip the relaxation.
    """
    width, height = 9.2, 6.2
    margin = 0.4
    xs = [f.x for f in doc.fields]
    ys = [f.y for f in doc.fields]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    sx = (width - 2 * margin) / (x1 - x0) if x1 > x0 else 1.0
    sy = (height - 2 * margin) / (y1 - y0) if y1 > y0 else 1.0
    names = [f.name for f in doc.fields]
    idx = {n: i for i, n in enumerate(names)}
    pos = {n: (margin + (f.x - x0) * sx, margin + (f.y - y0) * sy) for n, f in zip(names, doc.fields)}
    if len(names) < 3:
        return pos

    edges = [e for e in doc.edges if e.a in idx and e.b in idx]
    arrow_segs = _arrow_segments(doc, idx)
    arrow_clearance = 0.22 + 0.06  # field circle + small margin (badge grazing in dense triangles is unavoidable)
    box = (margin, margin, width - margin, height - margin)
    pts = np.array([pos[n] for n in names])
    # Visual contracts enforced on the LAYOUT (never on the drawing):
    #   - adjacency edges are straight and crossing-free (untangle)
    #   - mve/hsup arrows are straight, so no node may sit on their lines
    #     (deobstruct); msup/con curve BY DESIGN and are exempt.
    # The guarded relaxation below then keeps both invariants.
    _untangle(pts, idx, edges, box)
    _deobstruct(pts, idx, edges, arrow_segs, arrow_clearance, box)
    # coarse grid approximating the canvas area (Voronoi via nearest-node)
    gx, gy = np.meshgrid(
        np.linspace(margin, width - margin, 46),
        np.linspace(margin, height - margin, 31),
    )
    cells = np.stack([gx.ravel(), gy.ravel()], axis=1)

    for _ in range(12):
        d2 = ((cells[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2)
        assign = d2.argmin(axis=1)
        sums = np.zeros_like(pts)
        counts = np.zeros(len(pts))
        np.add.at(sums, assign, cells)
        np.add.at(counts, assign, 1)
        with np.errstate(invalid="ignore", divide="ignore"):
            targets = np.where(counts[:, None] > 0, sums / counts[:, None], pts)
        new = pts + (targets - pts) * 0.5
        new[:, 0] = np.clip(new[:, 0], margin, width - margin)
        new[:, 1] = np.clip(new[:, 1], margin, height - margin)
        if float(np.abs(new - pts).max()) < 0.001:
            break
        # greedy guarded application: big moves first; each move is accepted
        # only if it introduces no edge crossing AND no arrow obstruction
        moved = False
        for i in np.argsort(-np.abs(new - pts).sum(axis=1)):
            i = int(i)
            for step in (1.0, 0.5, 0.25, 0.125):
                cand = pts[i] + (new[i] - pts[i]) * step
                if not _move_creates_crossing_or_obstruction(pts, idx, edges, arrow_segs, arrow_clearance, i, cand):
                    if step > 0 and float(np.abs(cand - pts[i]).max()) > 0.001:
                        pts[i] = cand
                        moved = True
                    break
        if not moved:
            break
    return {n: (float(p[0]), float(p[1])) for n, p in zip(names, pts)}


def _jitter(name: str, amount: float = _DEFAULT_JITTER) -> Tuple[float, float]:
    """Deterministic per-name offset in (-amount, +amount) for both axes.

    Same field name -> same offset across renders, so PNGs stay stable in
    git, but exact grid alignment is broken so diagrams look less synthetic.
    """
    digest = hashlib.md5(name.encode("utf-8")).digest()
    dx = (digest[0] / 255.0 * 2.0 - 1.0) * amount
    dy = (digest[1] / 255.0 * 2.0 - 1.0) * amount
    return dx, dy


def _jitter_amount(doc: DwexDocument) -> float:
    """Read the field-jitter pragma if present, otherwise default 0.2."""
    raw = doc.pragmas.get("field-jitter")
    if raw is None:
        return _DEFAULT_JITTER
    try:
        return float(raw)
    except (TypeError, ValueError):
        return _DEFAULT_JITTER


def _midpoint_arrow(
    ax,
    p_start: Tuple[float, float],
    p_via: Tuple[float, float],
    p_end: Tuple[float, float],
    color: str,
    linestyle: str,
    arrowstyle: str,
    mutation_scale: float = 10.0,
) -> None:
    """Draw a small arrow at the midpoint of a (possibly Bezier) path.

    For quadratic Bezier curves the curve midpoint is
        B(0.5) = 0.25·P0 + 0.5·P_via + 0.25·P2
    and the tangent direction at t=0.5 is (P2 − P0).
    Passing `p_via = midpoint(p_start, p_end)` recovers the straight-line case.

    `arrowstyle` is required and should match the path's end shape so the
    midpoint visually repeats it (orthogonal-system convention).
    """
    mx = 0.25 * p_start[0] + 0.5 * p_via[0] + 0.25 * p_end[0]
    my = 0.25 * p_start[1] + 0.5 * p_via[1] + 0.25 * p_end[1]
    dx = p_end[0] - p_start[0]
    dy = p_end[1] - p_start[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    span = 0.07
    tail = (mx - ux * span, my - uy * span)
    tip = (mx + ux * span, my + uy * span)
    arrow = FancyArrowPatch(
        tail,
        tip,
        arrowstyle=arrowstyle,
        mutation_scale=mutation_scale,
        color=color,
        linestyle=linestyle,
        lw=1.0,
        zorder=5,
    )
    ax.add_patch(arrow)


def _point_seg_dist(p, a, b) -> float:
    """Distance from point p to the segment a-b."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    if seg2 < 1e-12:
        return math.hypot(p[0] - ax, p[1] - ay)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / seg2))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(p[0] - cx, p[1] - cy)


def _crossing_pairs(pts: np.ndarray, idx: Dict[str, int], edges: List) -> List:
    """All properly crossing adjacency-edge pairs (straight segments)."""
    pairs: List = []
    for i, e1 in enumerate(edges):
        if e1.a not in idx or e1.b not in idx:
            continue
        p1, p2 = pts[idx[e1.a]], pts[idx[e1.b]]
        for e2 in edges[i + 1 :]:
            if e2.a not in idx or e2.b not in idx:
                continue
            if e1.a in (e2.a, e2.b) or e1.b in (e2.a, e2.b):
                continue
            q1, q2 = pts[idx[e2.a]], pts[idx[e2.b]]
            if _cross(p1, p2, q1, q2):
                pairs.append((e1, e2))
    return pairs


def _reflect(p, q1, q2, damping: float) -> Tuple[float, float]:
    """Reflect point p across the line q1-q2, moved only `damping` of the way."""
    dx, dy = q2[0] - q1[0], q2[1] - q1[1]
    seg2 = dx * dx + dy * dy
    if seg2 < 1e-12:
        return (p[0], p[1])
    t = ((p[0] - q1[0]) * dx + (p[1] - q1[1]) * dy) / seg2
    fx, fy = q1[0] + t * dx, q1[1] + t * dy
    return (p[0] + (2 * fx - p[0] - p[0]) * damping, p[1] + (2 * fy - p[1] - p[1]) * damping)


def _untangle(
    pts: np.ndarray, idx: Dict[str, int], edges: List, box: Tuple[float, float, float, float], rounds: int = 30
) -> None:
    """Resolve edge crossings by moving NODES (edges stay straight, per the
    visual contract: curved lines would read as support arrows).

    For each crossing, the endpoint nearest the crossing is reflected across
    the other edge's line (damped). Moves are accepted only when the total
    crossing count decreases; otherwise they are reverted. Monotone in the
    crossing count, so this terminates; for planar graphs it typically
    reaches zero."""
    x_lo, y_lo, x_hi, y_hi = box
    for _ in range(rounds):
        before = len(_crossing_pairs(pts, idx, edges))
        if before == 0:
            return
        improved = False
        for e1, e2 in _crossing_pairs(pts, idx, edges):
            p1, p2 = pts[idx[e1.a]], pts[idx[e1.b]]
            q1, q2 = pts[idx[e2.a]], pts[idx[e2.b]]
            if not _cross(p1, p2, q1, q2):
                continue  # stale entry from a later fix
            # try every endpoint of both edges, reflected across the OTHER
            # edge's line, with two dampings; keep the best strictly
            # improving move (deterministic order)
            candidates = [
                (idx[e1.a], q1, q2),
                (idx[e1.b], q1, q2),
                (idx[e2.a], p1, p2),
                (idx[e2.b], p1, p2),
            ]
            best: Tuple[int, np.ndarray, int] | None = None
            for move_idx, line_a, line_b in candidates:
                for damping in (1.0, 0.75):
                    old = pts[move_idx].copy()
                    cand = np.clip(_reflect(pts[move_idx], line_a, line_b, damping), [x_lo, y_lo], [x_hi, y_hi])
                    pts[move_idx] = cand
                    cnt = len(_crossing_pairs(pts, idx, edges))
                    pts[move_idx] = old
                    if cnt < before and (best is None or cnt < best[2]):
                        best = (move_idx, cand, cnt)
            if best is not None:
                pts[best[0]] = best[1]
                improved = True
        if not improved:
            # local minimum under single-endpoint reflections; try pairwise
            # moves: reflect BOTH endpoints of one edge across the other
            for e1, e2 in _crossing_pairs(pts, idx, edges):
                p1, p2 = pts[idx[e1.a]], pts[idx[e1.b]]
                q1, q2 = pts[idx[e2.a]], pts[idx[e2.b]]
                if not _cross(p1, p2, q1, q2):
                    continue
                before = len(_crossing_pairs(pts, idx, edges))
                for i1, i2, la, lb in (
                    (idx[e1.a], idx[e1.b], q1, q2),
                    (idx[e2.a], idx[e2.b], p1, p2),
                ):
                    old1, old2 = pts[i1].copy(), pts[i2].copy()
                    pts[i1] = np.clip(_reflect(pts[i1], la, lb, 1.0), [x_lo, y_lo], [x_hi, y_hi])
                    pts[i2] = np.clip(_reflect(pts[i2], la, lb, 1.0), [x_lo, y_lo], [x_hi, y_hi])
                    if len(_crossing_pairs(pts, idx, edges)) < before:
                        improved = True
                        break
                    pts[i1], pts[i2] = old1, old2
                if improved:
                    break
            if not improved:
                return


def render_png(doc: DwexDocument, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 7), dpi=100)
    show_mid_arrows = "no-mid-arrows" not in doc.pragmas

    # `layout-fill` pragma: stretch the node positions so they fill the
    # whole figure area (dense boards otherwise letterbox in a wide region).
    # Relative layout — and with it map topology — is preserved.
    if "layout-fill" in doc.pragmas:
        pos = _fill_positions(doc)
    else:
        # Jitter field positions deterministically (per-name hash) so the diagram
        # doesn't read as a strict grid. Position-dependent renders (labels, edges,
        # arrows, supports) all read from `pos`, so they follow the jittered values.
        # The jitter amplitude can be overridden via the `field-jitter(<value>)`
        # pragma; default 0.2 (≈20% of one axis unit).
        jit = _jitter_amount(doc)
        pos = {}
        for f in doc.fields:
            dx, dy = _jitter(f.name, amount=jit)
            pos[f.name] = (f.x + dx, f.y + dy)
    radius = 0.22

    # adjacency edges — subtle dotted light-gray straight segments; order
    # arrows below carry the prominence. NEVER curved (visual contract:
    # curves read as support arrows); crossings are resolved by the layout
    # (untangle + guarded relaxation), not by bending edges.
    for e in doc.edges:
        if e.a not in pos or e.b not in pos:
            continue
        x1, y1 = pos[e.a]
        x2, y2 = pos[e.b]
        ax.plot([x1, x2], [y1, y2], color="#bbbbbb", linestyle=":", lw=0.9, zorder=1)

    # fields — drawn at the jittered positions stored in `pos`
    for f in doc.fields:
        x, y = pos[f.name]
        fc = FIELD_COLORS.get(f.type, "#FFFFFF")
        ax.add_patch(Circle((x, y), radius, facecolor=fc, edgecolor="black", lw=1.2, zorder=2))
        ax.text(x, y - radius - 0.08, f.name, ha="center", va="top", fontsize=10, weight="bold", zorder=3)

    # units — nation-coloured badge, with a red ✗ overlay when dislodged ('>')
    dislodged_fields = {o.current for o in doc.orders if o.expected_dislodged}
    for u in doc.units:
        if u.current not in pos:
            continue
        x, y = pos[u.current]
        color = _nation_color(u.nation)
        ax.text(
            x,
            y,
            f"{u.utype}:{u.nation}",
            ha="center",
            va="center",
            fontsize=9,
            color="white",
            bbox=dict(boxstyle="round,pad=0.2", facecolor=color, edgecolor="none"),
            zorder=4,
        )
        if u.current in dislodged_fields:
            # Two crossed red lines (matplotlib marker='x') placed BELOW the
            # unit badge — between badge bottom (~y-0.07) and the field-name
            # label (~y - radius - 0.08) — so the badge text stays readable.
            ax.scatter(
                [x],
                [y - 0.16],
                marker="x",
                s=180,
                color="red",
                linewidths=2.4,
                zorder=6,
            )

    # All orders share the orthogonal axes:
    #   shape  = order type (mve filled-triangle, msup open-V, hsup square, con hexagon)
    #   line   = solid (success) / dashed (failure)
    #   colour = nation
    move_dest_by_current: Dict[str, str] = {
        o.current: o.dest for o in doc.orders if o.order == "mve" and o.dest is not None
    }
    for o in doc.orders:
        color = _nation_color(o.nation)
        linestyle = _line_style(o.expected_failed, o.expected_dislodged)
        if o.order == "hsup":
            if o.dest is None or o.dest not in pos or o.current not in pos:
                continue
            x1, y1 = pos[o.current]
            x2, y2 = pos[o.dest]
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length < 1e-3:
                continue
            ux, uy = dx / length, dy / length
            pad = radius + 0.04
            tip_x, tip_y = x2 - ux * pad, y2 - uy * pad
            start_x, start_y = x1 + ux * pad, y1 + uy * pad
            ax.plot(
                [start_x, tip_x],
                [start_y, tip_y],
                color=color,
                linestyle=linestyle,
                lw=1.4,
                zorder=4,
            )
            ax.scatter(
                [tip_x],
                [tip_y],
                marker="s",
                s=85,
                color=color,
                edgecolor="white",
                linewidths=0.8,
                zorder=5,
            )
            if show_mid_arrows:
                # hsup uses a square scatter marker as its end shape, so the
                # midpoint repeats that shape (smaller) rather than calling the
                # arrowstyle-based helper.
                mid_mx = (start_x + tip_x) / 2
                mid_my = (start_y + tip_y) / 2
                ax.scatter(
                    [mid_mx],
                    [mid_my],
                    marker="s",
                    s=35,
                    color=color,
                    edgecolor="white",
                    linewidths=0.6,
                    zorder=5,
                )
        elif o.order == "msup":
            if o.dest is None or o.dest not in pos or o.current not in pos:
                continue
            # curve endpoint: explicit notation ("sup Ber mve Kie") wins;
            # implicit notation resolves the supported unit's own mve order
            supported_dest = o.target if o.target is not None else move_dest_by_current.get(o.dest)
            if supported_dest is None or supported_dest not in pos:
                # fallback: straight line + diamond (no target knowable at all)
                x1, y1 = pos[o.current]
                x2, y2 = pos[o.dest]
                dx, dy = x2 - x1, y2 - y1
                length = math.hypot(dx, dy)
                if length < 1e-3:
                    continue
                ux, uy = dx / length, dy / length
                pad = radius + 0.04
                tip_x, tip_y = x2 - ux * pad, y2 - uy * pad
                start_x, start_y = x1 + ux * pad, y1 + uy * pad
                ax.plot(
                    [start_x, tip_x],
                    [start_y, tip_y],
                    color=color,
                    linestyle=linestyle,
                    lw=1.4,
                    zorder=4,
                )
                ax.scatter(
                    [tip_x],
                    [tip_y],
                    marker="D",
                    s=85,
                    color=color,
                    edgecolor="white",
                    linewidths=0.8,
                    zorder=5,
                )
                if show_mid_arrows:
                    # fallback path uses a diamond end-marker; repeat it smaller at midpoint
                    mid_mx = (start_x + tip_x) / 2
                    mid_my = (start_y + tip_y) / 2
                    ax.scatter(
                        [mid_mx],
                        [mid_my],
                        marker="D",
                        s=35,
                        color=color,
                        edgecolor="white",
                        linewidths=0.6,
                        zorder=5,
                    )
                continue
            # natural quadratic Bezier: supporter -> [via field as control point] -> dest.
            # The curve bows TOWARD the supported unit's field without passing exactly
            # through its centre. Endpoints are pulled inward in axis coordinates so the
            # path stops at the field boundary plus a small pad (no need for shrinkA/B
            # in display-points, which depend on figure size).
            sx, sy = pos[o.current]
            vx, vy = pos[o.dest]
            ex, ey = pos[supported_dest]
            pad_axis = radius + 0.04
            # tangent at start = direction from supporter toward the control point (via)
            t1x, t1y = vx - sx, vy - sy
            t1len = math.hypot(t1x, t1y) or 1.0
            start = (sx + t1x / t1len * pad_axis, sy + t1y / t1len * pad_axis)
            # tangent at end = direction from control point (via) toward dest
            t2x, t2y = ex - vx, ey - vy
            t2len = math.hypot(t2x, t2y) or 1.0
            end = (ex - t2x / t2len * pad_axis, ey - t2y / t2len * pad_axis)
            path = MplPath(
                [start, (vx, vy), end],
                [MplPath.MOVETO, MplPath.CURVE3, MplPath.CURVE3],
            )
            arrow = FancyArrowPatch(
                path=path,
                arrowstyle="->",
                mutation_scale=14,
                color=color,
                linestyle=linestyle,
                lw=1.4,
                shrinkA=0,
                shrinkB=0,
                zorder=5,
            )
            ax.add_patch(arrow)
            if show_mid_arrows:
                _midpoint_arrow(
                    ax,
                    start,
                    (vx, vy),
                    end,
                    color,
                    linestyle,
                    arrowstyle="->",
                )
        elif o.order == "con":
            # Convoy: Bezier curve from convoyer through the convoyed army's
            # start to the army's destination. End shape is an open bracket
            # `-[` — distinct from mve/msup/hsup tips, evoking a 'dock' visual.
            if o.dest is None or o.dest not in pos or o.current not in pos:
                continue
            supported_dest = move_dest_by_current.get(o.dest)
            if supported_dest is None or supported_dest not in pos:
                # Convoyed unit has no mve — fall back to a hexagon marker on
                # the convoyer so the order is at least visible.
                cxc, cyc = pos[o.current]
                ax.scatter(
                    [cxc],
                    [cyc],
                    marker="h",
                    s=110,
                    color=color,
                    edgecolor="white",
                    linewidths=0.8,
                    zorder=5,
                )
                continue
            sx, sy = pos[o.current]
            vx, vy = pos[o.dest]
            ex, ey = pos[supported_dest]
            pad_axis = radius + 0.04
            t1x, t1y = vx - sx, vy - sy
            t1len = math.hypot(t1x, t1y) or 1.0
            start = (sx + t1x / t1len * pad_axis, sy + t1y / t1len * pad_axis)
            t2x, t2y = ex - vx, ey - vy
            t2len = math.hypot(t2x, t2y) or 1.0
            end = (ex - t2x / t2len * pad_axis, ey - t2y / t2len * pad_axis)
            path = MplPath(
                [start, (vx, vy), end],
                [MplPath.MOVETO, MplPath.CURVE3, MplPath.CURVE3],
            )
            arrow = FancyArrowPatch(
                path=path,
                arrowstyle="-[",
                mutation_scale=14,
                color=color,
                linestyle=linestyle,
                lw=1.4,
                shrinkA=0,
                shrinkB=0,
                zorder=5,
            )
            ax.add_patch(arrow)
            if show_mid_arrows:
                _midpoint_arrow(
                    ax,
                    start,
                    (vx, vy),
                    end,
                    color,
                    linestyle,
                    arrowstyle="-[",
                )
    # mve arrows — filled-triangle arrowhead identifies the order type.
    # ALWAYS straight (visual contract: only support/convoy orders curve).
    # When a third field lies ON the line (pinned there by the map topology:
    # e.g. Boh between Mun and Sil), the arrow is drawn as collinear
    # segments with a GAP around that field — straight, never bent, never
    # cutting through a node.
    for o in doc.orders:
        if o.order != "mve" or o.dest not in pos or o.current not in pos:
            continue
        x1, y1 = pos[o.current]
        x2, y2 = pos[o.dest]
        color = _nation_color(o.nation)
        linestyle = _line_style(o.expected_failed, o.expected_dislodged)
        # blocked intervals along the line, as [t0, t1] parameters
        length = math.hypot(x2 - x1, y2 - y1)
        if length < 1e-9:
            continue
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        intervals: List = []
        for name, (nx, ny) in pos.items():
            if name in (o.current, o.dest):
                continue
            # projection of the node onto the line
            t = (nx - x1) * ux + (ny - y1) * uy
            if t <= radius + 0.05 or t >= length - radius - 0.05:
                continue
            d = abs((nx - x1) * uy - (ny - y1) * ux)  # perpendicular distance
            if d >= radius + 0.16:
                continue
            half = math.sqrt(max((radius + 0.16) ** 2 - d * d, 0.0))
            intervals.append((t - half, t + half))
        intervals.sort()
        # merge overlapping intervals
        merged: List = []
        for t0, t1 in intervals:
            if merged and t0 <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], t1)
            else:
                merged.append([t0, t1])
        # collinear sub-segments between the gaps
        segs: List = []
        cur = 0.0
        for t0, t1 in merged:
            if t0 > cur:
                segs.append((cur, min(t0, length)))
            cur = max(cur, t1)
        if cur < length:
            segs.append((cur, length))
        for si, (ta, tb) in enumerate(segs):
            pa = (x1 + ux * ta, y1 + uy * ta)
            pb = (x1 + ux * tb, y1 + uy * tb)
            arrow = FancyArrowPatch(
                pa,
                pb,
                arrowstyle="-|>" if si == len(segs) - 1 else "-",
                mutation_scale=18,
                color=color,
                linestyle=linestyle,
                lw=1.6,
                shrinkA=18 if si == 0 else 0,
                shrinkB=0,
                zorder=6,
            )
            ax.add_patch(arrow)

    # title
    ax.set_title(doc.title, fontsize=12)

    # styling — use jittered positions so axis limits enclose the rendered nodes
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    if xs and ys:
        pad = 0.6
        ax.set_xlim(min(xs) - pad, max(xs) + pad)
        ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_aspect("equal")
    ax.set_axis_off()

    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
