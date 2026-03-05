"""
shared.visualization.export_utils
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Utilities for exporting SAFIR result data to common file formats.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def export_to_csv(df: "pd.DataFrame", output_path: str, index: bool = False) -> str:
    """Write *df* to a CSV file at *output_path*.

    Parameters
    ----------
    df:
        :class:`pandas.DataFrame` to export.
    output_path:
        Destination file path (created if it does not exist).
    index:
        Whether to include the DataFrame index column (default ``False``).

    Returns
    -------
    str
        Absolute path of the written file.
    """
    abs_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    df.to_csv(abs_path, index=index)
    return abs_path


def export_to_excel(
    df: "pd.DataFrame",
    output_path: str,
    sheet_name: str = "Results",
    index: bool = False,
) -> str:
    """Write *df* to an Excel workbook at *output_path*.

    Requires ``openpyxl`` (install via ``pip install openpyxl``).

    Parameters
    ----------
    df:
        :class:`pandas.DataFrame` to export.
    output_path:
        Destination ``.xlsx`` file path.
    sheet_name:
        Name of the worksheet (default ``"Results"``).
    index:
        Whether to include the DataFrame index column (default ``False``).

    Returns
    -------
    str
        Absolute path of the written file.
    """
    abs_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    df.to_excel(abs_path, sheet_name=sheet_name, index=index, engine="openpyxl")
    return abs_path


def ensure_output_dir(base_dir: str, sub: str = "output") -> str:
    """Create and return ``base_dir/sub``, creating intermediate dirs."""
    path = os.path.join(base_dir, sub)
    os.makedirs(path, exist_ok=True)
    return path
