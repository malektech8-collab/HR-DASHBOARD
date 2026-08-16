"""Declared column derivations (Phase 1a).

Real HRIS exports do not carry `is_saudi`; they carry `nationality`. The
contract declares the gap and names a derivation rule; this module implements
the named rules.

Two hard constraints, both deliberate:

1. **Registry, never eval.** A contract names a rule (`derivation:
   nationality_is_saudi`); it never carries an expression. Nothing here
   compiles, evals, or otherwise executes text from a YAML file. A contract is
   data supplied by an operator — treating it as code would make a schema file
   an execution vector.

2. **Fail loudly on unrecognised input.** `is_saudi` feeds the Saudization
   percentage, which is the most consequential number in the product and the
   basis of Nitaqat banding. Defaulting an unrecognised nationality to False
   would silently understate it. Unknown values raise DerivationError naming
   the offending values, so the operator extends the alias table or fixes the
   export — a decision that must be made explicitly, not absorbed.

Nothing in this module runs during demo-mode ingestion.
"""


class DerivationError(ValueError):
    """Raised when a declared derivation cannot be computed safely."""


# Values that mean "Saudi national". Normalised (see _normalise) before lookup.
# Extend deliberately — every addition changes the Saudization figure.
_SAUDI_ALIASES = {
    "saudi",
    "saudi arabian",
    "saudi arabia",
    "ksa",
    "sa",
    "sau",
    "saudian",
    "السعودية",
    "سعودي",
    "سعودية",
    "سعوديه",
    "المملكة العربية السعودية",
}

# Values known to be non-Saudi nationalities present in current data. Anything
# outside BOTH sets raises rather than defaulting.
_NON_SAUDI_ALIASES = {
    "american", "australian", "british", "canadian", "egyptian", "german",
    "jordanian", "syrian", "indian", "pakistani", "bangladeshi", "filipino",
    "nepali", "sudanese", "yemeni", "lebanese", "tunisian", "moroccan",
    "algerian", "turkish", "sri lankan", "indonesian", "ethiopian", "kenyan",
    "emirati", "kuwaiti", "bahraini", "omani", "qatari",
    "مصري", "أردني", "سوري", "هندي", "باكستاني", "يمني", "سوداني",
    "فلبيني", "بنغلاديشي", "لبناني", "مغربي", "تونسي",

    # Arabic forms met in a real KSA export (upload-mapping cycle B). Several
    # already had an ENGLISH entry above - british, turkish, kenyan,
    # bangladeshi, nepali - which did not help, because this table matches the
    # value as the client WROTE it and they wrote it in Arabic.
    #
    # No padded variants. Two of these arrived with trailing whitespace and
    # `_normalise` already strips and collapses it, so a padded entry here
    # would be a second spelling of a rule that is already enforced once.
    "الأوزبكستاني",       # Uzbek
    "البوسنية",           # Bosnian
    "البولندي",           # Polish
    "الغاني",             # Ghanaian
    "الكيني",             # Kenyan
    "برتغالي",            # Portuguese
    "بريطاني",            # British
    "بنجلاديش",           # Bangladeshi
    "تركي",               # Turkish
    "جنوب افريقي",        # South African
    "جيبوتي",             # Djiboutian
    "دومينيكا",           # Dominican
    "روسي",               # Russian
    "صومالي",             # Somali
    "غيانا",              # Guyanese
    "غينيا",              # Guinean
    "فلسطيني",            # Palestinian
    "نيبالي",             # Nepali

    # A CATEGORY, not a nationality. `False` is the right answer and is why it
    # sits in this table - but the actual nationality is unrecorded, and
    # Nitaqat reporting needs more than the Saudi/non-Saudi binary. The
    # derivation cannot say so (it returns booleans), so the observation is
    # raised where the client will read it: `flag_values` on `nationality` in
    # the employees contract.
    "غير سعودي",          # literally "non-Saudi"
}

# Normalisation moved to scripts/text.py so header and value matching can share
# it. Re-exported here because this module's callers already import it.
from text import _normalise, normalise  # noqa: E402,F401


def _normalised_set(values):
    return {_normalise(v) for v in values}


_SAUDI_NORM = _normalised_set(_SAUDI_ALIASES)
_NON_SAUDI_NORM = _normalised_set(_NON_SAUDI_ALIASES)


def nationality_is_saudi(values):
    """Map a sequence of nationality values to booleans.

    Returns a list aligned with `values`. None/empty is returned as None
    (unknown), not False — a missing nationality is a data-quality exception,
    not evidence of non-Saudi status.

    Raises DerivationError listing every unrecognised value.
    """
    out = []
    unknown = set()
    for v in values:
        n = _normalise(v)
        if not n:
            out.append(None)
        elif n in _SAUDI_NORM:
            out.append(True)
        elif n in _NON_SAUDI_NORM:
            out.append(False)
        else:
            unknown.add(str(v))
            out.append(None)
    if unknown:
        raise DerivationError(
            "nationality_is_saudi: unrecognised nationality value(s) "
            "{}. Refusing to guess — is_saudi drives the Saudization "
            "percentage and Nitaqat banding. Add each value to the Saudi or "
            "non-Saudi alias table in scripts/derivations.py, or correct the "
            "source export.".format(sorted(unknown))
        )
    return out


# name -> callable. A contract's `derivation:` key is resolved against this.
REGISTRY = {
    "nationality_is_saudi": nationality_is_saudi,
}


def resolve(rule_name):
    """Look up a derivation by name. Unknown names raise; nothing is eval'd."""
    try:
        return REGISTRY[rule_name]
    except KeyError:
        raise DerivationError(
            "Unknown derivation rule '{}'. Known rules: {}. Derivations are "
            "resolved from a registry; contracts never carry executable "
            "expressions.".format(rule_name, sorted(REGISTRY))
        )


def derive_column(column_spec, source_values):
    """Apply the derivation declared on a column spec.

    `column_spec` is a canonical-schema column dict carrying `derivation`
    (rule name) and `derived_from` (source column name).
    """
    rule = column_spec.get("derivation")
    if not rule:
        raise DerivationError(
            "Column '{}' has no `derivation` key.".format(column_spec.get("name"))
        )
    return resolve(rule)(source_values)
