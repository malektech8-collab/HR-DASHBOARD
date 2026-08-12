"""Text normalisation shared by everything that compares Arabic strings.

Promoted out of `derivations.py` (upload-mapping cycle A). It was written for
nationality matching; header matching and value-vocabulary matching need
exactly the same thing, and `PRODUCT-ARCHITECTURE` §4 names "Arabic column
headers with inconsistent spacing and naming" as a real-world case rather than
an edge case.

One implementation, three callers. A second copy would diverge on the day
someone adds a variant to one of them.
"""
import unicodedata


# Tashkeel (U+064B-U+0652), Quranic honorifics (U+0610-U+061A) and the
# superscript alef (U+0670). Deliberately NOT U+0621-U+064A, which are the
# Arabic letters themselves.
_ARABIC_DIACRITICS = dict.fromkeys(
    list(range(0x064B, 0x0653)) + list(range(0x0610, 0x061B)) + [0x0670]
)


def _normalise(value):
    """Casefold, strip, collapse whitespace, and normalise Arabic forms.

    Handles the inconsistent spacing and alef/ya variants that appear in real
    Arabic exports.
    """
    if value is None:
        return ""
    s = unicodedata.normalize("NFKC", str(value)).strip()
    s = " ".join(s.split())
    s = s.translate(_ARABIC_DIACRITICS)
    s = s.replace("ـ", "")                       # tatweel
    for a in "آأإٱ":              # alef variants -> bare alef
        s = s.replace(a, "ا")
    s = s.replace("ى", "ي")                 # alef maqsura -> ya
    s = s.replace("ة", "ه")                 # ta marbuta -> ha
    return s.casefold()


def normalise(value):
    """Public name. `_normalise` remains as an alias for existing callers."""
    return _normalise(value)
