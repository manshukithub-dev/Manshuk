from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Ensure project root is importable when executed directly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.arb_parser import ARBValidationError, export_fixed_arb, parse_arb_content
from backend.app.services.glossary_service import INITIAL_GLOSSARY_TERMS, parse_glossary_csv
from backend.app.services.kazakh_nlp import transliterate_kk_to_latin
from backend.app.services.qa_engine import compute_quality_score, run_qa_checks
from backend.app.services.report_service import generate_html_report, generate_json_report


def _detect_lang(target_path: Path, parsed_locale: str | None, explicit_lang: str | None) -> str:
    if explicit_lang:
        return explicit_lang.strip().lower()
    if parsed_locale and parsed_locale.lower().startswith("uz"):
        return "uz"
    if "uz" in target_path.stem.lower():
        return "uz"
    return "kk"


def cmd_check(args: argparse.Namespace) -> int:
    src_path = Path(args.source)
    tgt_path = Path(args.target)

    if not src_path.exists():
        print(f"[ҚАТЕ] Түпнұсқа файл табылмады: {src_path}", file=sys.stderr)
        return 2
    if not tgt_path.exists():
        print(f"[ҚАТЕ] Аударма файлы табылмады: {tgt_path}", file=sys.stderr)
        return 2

    try:
        src_raw = src_path.read_text(encoding="utf-8")
        tgt_raw = tgt_path.read_text(encoding="utf-8")
        src_parsed = parse_arb_content(src_raw, src_path.name)
        tgt_parsed = parse_arb_content(tgt_raw, tgt_path.name)
    except ARBValidationError as exc:
        print(f"[ARB ҚАТЕСІ] {exc}", file=sys.stderr)
        return 2

    lang = _detect_lang(tgt_path, tgt_parsed.locale, args.lang)

    glossary_terms = list(INITIAL_GLOSSARY_TERMS)
    if args.glossary:
        gl_path = Path(args.glossary)
        if not gl_path.exists():
            print(f"[ҚАТЕ] Глоссарий файлы табылмады: {gl_path}", file=sys.stderr)
            return 2
        glossary_terms = parse_glossary_csv(gl_path.read_text(encoding="utf-8"))

    issues = run_qa_checks(
        source_entries=src_parsed.entries,
        target_entries=tgt_parsed.entries,
        lang=lang,
        glossary=glossary_terms,
    )
    score = compute_quality_score(len(src_parsed.entries), issues)
    high_cnt = sum(1 for i in issues if i.severity == "high")

    # Apply safe automatic fixes ONLY when `--fixed-arb` is requested (keeps reviewed_by_human=False)
    updates_map: dict[str, dict] = {}
    fixed_cnt = 0
    for key in src_parsed.entries:
        orig_val = tgt_parsed.entries.get(key, "")
        updates_map[key] = {
            "current_target": orig_val,
            "is_fixed": False,
            "reviewed_by_human": False,
            "reviewer_name": None,
            "reviewed_at": None,
        }

    if args.fixed_arb:
        for iss in issues:
            if iss.auto_fix_safe and iss.suggestion and iss.key in updates_map:
                if not updates_map[iss.key]["is_fixed"]:
                    updates_map[iss.key]["current_target"] = iss.suggestion
                    updates_map[iss.key]["is_fixed"] = True
                    fixed_cnt += 1

        fixed_json, summary, _warnings = export_fixed_arb(
            original_target_raw=tgt_raw,
            source_raw=src_raw,
            updated_entries=updates_map,
            target_locale=lang,
        )
        out_arb_path = Path(args.fixed_arb)
        out_arb_path.parent.mkdir(parents=True, exist_ok=True)
        out_arb_path.write_text(fixed_json, encoding="utf-8")
        print(f"[OK] Түзетілген ARB сақталды: {out_arb_path} (өзгертілген жолдар: {summary['modified_keys']})")

    if args.out:
        out_json_path = Path(args.out)
        out_json_path.parent.mkdir(parents=True, exist_ok=True)
        json_report = generate_json_report(issues, include_wrapper=False)
        out_json_path.write_text(json_report, encoding="utf-8")
        print(f"[OK] JSON есебі сақталды: {out_json_path}")

    if args.html:
        out_html_path = Path(args.html)
        out_html_path.parent.mkdir(parents=True, exist_ok=True)
        html_report = generate_html_report(
            project_name=f"{src_path.name} → {tgt_path.name}",
            total_strings=len(src_parsed.entries),
            fixed_strings=fixed_cnt,
            human_reviewed_strings=0,
            unreviewed_strings=len(src_parsed.entries),
            kk_score=score if lang == "kk" else 100.0,
            uz_score=score if lang == "uz" else None,
            issues=issues,
            is_demo=False,
        )
        out_html_path.write_text(html_report, encoding="utf-8")
        print(f"[OK] HTML есебі сақталды: {out_html_path}")

    print(
        f"[QAZAQ LOC QA] Тіл={lang.upper()} | Жолдар={len(src_parsed.entries)} | "
        f"Қателер={len(issues)} (High={high_cnt}) | Сапа={score:.1f}%"
    )

    if args.fail_on_high and high_cnt > 0:
        return 1
    return 0


def cmd_transliterate(args: argparse.Namespace) -> int:
    latin = transliterate_kk_to_latin(args.text)
    print(latin)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="locqa",
        description="Qazaq Loc QA — Мобильді ойындардың қазақша және өзбекше ARB локализациясын тексеру CLI құралы",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check_p = sub.add_parser("check", help="ARB локализация файлдарын тексеру және есеп шығару")
    check_p.add_argument("--source", required=True, help="Түпнұсқа ARB файлы (мысалы: intl_ru.arb)")
    check_p.add_argument("--target", required=True, help="Мақсатты ARB файлы (мысалы: intl_kk.arb немесе intl_uz.arb)")
    check_p.add_argument("--lang", choices=["kk", "uz"], default=None, help="Мақсатты тіл коды (kk немесе uz)")
    check_p.add_argument("--glossary", default=None, help="Глоссарий CSV файлы (мысалы: glossary.csv)")
    check_p.add_argument("--out", default=None, help="JSON есеп шығару жолы (мысалы: report.json)")
    check_p.add_argument("--html", default=None, help="HTML есеп шығару жолы (мысалы: report.html)")
    check_p.add_argument("--fixed-arb", default=None, help="Түзетілген ARB шығару жолы (мысалы: intl_kk_fixed.arb)")
    check_p.add_argument("--fail-on-high", action="store_true", help="High деңгейлі қате табылса exit code 1 қайтару")
    check_p.set_defaults(func=cmd_check)

    tr_p = sub.add_parser("transliterate", help="Қазақша кирилл мәтінін ресми латын әліпбиіне аудару")
    tr_p.add_argument("text", help="Кирилл мәтіні")
    tr_p.set_defaults(func=cmd_transliterate)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Ensure UTF-8 stdout on Windows consoles
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
