"""
Qazaq Loc QA — Production & Post-Deployment Verification Suite.

Usage (Local Production Simulation):
  python scripts/verify_deployment.py --api-url http://127.0.0.1:8000 --frontend-url http://127.0.0.1:4173

Usage (Live Cloud Verification after Vercel + Render Deploy):
  python scripts/verify_deployment.py --api-url https://qazaq-locqa-api.onrender.com --frontend-url https://qazaq-loc-qa.vercel.app
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import uuid
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = PROJECT_ROOT / "data" / "demo"
GLOSSARY_CSV = PROJECT_ROOT / "glossary" / "glossary.csv"


def verify_deployment(api_url: str, frontend_url: str | None, origin: str) -> None:
    api_base = api_url.rstrip("/")
    ws_id = f"deploy-verify-{uuid.uuid4().hex[:10]}"
    headers = {
        "X-Workspace-Id": ws_id,
        "Origin": origin,
        "bypass-tunnel-reminder": "true",
    }

    uploaded_file_ids: list[int] = []
    created_run_ids: list[int] = []
    created_glossary_id: int | None = None

    print(f"=== QAZAQ LOC QA DEPLOYMENT VERIFICATION ===")
    print(f"API Base URL : {api_base}")
    if frontend_url:
        print(f"Frontend URL : {frontend_url.rstrip('/')}")
    print(f"CORS Origin  : {origin}")

    # 1. Verify Frontend Bundle (if provided)
    if frontend_url:
        with httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={"bypass-tunnel-reminder": "true"},
        ) as fe_client:
            fe_resp = fe_client.get(frontend_url.rstrip("/"))
            assert fe_resp.status_code == 200, f"Frontend returned {fe_resp.status_code}"
            assert "QAZAQ LOC QA" in fe_resp.text.upper(), "Frontend HTML title mismatch"
            print("[OK] 1. Frontend SPA bundle reachable and serving QAZAQ LOC QA HTML")

    with httpx.Client(
        base_url=api_base,
        timeout=45.0,
        follow_redirects=True,
        headers={"bypass-tunnel-reminder": "true"},
    ) as client:
        try:
            # 2. Verify Root & Healthcheck + Database Engine
            r_root = client.get("/")
            assert r_root.status_code == 200
            r_health = client.get("/api/health")
            assert r_health.status_code == 200
            h_json = r_health.json()
            assert h_json["status"] == "ok"
            print(
                f"[OK] 2. Backend Healthcheck OK (database={h_json.get('database')}, env={h_json.get('environment')})"
            )

            # 3. Verify CORS Preflight & Exposed Headers
            r_cors = client.options(
                "/api/dashboard",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "X-Workspace-Id,Content-Type",
                },
            )
            assert r_cors.status_code in (200, 204), f"Preflight status {r_cors.status_code}"
            allow_origin = r_cors.headers.get("access-control-allow-origin")
            is_same_origin = bool(frontend_url and frontend_url.rstrip("/") == api_base)
            assert is_same_origin or allow_origin in (origin, "*"), f"CORS blocked origin {origin}: got {allow_origin}"
            print(f"[OK] 3. CORS / Same-Origin Proxy verified (Origin={allow_origin or origin})")

            # 4. Verify Dashboard clean state
            r_d0 = client.get("/api/dashboard", headers=headers)
            assert r_d0.status_code == 200 and r_d0.json()["has_runs"] is False
            print("[OK] 4. Dashboard live DB query verified (clean workspace isolation)")

            # 5. Verify File Upload & ARB Validation
            r_bad = client.post(
                "/api/files/upload",
                headers=headers,
                data={"role": "ru"},
                files={"file": ("invalid.arb", b"{broken_json", "application/json")},
            )
            assert r_bad.status_code == 400

            fmap: dict[str, int] = {}
            for role, fname in [
                ("ru", "intl_ru.arb"),
                ("kk", "intl_kk.arb"),
                ("uz", "intl_uz.arb"),
                ("en", "intl_en.arb"),
            ]:
                r_up = client.post(
                    "/api/files/upload",
                    headers=headers,
                    data={"role": role},
                    files={"file": (fname, (DEMO_DIR / fname).read_bytes(), "application/json")},
                )
                assert r_up.status_code == 200, r_up.text
                fmap[role] = r_up.json()["id"]
                uploaded_file_ids.append(fmap[role])

            r_gl_up = client.post(
                "/api/files/upload",
                headers=headers,
                data={"role": "glossary"},
                files={"file": ("glossary.csv", GLOSSARY_CSV.read_bytes(), "text/csv")},
            )
            assert r_gl_up.status_code == 200
            gl_fid = r_gl_up.json()["id"]
            uploaded_file_ids.append(gl_fid)
            print("[OK] 5. File Upload & ARB validation verified (5 files persisted in DB)")

            # 6. Verify QA Check Execution & Dashboard Aggregation
            r_run = client.post(
                "/api/checks/run",
                headers=headers,
                json={
                    "name": "Production Smoke Verification",
                    "ru_file_id": fmap["ru"],
                    "kk_file_id": fmap["kk"],
                    "uz_file_id": fmap["uz"],
                    "en_file_id": fmap["en"],
                    "glossary_file_id": gl_fid,
                    "use_llm": False,
                },
            )
            assert r_run.status_code == 200, r_run.text
            run_data = r_run.json()
            run_id = run_data["id"]
            created_run_ids.append(run_id)
            assert run_data["total_issues"] >= 10

            r_d1 = client.get("/api/dashboard", headers=headers)
            assert r_d1.status_code == 200 and r_d1.json()["has_runs"] is True
            print(
                f"[OK] 6. QA Engine & Dashboard verified (checked={run_data['checked_strings']}, issues={run_data['total_issues']})"
            )

            # 7. Verify Issues Analysis, Kazakh Dynamic Suffix Guard, & Human Review
            issues = client.get(f"/api/issues?run_id={run_id}&page=1&page_size=100", headers=headers).json()["items"]
            unsafe_suffix = [i for i in issues if i["issue_type"] == "suffix_harmony" and not i["auto_fix_safe"]]
            assert len(unsafe_suffix) >= 1
            r_blk = client.post(
                f"/api/issues/{unsafe_suffix[0]['id']}/action",
                headers=headers,
                json={"action": "auto_apply"},
            )
            assert r_blk.status_code == 400

            r_batch = client.post(f"/api/issues/batch-auto-fix?run_id={run_id}", headers=headers)
            assert r_batch.status_code == 200 and r_batch.json()["reviewed_by_human"] is False

            r_hum = client.post(
                f"/api/issues/{unsafe_suffix[0]['id']}/action",
                headers=headers,
                json={
                    "action": "manual_edit",
                    "new_target": "Жүлде ойыншыға берілді: {name}",
                    "reviewer_name": "QA Specialist",
                },
            )
            assert r_hum.status_code == 200 and r_hum.json()["reviewed_by_human"] is True
            print("[OK] 7. Issues Analysis, Suffix Harmony safety guard, and Human Review verified")

            # 8. Verify CAT Editor, Latin Transliteration, Glossary, & ARB/JSON/HTML Exports
            r_entries = client.get(f"/api/entries?run_id={run_id}&lang=kk", headers=headers)
            assert r_entries.status_code == 200 and len(r_entries.json()["items"]) > 0

            r_tr = client.post("/api/transliterate", headers=headers, json={"text": "Жалға алу"})
            assert r_tr.status_code == 200 and len(r_tr.json()["latin_text"]) > 0

            r_gl = client.get("/api/glossary", headers=headers)
            assert r_gl.status_code == 200 and len(r_gl.json()) >= 10

            r_json = client.get(f"/api/reports/{run_id}/json", headers=headers)
            assert r_json.status_code == 200 and isinstance(json.loads(r_json.text), list)

            r_html = client.get(f"/api/reports/{run_id}/html?download=false", headers=headers)
            assert r_html.status_code == 200 and "QAZAQ LOC QA" in r_html.text.upper()

            r_arb = client.get(f"/api/reports/{run_id}/export-arb?lang=kk", headers=headers)
            assert r_arb.status_code == 200
            assert "content-disposition" in {k.lower() for k in r_arb.headers.keys()}
            arb_obj = json.loads(r_arb.text)
            assert arb_obj["@@locale"] == "kk"
            print("[OK] 8. CAT Editor, Glossary, JSON/HTML Reports, and Flutter gen-l10n ARB Export verified")

        finally:
            if created_glossary_id is not None:
                client.delete(f"/api/glossary/{created_glossary_id}", headers=headers)
            for rid in created_run_ids:
                client.delete(f"/api/checks/{rid}", headers=headers)
            for fid in uploaded_file_ids:
                client.delete(f"/api/files/{fid}", headers=headers)
            print("[OK] Cleanup completed — temporary verification data removed.")

    print("=== ALL PRODUCTION CHECKS PASSED SUCCESSFULLY ===")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Qazaq Loc QA deployment end-to-end")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000", help="Backend API base URL")
    parser.add_argument("--frontend-url", default=None, help="Optional Frontend URL (Vercel / Vite preview)")
    parser.add_argument(
        "--origin",
        default="https://qazaq-loc-qa.vercel.app",
        help="Simulated Origin header for CORS verification",
    )
    args = parser.parse_args()
    verify_deployment(api_url=args.api_url, frontend_url=args.frontend_url, origin=args.origin)
    return 0


if __name__ == "__main__":
    sys.exit(main())
