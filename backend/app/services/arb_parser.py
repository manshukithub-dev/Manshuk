from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


PRINTF_PLACEHOLDER_RE = re.compile(r"%(?:\d+\$)?[-+#0 ]*\d*(?:\.\d+)?[sdifuxX%]|\$\d+")
HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
ICU_HEAD_RE = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,\s*(plural|select|selectordinal)\s*,(.*)$", re.DOTALL)
ICU_SIMPLE_ARG_RE = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)(?:\s*,\s*[a-zA-Z]+(?:\s*,\s*[^}]+)?)?\s*$")
VALID_PLURAL_CATEGORIES = {"=0", "=1", "=2", "zero", "one", "two", "few", "many", "other"}


class ARBValidationError(ValueError):
    """Raised when an ARB file violates JSON or Flutter gen-l10n structure."""


@dataclass
class ICUBlock:
    variable: str
    kind: str  # plural, select, selectordinal
    branches: dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedARB:
    locale: str | None
    entries: dict[str, str]
    metadata: dict[str, dict[str, Any]]
    global_attrs: dict[str, Any]
    key_order: list[str]
    line_count: int


def extract_icu_structure(text: str) -> tuple[set[str], list[ICUBlock], list[str]]:
    """
    Parse ICU MessageFormat string using balanced brace scanning.
    Returns (placeholders, icu_blocks, syntax_errors).
    Placeholders inside '#' of plural branches are mapped to the plural variable.
    """
    placeholders: set[str] = set()
    icu_blocks: list[ICUBlock] = []
    errors: list[str] = []

    # Also capture printf/positional placeholders (%s, %d, $1)
    for match in PRINTF_PLACEHOLDER_RE.finditer(text):
        token = match.group(0)
        if token != "%%":
            placeholders.add(token)

    def _scan(segment: str) -> None:
        i = 0
        n = len(segment)
        while i < n:
            ch = segment[i]
            # Escaped single quotes in ICU MessageFormat ('{' or '}')
            if ch == "'":
                if i + 1 < n and segment[i + 1] == "'":
                    i += 2
                    continue
                if i + 1 < n and segment[i + 1] in "{}#":
                    end_quote = segment.find("'", i + 2)
                    if end_quote != -1:
                        i = end_quote + 1
                        continue
            if ch == "{":
                depth = 1
                j = i + 1
                while j < n and depth > 0:
                    if segment[j] == "{":
                        depth += 1
                    elif segment[j] == "}":
                        depth -= 1
                    j += 1
                if depth != 0:
                    errors.append("Жабылмаған '{' жақшасы табылды (ICU синтаксис қатесі).")
                    return
                inner = segment[i + 1 : j - 1]
                head_match = ICU_HEAD_RE.match(inner)
                if head_match:
                    var_name, kind, body = head_match.group(1), head_match.group(2), head_match.group(3)
                    placeholders.add(var_name)
                    branches, branch_errors = _parse_icu_branches(body)
                    errors.extend(branch_errors)
                    if "other" not in branches:
                        errors.append(
                            f"ICU {kind} құрылымында міндетті 'other{{...}}' тармағы жоқ ({var_name})."
                        )
                    if kind in ("plural", "selectordinal"):
                        for cat in branches:
                            if cat not in VALID_PLURAL_CATEGORIES and not re.match(r"^=\d+$", cat):
                                errors.append(f"Белгісіз ICU көпше санаты: '{cat}'.")
                    icu_blocks.append(ICUBlock(variable=var_name, kind=kind, branches=branches))
                    for branch_text in branches.values():
                        _scan(branch_text)
                else:
                    arg_match = ICU_SIMPLE_ARG_RE.match(inner)
                    if arg_match:
                        placeholders.add(arg_match.group(1))
                    elif inner.strip() == "":
                        errors.append("Бос '{}' плейсхолдері табылды.")
                    else:
                        # Could still be non-standard placeholder token like {player_name} or {0}
                        cleaned = inner.strip()
                        if re.match(r"^[a-zA-Z0-9_.-]+$", cleaned):
                            placeholders.add(cleaned)
                        else:
                            errors.append(f"Жарамсыз ICU өрнегі немесе плейсхолдер: '{{{inner}}}'.")
                i = j
            elif ch == "}":
                errors.append("Артық '}' жақшасы табылды (ICU синтаксис қатесі).")
                i += 1
            else:
                i += 1

    _scan(text)
    return placeholders, icu_blocks, errors


def _parse_icu_branches(body: str) -> tuple[dict[str, str], list[str]]:
    branches: dict[str, str] = {}
    errors: list[str] = []
    i = 0
    n = len(body)
    while i < n:
        while i < n and body[i].isspace():
            i += 1
        if i >= n:
            break
        key_start = i
        while i < n and not body[i].isspace() and body[i] != "{":
            i += 1
        selector = body[key_start:i].strip()
        while i < n and body[i].isspace():
            i += 1
        if not selector or i >= n or body[i] != "{":
            errors.append(f"ICU тармағының синтаксисі бұзылған: '{body[key_start:min(n, key_start + 25)]}'.")
            break
        depth = 1
        j = i + 1
        while j < n and depth > 0:
            if body[j] == "{":
                depth += 1
            elif body[j] == "}":
                depth -= 1
            j += 1
        if depth != 0:
            errors.append(f"ICU '{selector}' тармағында жақша жабылмаған.")
            break
        branches[selector] = body[i + 1 : j - 1]
        i = j
    return branches, errors


def extract_html_tags(text: str) -> list[str]:
    return HTML_TAG_RE.findall(text)


def parse_arb_content(raw_text: str, filename: str = "file.arb") -> ParsedARB:
    """
    Parse and validate ARB content according to Flutter gen-l10n & ARB specification.
    Raises ARBValidationError with clear Kazakh error description on invalid JSON/ARB.
    """
    if not raw_text or not raw_text.strip():
        raise ARBValidationError(f"«{filename}» файлы бос.")

    # Strip UTF-8 BOM if present
    cleaned = raw_text.lstrip("\ufeff")
    line_count = cleaned.count("\n") + 1

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ARBValidationError(
            f"JSON құрылымы қате ({filename}): {exc.msg} — жол {exc.lineno}, баған {exc.colno}."
        ) from exc

    if not isinstance(data, dict):
        raise ARBValidationError(
            f"ARB файлының түбірлік элементі JSON объектісі ({{...}}) болуы керек ({filename})."
        )

    locale: str | None = None
    entries: dict[str, str] = {}
    metadata: dict[str, dict[str, Any]] = {}
    global_attrs: dict[str, Any] = {}
    key_order: list[str] = list(data.keys())

    for key, value in data.items():
        if key.startswith("@@"):
            global_attrs[key] = value
            if key == "@@locale" and isinstance(value, str):
                locale = value
        elif key.startswith("@"):
            target_key = key[1:]
            if not isinstance(value, dict):
                raise ARBValidationError(
                    f"«{key}» метадеректер өрісі JSON объектісі болуы тиіс ({filename})."
                )
            metadata[target_key] = value
        else:
            if not isinstance(value, str):
                raise ARBValidationError(
                    f"«{key}» кілтінің мәні мәтін (string) болуы тиіс, алынғаны: {type(value).__name__} ({filename})."
                )
            entries[key] = value

    # Check orphan @metadata keys (Flutter gen-l10n fails if @foo exists without foo)
    orphan_meta = [f"@{k}" for k in metadata if k not in entries]
    if orphan_meta:
        sample = ", ".join(orphan_meta[:3])
        raise ARBValidationError(
            f"Негізгі кілті жоқ жетім метадеректер табылды ({sample}) — Flutter gen-l10n стандартына қайшы."
        )

    return ParsedARB(
        locale=locale,
        entries=entries,
        metadata=metadata,
        global_attrs=global_attrs,
        key_order=key_order,
        line_count=line_count,
    )


def validate_arb_for_gen_l10n(
    arb_dict: dict[str, Any],
    source_entries: dict[str, str] | None = None,
    preexisting_unmodified_keys: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """
    Validate an ARB dictionary prior to export so it compiles cleanly under Flutter `gen-l10n`.
    Returns `(blocking_errors, icu_warnings_on_untouched_keys)`.
    """
    errors: list[str] = []
    warnings: list[str] = []
    untouched = preexisting_unmodified_keys or set()

    if not isinstance(arb_dict, dict):
        return ["ARB дерегі JSON объектісі емес."], []

    resource_keys = {k for k in arb_dict if not k.startswith("@")}
    if source_entries:
        missing = [k for k in source_entries if k not in resource_keys]
        if missing:
            errors.append(f"Бастапқы кілттер жоғалған ({len(missing)} кілт): {', '.join(missing[:5])}")

    for key, val in arb_dict.items():
        if key.startswith("@@"):
            continue
        if key.startswith("@"):
            base_key = key[1:]
            if base_key not in resource_keys:
                errors.append(f"Негізгі кілті жоқ метадеректер: {key}")
            if not isinstance(val, dict):
                errors.append(f"{key} метадерегі объект болуы тиіс.")
            else:
                if "description" in val and not isinstance(val["description"], str):
                    errors.append(f"{key}.description мәтін болуы тиіс.")
                if "placeholders" in val and not isinstance(val["placeholders"], dict):
                    errors.append(f"{key}.placeholders объект болуы тиіс.")
        else:
            if not isinstance(val, str):
                errors.append(f"«{key}» мәні string емес.")
                continue
            _, _, icu_errors = extract_icu_structure(val)
            for err in icu_errors:
                if key in untouched:
                    warnings.append(f"[{key}] (Әлі түзетілмеген бастапқы жол) {err}")
                else:
                    errors.append(f"[{key}] {err}")

    return errors, warnings


def export_fixed_arb(
    original_target_raw: str | None,
    source_raw: str,
    updated_entries: dict[str, dict[str, Any]],
    target_locale: str = "kk",
) -> tuple[str, dict[str, Any], list[str]]:
    """
    Build a Flutter gen-l10n compliant ARB JSON preserving key order, untouched values,
    @metadata, ICU structures, and adding valid `x-*` human review metadata inside `@<key>`.

    `updated_entries` maps `key -> {
        "current_target": str,
        "is_fixed": bool,
        "reviewed_by_human": bool,
        "reviewer_name": str | None,
        "reviewed_at": str | None,
    }`

    Returns `(formatted_json_str, export_summary, validation_warnings)`.
    """
    source_parsed = parse_arb_content(source_raw, "source.arb")
    target_parsed = (
        parse_arb_content(original_target_raw, "target.arb")
        if original_target_raw
        else ParsedARB(
            locale=target_locale,
            entries={},
            metadata={},
            global_attrs={"@@locale": target_locale},
            key_order=[],
            line_count=0,
        )
    )

    out: dict[str, Any] = {}

    # 1. Preserve global @@ attributes, ensuring @@locale matches target_locale
    out["@@locale"] = target_parsed.locale or target_locale
    for gk, gv in target_parsed.global_attrs.items():
        if gk != "@@locale":
            out[gk] = gv

    # Determine key ordering: keep target's original order first, then any missing source keys
    ordered_resource_keys: list[str] = []
    seen: set[str] = set()

    base_order = target_parsed.key_order if target_parsed.key_order else source_parsed.key_order
    for raw_k in base_order:
        if raw_k.startswith("@"):
            continue
        if raw_k not in seen:
            ordered_resource_keys.append(raw_k)
            seen.add(raw_k)

    for src_k in source_parsed.entries:
        if src_k not in seen:
            ordered_resource_keys.append(src_k)
            seen.add(src_k)

    untouched_count = 0
    modified_count = 0
    human_verified_count = 0
    warnings: list[str] = []
    untouched_keys_set: set[str] = set()

    for key in ordered_resource_keys:
        orig_val = target_parsed.entries.get(key)
        entry_info = updated_entries.get(key)

        if entry_info is not None:
            candidate = entry_info["current_target"]
            is_fixed = bool(entry_info.get("is_fixed", False))

            # Safety check: if candidate breaks ICU syntax while original was valid, keep safe or warn
            _, _, cand_icu_errs = extract_icu_structure(candidate)
            if cand_icu_errs and orig_val is not None:
                _, _, orig_icu_errs = extract_icu_structure(orig_val)
                if not orig_icu_errs:
                    warnings.append(
                        f"[{key}] Түзетілген мәтінде ICU синтаксис қатесі бар; бастапқы қауіпсіз мән сақталды."
                    )
                    candidate = orig_val
                    is_fixed = False

            if orig_val is not None and candidate == orig_val and not is_fixed:
                out[key] = orig_val
                untouched_count += 1
                untouched_keys_set.add(key)
            else:
                out[key] = candidate
                if orig_val != candidate:
                    modified_count += 1
                else:
                    untouched_count += 1
                    untouched_keys_set.add(key)
        else:
            out[key] = orig_val if orig_val is not None else source_parsed.entries.get(key, "")
            untouched_count += 1
            untouched_keys_set.add(key)

        # Preserve @metadata from target (or fallback to source @metadata)
        existing_meta: dict[str, Any] | None = None
        if key in target_parsed.metadata:
            existing_meta = dict(target_parsed.metadata[key])
        elif key in source_parsed.metadata:
            existing_meta = dict(source_parsed.metadata[key])

        if entry_info and entry_info.get("reviewed_by_human"):
            human_verified_count += 1
            meta_obj = dict(existing_meta) if existing_meta is not None else {}
            # Valid ARB custom vendor extension properties (`x-*`) fully compatible with Flutter gen-l10n
            meta_obj["x-reviewed-by-human"] = True
            meta_obj["x-qa-status"] = "verified"
            if entry_info.get("reviewer_name"):
                meta_obj["x-reviewed-by"] = entry_info["reviewer_name"]
            if entry_info.get("reviewed_at"):
                meta_obj["x-reviewed-at"] = entry_info["reviewed_at"]
            out[f"@{key}"] = meta_obj
        elif existing_meta is not None:
            out[f"@{key}"] = existing_meta

    validation_errors, icu_warnings = validate_arb_for_gen_l10n(
        out,
        source_parsed.entries,
        preexisting_unmodified_keys=untouched_keys_set,
    )
    warnings.extend(icu_warnings)
    if validation_errors:
        raise ARBValidationError(
            "Экспорт алдындағы gen-l10n валидациясы сәтсіз аяқталды: " + "; ".join(validation_errors[:5])
        )

    formatted_json = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    summary = {
        "locale": out["@@locale"],
        "total_keys": len(ordered_resource_keys),
        "modified_keys": modified_count,
        "untouched_keys": untouched_count,
        "human_verified_keys": human_verified_count,
    }
    return formatted_json, summary, warnings
