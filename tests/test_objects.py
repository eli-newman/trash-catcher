"""
Sanity tests for the physical-objects library.

Verifies physical plausibility (mass/Cd/area in believable ranges), schema
consistency (key = short_name, valid hex colors, single-grapheme emoji), and
computes terminal velocity for each entry so the human reviewer sees the
spectrum of behaviour from ballistic to leaf-like.
"""

import math
import re
import unicodedata

import pytest

from src.objects import OBJECT_LIBRARY, PhysicalObject


# --- physical constants for terminal-velocity calculation ---
RHO_AIR = 1.225   # kg/m^3, sea-level @ 15 C
G = 9.81          # m/s^2

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def terminal_velocity(obj: PhysicalObject) -> float:
    """v_t = sqrt(2 m g / (rho Cd A)) -- balance of weight and drag."""
    return math.sqrt(
        2.0 * obj.mass_kg * G
        / (RHO_AIR * obj.drag_coefficient * obj.cross_section_m2)
    )


# Materialise once so parametrize ids are stable
_ITEMS = list(OBJECT_LIBRARY.items())


@pytest.mark.parametrize("key,obj", _ITEMS, ids=[k for k, _ in _ITEMS])
def test_physical_plausibility(key, obj):
    """Mass, drag, and area must lie in physically believable ranges."""
    assert obj.mass_kg > 0, f"{key}: mass must be positive"
    assert obj.mass_kg < 5.0, f"{key}: mass {obj.mass_kg} > 5 kg is implausible"

    assert 0.1 < obj.drag_coefficient < 2.5, (
        f"{key}: Cd={obj.drag_coefficient} outside plausible 0.1-2.5"
    )
    assert 0.0001 < obj.cross_section_m2 < 0.1, (
        f"{key}: area={obj.cross_section_m2} outside plausible 1cm^2-1000cm^2"
    )


@pytest.mark.parametrize("key,obj", _ITEMS, ids=[k for k, _ in _ITEMS])
def test_short_name_matches_key(key, obj):
    """Dict key must equal short_name -- enforces single source of truth."""
    assert key == obj.short_name


@pytest.mark.parametrize("key,obj", _ITEMS, ids=[k for k, _ in _ITEMS])
def test_color_is_valid_hex(key, obj):
    """Color must be a 7-char hex string '#rrggbb'."""
    assert HEX_RE.match(obj.color), (
        f"{key}: color {obj.color!r} not a valid 7-char hex"
    )


@pytest.mark.parametrize("key,obj", _ITEMS, ids=[k for k, _ in _ITEMS])
def test_emoji_is_single_grapheme(key, obj):
    """Emoji should be one printable, non-empty grapheme."""
    e = obj.emoji
    assert e, f"{key}: emoji is empty"
    # Allow ZWJ sequences and variation selectors but no whitespace / multiple
    # base graphemes. Heuristic: no whitespace and length <= 4 codepoints.
    assert not any(ch.isspace() for ch in e), f"{key}: emoji contains whitespace"
    assert len(e) <= 4, f"{key}: emoji {e!r} too many codepoints (likely multi-glyph)"
    # First codepoint must be a 'symbol' or 'other' category (typical for emoji).
    cat = unicodedata.category(e[0])
    assert cat.startswith(("S", "C", "L")), (
        f"{key}: first codepoint of emoji {e!r} has unexpected category {cat}"
    )


def test_required_objects_present():
    """The simulator agent depends on these exact short_names existing."""
    required = {
        "tennis_ball", "soda_can_full", "soda_can_empty",
        "beer_can_empty", "water_bottle_full", "water_bottle_empty",
        "paper_ball_crumpled", "paper_sheet_flat", "banana_peel",
    }
    missing = required - OBJECT_LIBRARY.keys()
    assert not missing, f"missing required objects: {missing}"


def test_soda_can_full_mass_snapshot():
    """Snapshot guard: a sealed 12oz soda can should be 350-420 g."""
    m = OBJECT_LIBRARY["soda_can_full"].mass_kg
    assert 0.35 <= m <= 0.42, f"soda_can_full mass {m} kg outside expected range"


def test_terminal_velocity_spectrum(capsys):
    """
    Compute terminal velocity for every object, print the spectrum, and
    assert the two anchor points (tennis ball ballistic, paper sheet leaf-like).
    """
    rows = []
    for key, obj in OBJECT_LIBRARY.items():
        v_t = terminal_velocity(obj)
        rows.append((obj.name, obj.mass_kg, obj.drag_coefficient,
                     obj.cross_section_m2, v_t))

    # Print to stdout (visible with pytest -s) so the reviewer can audit.
    header = f"\n{'name':<32} {'mass(kg)':>9} {'Cd':>5} {'A(m^2)':>9} {'v_t(m/s)':>9}"
    print(header)
    print("-" * len(header))
    for name, m, cd, a, v in rows:
        print(f"{name:<32} {m:>9.4f} {cd:>5.2f} {a:>9.5f} {v:>9.2f}")

    # Anchors: the two ends of the realism spectrum.
    v_tennis = terminal_velocity(OBJECT_LIBRARY["tennis_ball"])
    v_sheet = terminal_velocity(OBJECT_LIBRARY["paper_sheet_flat"])
    assert v_tennis > 20.0, f"tennis ball v_t={v_tennis:.2f} should be > 20 m/s"
    assert v_sheet < 3.0, f"flat paper v_t={v_sheet:.2f} should be < 3 m/s"


def test_ordering_high_to_low_terminal_velocity():
    """Library should be ordered most-ballistic to most-leaf-like."""
    v_ts = [terminal_velocity(o) for o in OBJECT_LIBRARY.values()]
    # Strictly non-increasing across the catalogue.
    for i in range(len(v_ts) - 1):
        assert v_ts[i] >= v_ts[i + 1] - 0.01, (
            f"ordering broken at index {i}: "
            f"{list(OBJECT_LIBRARY)[i]}={v_ts[i]:.2f} < "
            f"{list(OBJECT_LIBRARY)[i+1]}={v_ts[i+1]:.2f}"
        )


def test_dataclass_is_frozen():
    """PhysicalObject must be immutable so it's safe to share across threads."""
    obj = next(iter(OBJECT_LIBRARY.values()))
    with pytest.raises((AttributeError, Exception)):
        obj.mass_kg = 999.0  # type: ignore[misc]
