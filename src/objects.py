"""
Physical-properties library of throwable household objects.

Feeds an air-drag-enabled projectile simulator. Each entry pairs measured/specced
mass and dimensions with a tumbling-average drag coefficient and frontal area.

Source notation in `notes`: brief citation. Where genuine uncertainty exists
("tumbling Cd depends on axis"), it's documented inline.

Drag-coefficient reference values used across this file:
  - Sphere (smooth):           Cd ~ 0.47        (NASA Glenn shape effects)
  - Sphere (fuzzy, tennis):    Cd ~ 0.55        (Mehta 2008, ITF wind-tunnel)
  - Cylinder broadside:        Cd ~ 1.0-1.2     (Hoerner; aerospaceweb.org)
  - Cylinder end-on (l/d~2):   Cd ~ 0.8         (axial flow)
  - Flat plate broadside:      Cd ~ 1.28        (NASA Glenn shape effects)
  - Tumbling irregular:        Cd ~ 0.7-1.0     (averaged orientations)

Air-density assumed elsewhere: rho = 1.225 kg/m^3 (sea level, 15 C).
"""

from dataclasses import dataclass
from math import pi
from typing import Dict


@dataclass(frozen=True)
class PhysicalObject:
    name: str                # Display name e.g. "Soda Can (full)"
    short_name: str          # snake_case key e.g. "soda_can_full"
    mass_kg: float           # mass in kg
    drag_coefficient: float  # Cd, dimensionless, tumbling-average
    cross_section_m2: float  # frontal area in m^2 (use tumbling-average if irregular)
    color: str               # hex color for rendering ("#22d3ee")
    emoji: str               # single emoji for HUD ("🥤")
    notes: str = ""          # one-liner: how it falls / why Cd is what it is


# Helper geometry constants (kept local so values stay auditable)
_SODA_D = 0.066                                       # 66 mm body dia (12oz std)
_SODA_H = 0.122                                       # 122 mm height
_SODA_BROADSIDE = _SODA_D * _SODA_H                   # ~0.00805 m^2
_SODA_END = pi * (_SODA_D / 2) ** 2                   # ~0.00342 m^2
_SODA_TUMBLE_A = 0.5 * (_SODA_BROADSIDE + _SODA_END)  # ~0.00574 m^2

_BOTTLE_D = 0.065                                     # ~65 mm body dia (500mL PET)
_BOTTLE_H = 0.21                                      # ~210 mm height
_BOTTLE_BROADSIDE = _BOTTLE_D * _BOTTLE_H             # ~0.01365 m^2
_BOTTLE_END = pi * (_BOTTLE_D / 2) ** 2               # ~0.00332 m^2
_BOTTLE_TUMBLE_A = 0.5 * (_BOTTLE_BROADSIDE + _BOTTLE_END)  # ~0.00849 m^2

_A4_AREA = 0.210 * 0.297                              # 0.06237 m^2 (broadside)


# Ordered most-ballistic -> most-leaf-like (terminal velocity high -> low).
# Order verified by tests/test_objects.py::test_ordering_high_to_low_terminal_velocity
OBJECT_LIBRARY: Dict[str, PhysicalObject] = {
    "soda_can_full": PhysicalObject(
        name="Soda Can (full)", short_name="soda_can_full",
        mass_kg=0.385, drag_coefficient=0.9, cross_section_m2=_SODA_TUMBLE_A,
        color="#f43f5e", emoji="🥤",
        # 355mL liquid (~370g) + ~14g aluminum shell = ~385g
        # (candimension.com, smartinches.com). Tumbling cylinder.
        notes="355mL sealed; ~385g. Tumbling cylinder, Cd avg ~0.9. v_t ~35 m/s.",
    ),
    "water_bottle_full": PhysicalObject(
        name="Water Bottle (full)", short_name="water_bottle_full",
        mass_kg=0.515, drag_coefficient=0.9, cross_section_m2=_BOTTLE_TUMBLE_A,
        color="#22d3ee", emoji="💧",
        # 500g water + ~15g PET (shunpoly.com, bottlefirst.com).
        # Dense, mostly stable; tumbling-average Cd between cylinder
        # broadside (~1.1) and end-on (~0.8).
        notes="500mL sealed PET; ~515g. Cd 0.8-1.1 by axis; using 0.9.",
    ),
    "tennis_ball": PhysicalObject(
        name="Tennis Ball", short_name="tennis_ball",
        mass_kg=0.058, drag_coefficient=0.55, cross_section_m2=pi * 0.0335 ** 2,
        color="#bef264", emoji="🎾",
        # ITF: 56.0-59.4 g, dia 65.41-68.58 mm. Cd ~0.55 (Mehta 2008
        # onlinelibrary.wiley.com/doi/full/10.1002/jst.11). Reference ballistic.
        notes="ITF spec ~58g, 67mm. Fuzzy nap: Cd ~0.55 (Mehta 2008).",
    ),
    "aluminum_foil_ball": PhysicalObject(
        name="Foil Ball", short_name="aluminum_foil_ball",
        mass_kg=0.012, drag_coefficient=0.6, cross_section_m2=pi * 0.025 ** 2,
        color="#94a3b8", emoji="🌕",
        # Tightly crumpled ~30 cm square of standard kitchen foil (~12g).
        # ~5cm dia rough sphere; surface dimples reduce Cd vs smooth sphere.
        notes="Hand-crumpled ~5cm sphere from kitchen foil; ~12g. Cd ~0.6.",
    ),
    "banana_peel": PhysicalObject(
        name="Banana Peel", short_name="banana_peel",
        mass_kg=0.040, drag_coefficient=1.1, cross_section_m2=0.012,
        color="#facc15", emoji="🍌",
        # ~35-40% of ~180g banana = ~60g whole (researchgate Cavendish);
        # used/eaten state ~40g. Splayed strips tumble unpredictably;
        # silhouette ~12 x 10 cm averaged across rotation.
        notes="Used 4-strip peel ~40g; tumbling, Cd 0.9-1.3, using 1.1.",
    ),
    "beer_can_empty": PhysicalObject(
        name="Beer Can (empty)", short_name="beer_can_empty",
        mass_kg=0.014, drag_coefficient=0.95, cross_section_m2=_SODA_TUMBLE_A,
        color="#fbbf24", emoji="🍺",
        # Standard 12oz aluminum shell ~14g (cask.com, candimension.com).
        # Same geometry as soda can but featherweight -> drag dominates.
        notes="12oz aluminum shell, ~14g, uncrushed. Tumbling Cd ~0.95.",
    ),
    "soda_can_empty": PhysicalObject(
        name="Soda Can (empty, uncrushed)", short_name="soda_can_empty",
        mass_kg=0.014, drag_coefficient=0.95, cross_section_m2=_SODA_TUMBLE_A,
        color="#a78bfa", emoji="🥫",
        # Same geometry/mass as beer can; kept distinct for HUD/labelling.
        # Crushed variant would have ~30% area and Cd ~1.0 (irregular).
        notes="12oz aluminum, uncrushed, ~14g. Crushed would tumble differently.",
    ),
    "paper_ball_crumpled": PhysicalObject(
        name="Crumpled Paper Ball", short_name="paper_ball_crumpled",
        mass_kg=0.005, drag_coefficient=0.7, cross_section_m2=pi * 0.03 ** 2,
        color="#fb923c", emoji="📄",
        # 80gsm A4 = 5g (papersizes.org). Crumpled to ~6cm dia.
        # Irregular surface: Cd between sphere (0.47) and rough cube (~0.8).
        notes="A4 80gsm crumpled to ~6cm; ~5g. Cd ~0.7 (rough sphere).",
    ),
    "water_bottle_empty": PhysicalObject(
        name="Water Bottle (empty)", short_name="water_bottle_empty",
        mass_kg=0.015, drag_coefficient=0.95, cross_section_m2=_BOTTLE_TUMBLE_A,
        color="#5eead4", emoji="🧴",
        # ~15g PET + cap, sealed (so it doesn't deform mid-flight).
        # Same geometry as full bottle; tiny mass -> drag dominates.
        notes="500mL PET capped, ~15g. Stable shape, very low ballistic coeff.",
    ),
    "paper_sheet_flat": PhysicalObject(
        name="Paper Sheet (A4, flat)", short_name="paper_sheet_flat",
        mass_kg=0.005, drag_coefficient=1.28, cross_section_m2=_A4_AREA,
        color="#f472b6", emoji="📃",
        # Held flat: extreme drag, leaf-like terminal v ~1 m/s.
        # Real paper flutters; we use NASA Glenn flat-plate Cd=1.28 as
        # a worst-case envelope (most leaf-like behaviour).
        notes="A4 80gsm flat; flutters in reality. Cd=1.28 (NASA flat plate).",
    ),
}


# Dict key must equal short_name (also enforced by tests).
assert all(k == v.short_name for k, v in OBJECT_LIBRARY.items()), \
    "OBJECT_LIBRARY key must match PhysicalObject.short_name"
