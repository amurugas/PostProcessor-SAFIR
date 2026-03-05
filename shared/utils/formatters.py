"""
shared.utils.formatters
~~~~~~~~~~~~~~~~~~~~~~~
Data formatting helpers for reports and dashboard labels.
"""

from __future__ import annotations

from typing import Any, Sequence


def format_value(value: float, decimals: int = 3, unit: str = "") -> str:
    """Format a numeric *value* to *decimals* decimal places.

    Parameters
    ----------
    value:
        The number to format.
    decimals:
        Number of decimal places (default 3).
    unit:
        Optional unit string appended after the number (e.g. ``"°C"``).

    Returns
    -------
    str
        Formatted string, e.g. ``"3.142 m"`` or ``"273.150°C"``.

    Examples
    --------
    >>> format_value(3.14159, decimals=2, unit="m")
    '3.14 m'
    >>> format_value(273.15, unit="°C")
    '273.150°C'
    """
    formatted = f"{value:.{decimals}f}"
    if unit:
        separator = " " if not unit.startswith("°") else ""
        return f"{formatted}{separator}{unit}"
    return formatted


def format_table_row(values: Sequence[Any], width: int = 15) -> str:
    """Format a sequence of *values* as a fixed-width table row.

    Parameters
    ----------
    values:
        Iterable of column values.
    width:
        Column width in characters (default 15).

    Returns
    -------
    str
        A single line with each value left-justified in a column of
        *width* characters, separated by a ``|`` delimiter.

    Examples
    --------
    >>> format_table_row(["Node", "X", "Y", "Z"])
    'Node           |X              |Y              |Z              '
    """
    return "|".join(str(v).ljust(width) for v in values)


def scale_n_to_kips(value: float) -> float:
    """Convert a force from Newtons to kips (1 kip = 4 448.22 N)."""
    return value / 4448.22


def scale_nm_to_kips_ft(value: float) -> float:
    """Convert a moment from N·m to kip-feet (1 kip·ft = 1 355.82 N·m)."""
    return value / (4448.22 * 0.3048)


def scale_m_to_inches(value: float) -> float:
    """Convert metres to inches (1 m = 39.3701 in)."""
    return value * 39.3701
