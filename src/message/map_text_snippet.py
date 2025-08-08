import re

import bs4


def first_n_words(s: str, n: int) -> str:
    # We take the first n * 32 characters as to avoid processing the entire text, which might be
    # large. This is for obvious reasons imperfect but probably good enough for manifesting a short,
    # representative snippet.
    words = re.split(r"\s+", s[: n * 32])
    return " ".join(words[:n]) + ("…" if len(words) > n else "")


def text_snippet(s: str) -> str:
    soup = bs4.BeautifulSoup(s, features="html.parser")
    return first_n_words(soup.get_text(), 16)
