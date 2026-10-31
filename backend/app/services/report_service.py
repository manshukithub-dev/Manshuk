from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import html
import json
from typing import Any

ISSUE_TYPE_LABELS_KK: dict[str, str] = {
    "untranslated": "Аударылмаған жол (untranslated)",
    "same_as_source": "Түпнұсқамен бірдей (same_as_source)",
    "placeholder_mismatch": "Плейсхолдер сәйкессіздігі (placeholder_mismatch)",
    "plural_mismatch": "ICU көпше түр қатесі (plural_mismatch)",
    "glossary_violation": "Глоссарий бұзушылығы (glossary_violation)",
    "length_overflow": "Мәтін тым ұзын (length_overflow)",
    "machine_translation_suspect": "Машиналық аударма күдігі (machine_translation_suspect)",
    "inconsistent_term": "Біркелкі емес термин (inconsistent_term)",
    "suffix_harmony": "Қосымша үндестігі (suffix_harmony)",
    "orthography": "Емле қатесі (orthography)",
    "wrong_language": "Қате тіл (wrong_language)",
    "other_localization_issue": "Басқа локализация қатесі (other)",
}


def format_issue_json_item(issue: Any) -> dict[str, Any]:
    """
    Exact JSON issue object structure required by Section 11:
    {
      "key": "garage_rent_button",
      "issue_type": "length_overflow",
      "severity": "high",
      "source": "Арендовать",
      "target": "Жалға алу үшін басыңыз",
      "evidence": "...",
      "suggestion": "Жалға алу",
      "confidence": 0.95,
      "reviewed_by_human": false
    }
    """
    if isinstance(issue, dict):
        return {
            "key": issue["key"],
            "issue_type": issue["issue_type"],
            "severity": issue["severity"],
            "source": issue["source"],
            "target": issue["target"],
            "evidence": issue["evidence"],
            "suggestion": issue["suggestion"],
            "confidence": round(float(issue["confidence"]), 2),
            "reviewed_by_human": bool(issue.get("reviewed_by_human", False)),
        }
    return {
        "key": issue.key,
        "issue_type": issue.issue_type,
        "severity": issue.severity,
        "source": issue.source,
        "target": issue.target,
        "evidence": issue.evidence,
        "suggestion": getattr(issue, "suggestion", ""),
        "confidence": round(float(issue.confidence), 2),
        "reviewed_by_human": bool(getattr(issue, "reviewed_by_human", False)),
    }


def generate_json_report(issues: list[Any], include_wrapper: bool = False, summary: dict[str, Any] | None = None) -> str:
    items = [format_issue_json_item(i) for i in issues]
    if include_wrapper and summary is not None:
        payload = {"summary": summary, "issues": items}
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return json.dumps(items, ensure_ascii=False, indent=2)


def generate_recommendations(type_counts: Counter[str], unreviewed_count: int) -> list[str]:
    recs: list[str] = []
    if type_counts.get("suffix_harmony", 0) > 0:
        recs.append(
            "Динамикалық плейсхолдерлерден кейінгі ({name}-ға, {name}-ден) тұрақты жалғауларды алып тастап, "
            "сөйлемді көмекші сөз арқылы қайта құрастырыңыз немесе код деңгейінде KazakhSuffixHelper қолданыңыз."
        )
    if type_counts.get("placeholder_mismatch", 0) > 0 or type_counts.get("plural_mismatch", 0) > 0:
        recs.append(
            "Flutter gen-l10n компиляциясы құламауы үшін барлық {name}, {count} плейсхолдерлері мен ICU plural 'other{...}' тармақтарын түзетіңіз."
        )
    if type_counts.get("glossary_violation", 0) > 0:
        recs.append(
            "Ойын глоссарийіндегі бекітілген терминдерді (Grand Coins, отбасы, фракция, варн, мут, фура, ГК) бірізді қолданыңыз."
        )
    if type_counts.get("orthography", 0) > 0:
        recs.append(
            "Қазақтың төл әріптерін (ә, ғ, қ, ң, ө, ұ, ү, һ, і) орыс немесе латын ұқсас таңбаларымен шатастырмай тексеріп шығыңыз."
        )
    if type_counts.get("length_overflow", 0) > 0:
        recs.append(
            "Мобильді интерфейстегі батырмаларда «үшін басыңыз» сияқты артық сөздерді қысқартып, тұйық етістік формасын («Жалға алу», «Сатып алу») қолданыңыз."
        )
    if unreviewed_count > 0:
        recs.append(
            f"Финалдық ARB экспорты алдында қалған {unreviewed_count} жолды қазақтілді локализация маманының тексеруінен (Human Review) өткізіңіз."
        )
    if not recs:
        recs.append("Барлық негізгі локализация талаптары орындалған. Финалдық ARB файлын экспорттауға дайын.")
    return recs


def generate_html_report(
    project_name: str,
    total_strings: int,
    fixed_strings: int,
    human_reviewed_strings: int,
    unreviewed_strings: int,
    kk_score: float,
    uz_score: float | None,
    issues: list[Any],
    is_demo: bool = False,
) -> str:
    items = [format_issue_json_item(i) for i in issues]
    type_counts: Counter[str] = Counter(i["issue_type"] for i in items)
    sev_counts: Counter[str] = Counter(i["severity"] for i in items)
    recommendations = generate_recommendations(type_counts, unreviewed_strings)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    demo_badge = (
        '<span style="background:#f59e0b22;color:#fbbf24;border:1px solid #f59e0b66;padding:4px 10px;border-radius:999px;font-size:12px;margin-left:10px;">DEMO ДЕРЕКТЕР</span>'
        if is_demo
        else ""
    )

    type_rows_html = "".join(
        f"""
        <tr>
          <td>{html.escape(ISSUE_TYPE_LABELS_KK.get(t, t))}</td>
          <td style="text-align:right;font-weight:700;color:#38bdf8;">{cnt}</td>
        </tr>
        """
        for t, cnt in type_counts.most_common()
    ) or '<tr><td colspan="2" style="color:#94a3b8;">Қателер табылған жоқ</td></tr>'

    rec_items_html = "".join(f"<li>{html.escape(r)}</li>" for r in recommendations)

    issue_rows_html = []
    for item in items:
        sev = item["severity"]
        sev_color = "#f43f5e" if sev == "high" else ("#f59e0b" if sev == "medium" else "#38bdf8")
        human_badge = (
            '<span style="color:#34d399;font-weight:600;">Расталған (Иә)</span>'
            if item["reviewed_by_human"]
            else '<span style="color:#94a3b8;">Күтілуде (Жоқ)</span>'
        )
        issue_rows_html.append(
            f"""
            <tr>
              <td style="font-family:monospace;color:#e2e8f0;font-size:12px;">{html.escape(item['key'])}</td>
              <td><span style="color:{sev_color};font-weight:700;text-transform:uppercase;font-size:11px;">{html.escape(sev)}</span></td>
              <td style="font-size:12px;color:#cbd5e1;">{html.escape(item['issue_type'])}</td>
              <td>{html.escape(item['source'])}</td>
              <td style="color:#fda4af;">{html.escape(item['target'])}</td>
              <td style="color:#6ee7b7;">{html.escape(item['suggestion'])}</td>
              <td style="font-size:12px;color:#94a3b8;">{html.escape(item['evidence'])}</td>
              <td style="text-align:center;">{int(item['confidence'] * 100)}%</td>
              <td>{human_badge}</td>
            </tr>
            """
        )

    uz_score_str = f"{uz_score:.1f}%" if uz_score is not None else "—"

    return f"""<!DOCTYPE html>
<html lang="kk">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Qazaq Loc QA — Локализация сапасы есебі</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 32px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #070b14;
      color: #e2e8f0;
      line-height: 1.5;
    }}
    .container {{ max-width: 1280px; margin: 0 auto; }}
    .header {{
      background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
      border: 1px solid #1e293b;
      border-radius: 16px;
      padding: 24px 28px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }}
    h1 {{ margin: 0; font-size: 24px; color: #f8fafc; }}
    .subtitle {{ color: #94a3b8; font-size: 13px; margin-top: 4px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }}
    .card {{
      background: #0f172a;
      border: 1px solid #1e293b;
      border-radius: 14px;
      padding: 16px 18px;
    }}
    .card-label {{ font-size: 12px; color: #94a3b8; }}
    .card-value {{ font-size: 26px; font-weight: 800; margin-top: 6px; color: #f8fafc; }}
    .two-col {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      margin-bottom: 24px;
    }}
    @media (max-width: 800px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #1e293b;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #111827; color: #94a3b8; font-weight: 600; }}
    .section-title {{ font-size: 16px; font-weight: 700; margin: 0 0 12px 0; color: #38bdf8; }}
    ul.recs {{ margin: 0; padding-left: 20px; color: #cbd5e1; }}
    ul.recs li {{ margin-bottom: 8px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1>QAZAQ LOC QA — Сапа есебі {demo_badge}</h1>
        <div class="subtitle">Жоба: {html.escape(project_name)} • Қалыптастырылған уақыты: {generated_at}</div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:12px;color:#94a3b8;">Сапа көрсеткіші (KK / UZ)</div>
        <div style="font-size:22px;font-weight:800;color:#34d399;">{kk_score:.1f}% / {uz_score_str}</div>
      </div>
    </div>

    <div class="grid">
      <div class="card"><div class="card-label">Жалпы жол саны</div><div class="card-value">{total_strings}</div></div>
      <div class="card"><div class="card-label">Табылған қателер</div><div class="card-value" style="color:#f43f5e;">{len(items)}</div></div>
      <div class="card"><div class="card-label">High / Medium / Low</div><div class="card-value" style="font-size:20px;"><span style="color:#f43f5e;">{sev_counts.get('high', 0)}</span> / <span style="color:#f59e0b;">{sev_counts.get('medium', 0)}</span> / <span style="color:#38bdf8;">{sev_counts.get('low', 0)}</span></div></div>
      <div class="card"><div class="card-label">Түзетілген жолдар</div><div class="card-value" style="color:#a78bfa;">{fixed_strings}</div></div>
      <div class="card"><div class="card-label">Адам тексерген жолдар</div><div class="card-value" style="color:#34d399;">{human_reviewed_strings}</div></div>
      <div class="card"><div class="card-label">Тексерілмеген жолдар</div><div class="card-value" style="color:#fbbf24;">{unreviewed_strings}</div></div>
    </div>

    <div class="two-col">
      <div class="card">
        <div class="section-title">Қате түрлері бойынша статистика</div>
        <table>
          <thead><tr><th>Қате түрі</th><th style="text-align:right;">Саны</th></tr></thead>
          <tbody>{type_rows_html}</tbody>
        </table>
      </div>
      <div class="card">
        <div class="section-title">Сапаны жақсарту бойынша ұсыныстар</div>
        <ul class="recs">{rec_items_html}</ul>
      </div>
    </div>

    <div class="card" style="overflow-x:auto;">
      <div class="section-title">Барлық анықталған мәселелер тізімі ({len(items)})</div>
      <table>
        <thead>
          <tr>
            <th>Key</th>
            <th>Severity</th>
            <th>Қате түрі</th>
            <th>Source (RU)</th>
            <th>Target</th>
            <th>Suggestion</th>
            <th>Evidence</th>
            <th>Conf.</th>
            <th>Human Review</th>
          </tr>
        </thead>
        <tbody>
          {''.join(issue_rows_html) if issue_rows_html else '<tr><td colspan="9" style="text-align:center;color:#34d399;">Қателер табылған жоқ!</td></tr>'}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>
"""
