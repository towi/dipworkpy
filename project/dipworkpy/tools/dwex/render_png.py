"""DDL -> PNG via matplotlib."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch
from matplotlib.path import Path as MplPath

from dipworkpy.tools.dwex.model import DwexDocument

SUPPORT_COLOR = "#3a6ea5"
FAIL_COLOR = "red"
SUCCESS_MVE_COLOR = "#2e7d32"


def _ok_or_fail(expected_failed: bool, ok_color: str):
    """Map (success, color) -> (color, linestyle). Failure always means red+dashed."""
    if expected_failed:
        return FAIL_COLOR, "dashed"
    return ok_color, "solid"


NATION_COLORS: Dict[str, str] = {
    "Au": "#E84545", "En": "#3A5BA0", "Fr": "#79B8E0", "Ge": "#444444",
    "It": "#3DA34D", "Ru": "#E0E0E0", "Tu": "#F2C94C", "Xx": "#888888",
}

FIELD_COLORS = {
    "LA": "#E8D9B5", "L": "#D6E8B5", "LCB": "#E8E0B5", "LC": "#E8E0B5",
    "LCA": "#E8E0B5", "LCF": "#E8E0B5", "O": "#B5D6E8", "COL": "#CCCCCC",
}


def render_png(doc: DwexDocument, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 7), dpi=100)

    pos = {f.name: (f.x, f.y) for f in doc.fields}

    # adjacency edges — subtle dotted light-gray; order arrows below carry the prominence
    for e in doc.edges:
        if e.a not in pos or e.b not in pos:
            continue
        x1, y1 = pos[e.a]
        x2, y2 = pos[e.b]
        ax.plot([x1, x2], [y1, y2], color="#bbbbbb", linestyle=":", lw=0.9, zorder=1)

    # fields
    radius = 0.22
    for f in doc.fields:
        x, y = f.x, f.y
        fc = FIELD_COLORS.get(f.type, "#FFFFFF")
        ax.add_patch(Circle((x, y), radius, facecolor=fc, edgecolor="black",
                            lw=1.2, zorder=2))
        ax.text(x, y - radius - 0.08, f.name, ha="center", va="top",
                fontsize=10, weight="bold", zorder=3)

    # units (drawn at field pos with small offset)
    for u in doc.units:
        if u.current not in pos:
            continue
        x, y = pos[u.current]
        color = NATION_COLORS.get(u.nation, "#888888")
        ax.text(x, y, f"{u.utype}:{u.nation}", ha="center", va="center",
                fontsize=9, color="white",
                bbox=dict(boxstyle="round,pad=0.2", facecolor=color, edgecolor="none"),
                zorder=4)

    # support orders.
    # hsup (support hold): straight violet line from supporter to held unit, square marker.
    # msup (support move): violet quadratic Bezier curve from supporter THROUGH the
    #   supported unit's starting field, ending at the supported move's destination.
    #   Arrow tip is the open-V style (two lines, not a filled triangle).
    move_dest_by_current: Dict[str, str] = {
        o.current: o.dest
        for o in doc.orders
        if o.order == "mve" and o.dest is not None
    }
    for o in doc.orders:
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
            color, linestyle = _ok_or_fail(o.expected_failed, SUPPORT_COLOR)
            ax.plot(
                [start_x, tip_x], [start_y, tip_y],
                color=color, linestyle=linestyle, lw=1.4, zorder=4,
            )
            ax.scatter(
                [tip_x], [tip_y], marker="s", s=85,
                color=color, edgecolor="white", linewidths=0.8, zorder=5,
            )
        elif o.order == "msup":
            if o.dest is None or o.dest not in pos or o.current not in pos:
                continue
            color, linestyle = _ok_or_fail(o.expected_failed, SUPPORT_COLOR)
            supported_dest = move_dest_by_current.get(o.dest)
            if supported_dest is None or supported_dest not in pos:
                # supported unit has no mve (or its dest is unknown) — degrade to a
                # straight line + diamond marker so the order is still visible.
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
                    [start_x, tip_x], [start_y, tip_y],
                    color=color, linestyle=linestyle, lw=1.4, zorder=4,
                )
                ax.scatter(
                    [tip_x], [tip_y], marker="D", s=85,
                    color=color, edgecolor="white", linewidths=0.8, zorder=5,
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
                path=path, arrowstyle="->", mutation_scale=14,
                color=color, linestyle=linestyle, lw=1.4,
                shrinkA=0, shrinkB=0, zorder=5,
            )
            ax.add_patch(arrow)

    # order arrows (mve)
    for o in doc.orders:
        if o.order != "mve" or o.dest not in pos or o.current not in pos:
            continue
        x1, y1 = pos[o.current]
        x2, y2 = pos[o.dest]
        color, style = _ok_or_fail(o.expected_failed, SUCCESS_MVE_COLOR)
        arrow = FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle="->", mutation_scale=14, color=color,
            linestyle=style, lw=1.6, shrinkA=18, shrinkB=18, zorder=6,
        )
        ax.add_patch(arrow)

    # title
    ax.set_title(doc.title, fontsize=12)

    # styling
    xs = [f.x for f in doc.fields]
    ys = [f.y for f in doc.fields]
    if xs and ys:
        pad = 0.6
        ax.set_xlim(min(xs) - pad, max(xs) + pad)
        ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_aspect("equal")
    ax.set_axis_off()

    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
