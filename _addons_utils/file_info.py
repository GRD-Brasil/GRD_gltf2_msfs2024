import os
import stat

def is_read_only(filepath: str) -> bool:
    """Check if a file is read only."""
    try:
        info = os.stat(filepath)
    except FileNotFoundError:
        return False
    if info.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY:
        return True
    return False
