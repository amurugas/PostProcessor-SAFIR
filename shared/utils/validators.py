"""
shared.utils.validators
~~~~~~~~~~~~~~~~~~~~~~~
Lightweight validation helpers used by parsers and database managers.

All public functions raise :class:`ValueError` (or a subclass) on
failure so callers can catch a single exception type.
"""

import os


def validate_file_exists(path: str, label: str = "File") -> str:
    """Assert that *path* points to an existing regular file.

    Parameters
    ----------
    path:
        Filesystem path to check.
    label:
        Human-readable name used in the error message.

    Returns
    -------
    str
        The normalised absolute path.

    Raises
    ------
    ValueError
        If the path does not exist or is not a regular file.
    """
    abs_path = os.path.abspath(path)
    if not os.path.isfile(abs_path):
        raise ValueError(f"{label} not found: {abs_path}")
    return abs_path


def validate_db_path(path: str) -> str:
    """Validate that *path* is usable as an SQLite database path.

    The parent directory must already exist.

    Parameters
    ----------
    path:
        Filesystem path for the ``.db`` file.

    Returns
    -------
    str
        The normalised absolute path.

    Raises
    ------
    ValueError
        If the parent directory does not exist.
    """
    abs_path = os.path.abspath(path)
    parent = os.path.dirname(abs_path)
    if not os.path.isdir(parent):
        raise ValueError(
            f"Parent directory for database does not exist: {parent}"
        )
    return abs_path


def validate_xml_path(path: str) -> str:
    """Validate that *path* points to an existing XML file.

    Parameters
    ----------
    path:
        Filesystem path to a SAFIR XML results file.

    Returns
    -------
    str
        The normalised absolute path.

    Raises
    ------
    ValueError
        If the path does not exist or does not end with ``.xml``
        (case-insensitive).
    """
    abs_path = validate_file_exists(path, label="XML file")
    if not abs_path.lower().endswith(".xml"):
        raise ValueError(f"Expected an .xml file, got: {abs_path}")
    return abs_path
