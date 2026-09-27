def slugify(text):
    """Convert a string into a URL-friendly slug."""
    return "-".join(text.strip().lower().split())


def chunked(iterable, size):
    """Yield successive chunks of `size` from `iterable`."""
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]
