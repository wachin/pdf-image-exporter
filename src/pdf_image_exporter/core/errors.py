"""User-facing error message mapping."""

from __future__ import annotations


def user_error_message(error: Exception) -> str:
    """Return a concise user-facing message for common failures."""

    if isinstance(error, FileExistsError):
        return (
            "An output file already exists. Change the conflict policy, choose a "
            "different output folder, or adjust the naming template."
        )
    if isinstance(error, PermissionError):
        return "The selected location is not writable. Choose another folder."
    if isinstance(error, FileNotFoundError):
        return "A required file or folder could not be found."
    if isinstance(error, NotADirectoryError):
        return "The selected path is not a folder."
    if isinstance(error, ValueError):
        return str(error)
    return "The operation could not be completed. See the log for technical details."
