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



# --------------------------------------------------------------------------
# Columns a source system is asked for but does not produce
# --------------------------------------------------------------------------
#
# Four contracts required columns that are OUTPUTS of this pipeline rather than
# inputs a client's system exports - asking the client to compute our metrics
# before uploading. These rules are the correction; dropping the required flag
# is the consequence.


def sla_breached(created_at, sla_hours, closed_at, as_of):
    """Whether a request missed its SLA target.

    RANKED FIRST because its absent-column behaviour is SILENT. `validate_data`
    filters `sla_breached == True`, and `NULL == True` is NULL, so with the
    column missing every row is dropped and the file reports as having NO SLA
    BREACHES - a clean bill of health for the domain whose entire purpose is
    SLA tracking. A check that goes quiet is worse than one that gets noisy,
    because noise gets noticed.

    `as_of` is the run's reference time, and is why this rule is
    parameterised: a request that is still OPEN is breached when the deadline
    is already behind us, and no column in the file carries "now".

    NULL, never False, when the answer is unknowable - an unknown SLA is not a
    met SLA.
    """
    import datetime

    def _parse(value):
        if value is None or value == "":
            return None
        if isinstance(value, (datetime.datetime, datetime.date)):
            return value if isinstance(value, datetime.datetime) else (
                datetime.datetime.combine(value, datetime.time()))
        try:
            return datetime.datetime.fromisoformat(str(value)[:19])
        except ValueError:
            return None

    out = []
    for created, hours, closed in zip(created_at, sla_hours, closed_at):
        start = _parse(created)
        try:
            budget = None if hours in (None, "") else float(hours)
        except (TypeError, ValueError):
            budget = None
        if start is None or budget is None:
            out.append(None)
            continue
        deadline = start + datetime.timedelta(hours=budget)
        finished = _parse(closed)
        # Closed: compare against when it actually closed. Still open: against
        # the reference time, because an open request past its deadline has
        # breached whether or not anyone has closed it.
        out.append((finished if finished is not None else as_of) > deadline)
    return out


def net_late_minutes(late_minutes, excused_late_minutes):
    """Raw lateness less the part formally excused, floored at zero.

    DERIVED ALWAYS, and the supplied column is kept as EVIDENCE rather than
    replaced by this: `mart_attendance_exceptions` compares a client's own
    figure against `calculated_net_late_minutes` and reports a disagreement.
    That reconciliation says whether their attendance engine agrees with our
    arithmetic, and it is worth more than the required flag - so the column is
    relaxed, not removed, and the check is gated on it being provided.
    """
    out = []
    for raw, excused in zip(late_minutes, excused_late_minutes):
        try:
            base = None if raw in (None, "") else float(raw)
        except (TypeError, ValueError):
            base = None
        try:
            off = 0.0 if excused in (None, "") else float(excused)
        except (TypeError, ValueError):
            off = 0.0
        out.append(None if base is None else int(max(base - off, 0)))
    return out


def missing_punch_count(actual_check_in, actual_check_out):
    """How many of the two punches this record is missing: 0, 1 or 2.

    Derived from the punches, which is why the attendance inversion is fixed in
    the same cycle: the contract required this figure while treating the
    columns it is computed from as optional.
    """
    out = []
    for check_in, check_out in zip(actual_check_in, actual_check_out):
        out.append(int(check_in in (None, "")) + int(check_out in (None, "")))
    return out


# name -> callable. A contract's `derivation:` key is resolved against this.
REGISTRY = {
    "nationality_is_saudi": nationality_is_saudi,
    "sla_breached": sla_breached,
    "net_late_minutes": net_late_minutes,
    "missing_punch_count": missing_punch_count,
}

# Rules needing a value from the RUN rather than from the file. Declared here,
# in reviewed code, for the same reason the rules themselves are: a contract
# names a rule and never carries an expression or a parameter.
_PARAMETERISED = {"sla_breached"}


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


def source_columns(column_spec):
    """The source column names a derivation reads, always as a list.

    `derived_from` accepts a single name or a list. The single-name form is
    what `is_saudi` uses and it keeps working untouched - the extension is
    additive, because a contract that already parses must not change meaning.
    """
    declared = column_spec.get("derived_from")
    if declared is None:
        return []
    if isinstance(declared, str):
        return [declared]
    return list(declared)


def needs_parameter(rule_name):
    """Rules that need something from the RUN, not from the file.

    `sla_breached` is the case: "breached" for a still-open request means the
    deadline is behind us, and no column carries "now". The reference time is
    supplied by ingest.

    It stays a REGISTRY lookup. A contract names a rule and never carries an
    expression - that rule is unchanged by this extension, and is the reason
    the parameter is declared here in code rather than in the YAML.
    """
    return rule_name in _PARAMETERISED


def derive_column(column_spec, sources, parameter=None):
    """Apply the derivation declared on a column spec.

    `column_spec` carries `derivation` (rule name) and `derived_from` (one
    source column name, or a list of them).

    `sources` is either a single sequence of values - the original single-source
    form, kept so `is_saudi` and any caller of it are unaffected - or a mapping
    of column name to sequence for a multi-source rule.

    `parameter` is passed only to rules that declare they need one.
    """
    rule = column_spec.get("derivation")
    if not rule:
        raise DerivationError(
            "Column '{}' has no `derivation` key.".format(column_spec.get("name"))
        )
    function = resolve(rule)
    names = source_columns(column_spec)

    if isinstance(sources, dict):
        missing = [n for n in names if n not in sources]
        if missing:
            raise DerivationError(
                "Column '{}' derives from {} but {} were not supplied to "
                "derive_column.".format(column_spec.get("name"), names, missing))
        ordered = [sources[n] for n in names]
    else:
        # Single-source form. One declared source or the rule takes one list.
        ordered = [sources]

    if needs_parameter(rule):
        return function(*ordered, parameter)
    return function(*ordered)
