import pathlib


def check_path(path: pathlib.Path):
    """
    Check if the path is a valid file or directory.

    Args:
        path: The path to check.

    Returns:
        A tuple of (bool, str). The first element is True if the path is valid,
        False otherwise. The second element is a message to be displayed to
        the user.
    """
    if not path.exists():
        return False, "File or directory does not exist!"
    if not path.is_absolute():
        return False, "Path must be absolute!"
    if not path.is_file() and not path.is_dir():
        return False, "File or directory does not exist!"

    if path.suffix == ".apk":
        return True, "Found APK file! Click the button below to install"
    elif path.suffix == ".zip":
        return True, "Found ZIP archive! Click the button below to install"
    elif path.is_dir():
        return True, "Found directory! Click the button below to install"
    else:
        return False, "Unknown file type!"

