"""Notation mapping between DipNet (diplomacy library) and DipworkPy formats.

Territory mapping derived from FIELDS.TXT (the authoritative geography source).
Nation, order type, and result mappings for the diplomacy/research dataset.
"""

from typing import Dict, List, Optional, Tuple

from dipworkpy.model import Order, OrderResult, OrderType


# --- Nation mapping ---

NATION_MAP: Dict[str, str] = {
    "AUSTRIA": "Au",
    "ENGLAND": "En",
    "FRANCE": "Fr",
    "GERMANY": "Ge",
    "ITALY": "It",
    "RUSSIA": "Ru",
    "TURKEY": "Tu",
}


# --- Territory mapping ---
# Derived from FIELDS.TXT synonym section and field definitions.
#
# Rules:
#   1. Non-trivial renames (DipNet ≠ simple case change of DipworkPy)
#   2. Ocean territories stay 3-letter uppercase
#   3. Land/coastal territories: capitalize first letter (PAR→Par)
#   4. Coast suffixes stripped to superfield (SPA/SC→Spa)

# Ocean territory names in DipworkPy (field type "O" in FIELDS.TXT)
_OCEAN_FIELDS = frozenset({
    "NTH", "NWS", "ENG", "IRI", "WMS", "LYO", "TYS", "ION",
    "ADR", "AEG", "EAS", "BLA", "BAR", "BOT", "BAS", "SKA",
    "HEL", "MID", "NAT",
})

# Non-trivial renames: DipNet name → DipworkPy canonical name
# Source: FIELDS.TXT synonym section (lines 591-627)
_RENAME_MAP: Dict[str, str] = {
    "BAL": "BAS",   # BAS = BAL Baltic
    "LVN": "Liv",   # Liv = Lvn Livo
    "LVP": "Lpl",   # Lpl = Lvp Livp
    "MAO": "MID",   # MID = MAO MidAtlanticOcean
    "NAF": "Afr",   # Afr = NAf NorA NorthAfr
    "NAO": "NAT",   # NAT = NAO
    "NWG": "NWS",   # NWS = NWG NorwSea
    "NWY": "Nor",   # Nor = Nwy Norw Norway
    "SEV": "Seb",   # Seb = Sev Sevastapol
    "STP": "Pet",   # Pet = StP
    "WES": "WMS",   # WMS = WMed West Western WES
}

# Subfield → superfield mapping (for coast suffixes)
_SUBFIELD_MAP: Dict[str, str] = {
    "SPA/NC": "Spa",
    "SPA/SC": "Spa",
    "STP/NC": "Pet",
    "STP/SC": "Pet",
    "BUL/EC": "Bul",
    "BUL/SC": "Bul",
}

# Full territory map: DipNet uppercase → DipworkPy canonical.
# Built once from FIELDS.TXT field definitions.
TERRITORY_MAP: Dict[str, str] = {
    # Subfields (must be checked first in convert_territory)
    **_SUBFIELD_MAP,
    # Non-trivial renames
    **_RENAME_MAP,
    # All standard territories from FIELDS.TXT field definitions.
    # Ocean territories (stay uppercase)
    "NTH": "NTH", "ENG": "ENG", "IRI": "IRI", "SKA": "SKA",
    "HEL": "HEL", "ADR": "ADR", "AEG": "AEG", "ION": "ION",
    "TYS": "TYS", "LYO": "LYO", "EAS": "EAS", "BLA": "BLA",
    "BAR": "BAR", "BOT": "BOT", "BAS": "BAS", "MID": "MID",
    "NAT": "NAT", "NWS": "NWS", "WMS": "WMS",
    # Austria
    "BUD": "Bud", "VIE": "Vie", "TRI": "Tri",
    # England
    "LPL": "Lpl", "LON": "Lon", "EDI": "Edi",
    # France
    "PAR": "Par", "BRE": "Bre", "MAR": "Mar",
    # Germany
    "MUN": "Mun", "KIE": "Kie", "BER": "Ber",
    # Italy
    "ROM": "Rom", "NAP": "Nap", "VEN": "Ven",
    # Russia
    "MOS": "Mos", "WAR": "War",
    # (Pet and Seb handled by _RENAME_MAP)
    # Turkey
    "CON": "Con", "ANK": "Ank", "SMY": "Smy",
    # Neutral supply centers
    "NOR": "Nor", "BEL": "Bel", "TUN": "Tun", "SWE": "Swe",
    "DEN": "Den", "HOL": "Hol", "SER": "Ser", "GRE": "Gre",
    "BUL": "Bul", "RUM": "Rum", "SPA": "Spa", "POR": "Por",
    # Non-SC territories
    "CLY": "Cly", "WAL": "Wal", "YOR": "Yor",
    "PIC": "Pic", "BUR": "Bur", "GAS": "Gas",
    "RUH": "Ruh", "PIE": "Pie", "TUS": "Tus", "TYR": "Tyr",
    "BOH": "Boh", "GAL": "Gal", "SIL": "Sil", "PRU": "Pru",
    "APU": "Apu", "ALB": "Alb", "UKR": "Ukr", "LIV": "Liv",
    "FIN": "Fin", "ARM": "Arm", "SYR": "Syr", "AFR": "Afr",
    # Switzerland (impassable but listed in FIELDS.TXT)
    "SWI": "Sui",
}


def convert_territory(dipnet_name: str) -> str:
    """Convert a DipNet territory name to DipworkPy canonical name.

    Handles coast suffixes (SPA/SC → Spa), non-trivial renames (STP → Pet),
    and standard capitalization (PAR → Par, NTH → NTH).

    Raises KeyError if territory is unknown.
    """
    upper = dipnet_name.upper()
    # Check subfield notation first (e.g., "SPA/SC", "STP/NC")
    if "/" in upper:
        if upper in _SUBFIELD_MAP:
            return _SUBFIELD_MAP[upper]
        # Unknown subfield - try stripping coast
        base = upper.split("/")[0]
        return convert_territory(base)
    # Direct lookup
    if upper in TERRITORY_MAP:
        return TERRITORY_MAP[upper]
    raise KeyError(f"Unknown DipNet territory: {dipnet_name!r}")


# --- Order parsing ---

def parse_dipnet_order(order_str: str, nation_dwp: str) -> Order:
    """Parse a DipNet order string into a DipworkPy Order.

    DipNet order formats:
        "A VIE H"             → hold
        "A VIE - BUD"         → move
        "A VIE - BUD VIA"     → move via convoy
        "F ENG C A LON - BEL" → convoy
        "A MUN S A VIE"       → support hold
        "A MUN S A VIE - BUD" → support move

    Args:
        order_str: DipNet order string (e.g., "A VIE - BUD")
        nation_dwp: DipworkPy nation code (e.g., "Au")

    Returns:
        DipworkPy Order object
    """
    parts = order_str.split()
    utype = parts[0]  # "A" or "F"
    current_dipnet = parts[1]  # territory, possibly with coast
    current = convert_territory(current_dipnet)

    if len(parts) < 3 or parts[2] == "H":
        # Hold: "A VIE H" or "A VIE"
        return Order(nation=nation_dwp, utype=utype, current=current,
                     order=OrderType.hld, dest=None)

    if parts[2] == "-":
        # Move: "A VIE - BUD" or "A VIE - BUD VIA"
        dest = convert_territory(parts[3])
        return Order(nation=nation_dwp, utype=utype, current=current,
                     order=OrderType.mve, dest=dest)

    if parts[2] == "S":
        # Support: "A MUN S A VIE" (hold) or "A MUN S A VIE - BUD" (move)
        # parts[3] = supported unit type (ignored)
        supported_loc = convert_territory(parts[4])
        if len(parts) > 5 and parts[5] == "-":
            # Support move: dest = supported unit's STARTING field
            return Order(nation=nation_dwp, utype=utype, current=current,
                         order=OrderType.msup, dest=supported_loc)
        else:
            # Support hold: dest = held unit's location
            return Order(nation=nation_dwp, utype=utype, current=current,
                         order=OrderType.hsup, dest=supported_loc)

    if parts[2] == "C":
        # Convoy: "F ENG C A LON - BEL"
        # parts[3] = convoyed unit type (ignored)
        convoyed_loc = convert_territory(parts[4])
        # dest = convoyed army's STARTING field
        return Order(nation=nation_dwp, utype=utype, current=current,
                     order=OrderType.con, dest=convoyed_loc)

    # Unknown order format - treat as hold
    return Order(nation=nation_dwp, utype=utype, current=current,
                 order=OrderType.hld, dest=None)


# --- Result mapping ---

def map_result(result_list: List[str]) -> Tuple[Optional[bool], Optional[bool]]:
    """Convert DipNet result list to DipworkPy (succeeds, dislodged) tuple.

    DipNet results:
        []                    → (None, None)     success
        ["bounce"]            → (False, None)    move bounced
        ["cut"]               → (False, None)    support cut
        ["dislodged"]         → (None, True)     unit dislodged, order OK
        ["bounce","dislodged"]→ (False, True)    bounced and dislodged
        ["cut","dislodged"]   → (False, True)    cut and dislodged
        ["void"]              → (False, None)    geography-dependent (→ INCONCLUSIVE)
        ["no convoy"]         → (False, None)    convoy route failed

    Returns:
        (succeeds, dislodged) where None means "default" (success / not dislodged)
    """
    if not result_list:
        return (None, None)

    succeeds: Optional[bool] = None
    dislodged: Optional[bool] = None

    for r in result_list:
        if r == "bounce" or r == "cut" or r == "void" or r == "no convoy":
            succeeds = False
        elif r == "dislodged":
            dislodged = True

    return (succeeds, dislodged)


# --- Formatting for failure output ---

def format_order_dwp(order: Order) -> str:
    """Format a DipworkPy Order as a human-readable string.

    Example: "Au A Vie mve Mun"
    """
    o = order.order.value if order.order else ""
    d = order.dest if order.dest else ""
    parts = [order.nation, order.utype, order.current]
    if o:
        parts.append(o)
    if d:
        parts.append(d)
    return " ".join(parts)


def format_oresult_dwp(oresult: OrderResult) -> str:
    """Format a DipworkPy OrderResult with ! and > markers.

    Examples:
        "Au A Vie mve Mun"      → success
        "Au A Vie mve Mun !"    → failed
        "Au A Vie mve Mun >"    → dislodged
        "Au A Vie mve Mun ! >"  → failed and dislodged
    """
    base = format_order_dwp(oresult)  # type: ignore[arg-type]
    markers: List[str] = []
    if oresult.succeeds is False:
        markers.append("!")
    if oresult.dislodged is True:
        markers.append(">")
    if markers:
        return base + " " + " ".join(markers)
    return base
