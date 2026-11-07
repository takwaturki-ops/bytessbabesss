"""Run every evaluation scenario + dataset-level metrics and write reports/eval_report.{md,json}.

Usage:  python -m evaluation.run_eval            (uses LLM_MODE from .env, default mock)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents import AGENTS  # noqa: E402
from core import data  # noqa: E402
from core.llm_client import LLMClient, ScriptedLLMClient, get_default_client  # noqa: E402
from evaluation.checks import run_checks  # noqa: E402
from evaluation.reference_calc import reference_metrics  # noqa: E402
from evaluation.scenarios import all_scenarios  # noqa: E402

REPORTS = ROOT / "reports"


def _agent_for(key: str, scenario: dict, default_llm: LLMClient):
    if "llm_draft" in scenario:
        return AGENTS[key](llm=ScriptedLLMClient(draft=scenario["llm_draft"]))
    if scenario.get("llm_fail"):
        return AGENTS[key](llm=ScriptedLLMClient(fail=True))
    return AGENTS[key](llm=default_llm)


def run_scenarios(llm: LLMClient | None = None) -> dict[str, list[dict]]:
    llm = llm or get_default_client()
    results: dict[str, list[dict]] = {}
    for key, scenarios in all_scenarios().items():
        rows = []
        for sc in scenarios:
            resp = _agent_for(key, sc, llm).run(sc["input"]).model_dump()
            checks = run_checks(resp, sc["checks"])
            rows.append({"id": sc["id"], "category": sc["category"], "description": sc["description"],
                         "mode": resp["meta"]["mode"], "passed": all(c["passed"] for c in checks), "checks": checks})
        results[key] = rows
    return results


# ----------------------------------------------------------------------------- dataset-level metrics
def dataset_metrics(llm: LLMClient | None = None, split: str = "eval") -> dict:
    llm = llm or get_default_client()
    out: dict = {}

    # Fraud: every scenario (dev+eval) - accuracy, false positives / negatives.
    fraud = AGENTS["fraud"](llm=llm)
    rows = data.split_records("fraud_scenarios", "all")
    tp = fp = tn = fn = exact = flag_ok = 0
    mismatches = []
    for r in rows:
        res = fraud.run({"event": r["event"], "history": r["history"], "customer_context": r["customer_context"],
                         "explain": False}).data
        exp_flag, got_flag = r["expected_action"] != "allow", res.action != "allow"
        tp += exp_flag and got_flag; tn += (not exp_flag) and (not got_flag)
        fp += (not exp_flag) and got_flag; fn += exp_flag and (not got_flag)
        exact += res.action == r["expected_action"]
        flag_ok += set(r["expected_flags"]) <= set(res.flags)
        if res.action != r["expected_action"]:
            mismatches.append({"id": r["scenario_id"], "type": r["scenario_type"], "expected": r["expected_action"],
                               "got": res.action, "flags": res.flags})
    n = len(rows)
    out["fraud"] = {"n": n, "action_accuracy": round(exact / n, 4), "expected_flags_found": round(flag_ok / n, 4),
                    "false_positive_rate": round(fp / (fp + tn), 4) if fp + tn else 0.0,
                    "false_negative_rate": round(fn / (fn + tp), 4) if fn + tp else 0.0,
                    "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn}, "mismatches": mismatches}

    # Payment: every eval-split transaction.
    pay = AGENTS["payment"](llm=llm)
    txns = data.split_records("transactions", split)
    correct = unsafe = 0
    for t in txns:
        res = pay.run({**t, "explain": False}).data
        correct += res.final_status == t["status"]
        unsafe += res.payment_confirmed and t["status"] != "success"
    out["payment"] = {"n": len(txns), "status_accuracy": round(correct / len(txns), 4),
                      "unsafe_confirmations": unsafe}

    # Customer intelligence + sales intent on held-out conversations.
    intel, sales = AGENTS["customer_intel"](llm=llm), AGENTS["sales"](llm=llm)
    convs = data.split_records("conversations", split)
    i_int = i_sent = i_obj = s_int = s_reco = s_reco_n = 0
    mae = 0.0
    confusion = Counter()
    for c in convs:
        lab = c["labels"]
        ins = intel.run({"turns": c["turns"], "conversation_id": c["conversation_id"]}).data
        i_int += ins.primary_intent == lab["intent"]
        i_sent += ins.sentiment == lab["sentiment"]
        i_obj += set(ins.objections) == set(lab["objections"])
        mae += abs(ins.interest_score - lab["interest_score"])
        sr = sales.run({"customer_message": c["turns"][0]["text"], "customer_id": c["customer_id"]}).data
        s_int += sr.detected_intent == lab["intent"]
        confusion[(lab["intent"], sr.detected_intent)] += 1
        if lab["mentioned_course_id"] and lab["intent"] not in ("payment_issue", "support_request", "not_interested"):
            s_reco_n += 1
            s_reco += lab["mentioned_course_id"] in [r.course_id for r in sr.recommended_courses]
    n = len(convs)
    out["customer_intel"] = {"n": n, "intent_accuracy": round(i_int / n, 4), "sentiment_accuracy": round(i_sent / n, 4),
                             "objection_exact_match": round(i_obj / n, 4), "interest_mae": round(mae / n, 2)}
    out["sales"] = {"n": n, "intent_accuracy": round(s_int / n, 4),
                    "recommendation_hit_rate": round(s_reco / s_reco_n, 4) if s_reco_n else None,
                    "intent_errors": {f"{a}->{b}": v for (a, b), v in confusion.items() if a != b}}

    # Financial: pandas engine vs independent pure-Python reference on every split.
    fin = AGENTS["financial"](llm=llm)
    fin_rows = []
    for sp in ("dev", "eval", "all"):
        m = fin.run({"split": sp, "explain": False}).data.metrics.model_dump()
        ref = reference_metrics(data.split_records("orders", sp), data.split_records("transactions", sp))
        diffs = {k: (m[k], v) for k, v in ref.items() if abs(float(m[k]) - float(v)) > 0.011}
        fin_rows.append({"split": sp, "fields_checked": len(ref), "mismatches": diffs})
    out["financial"] = {"cross_checks": fin_rows,
                        "all_match": all(not r["mismatches"] for r in fin_rows)}
    return out


# ----------------------------------------------------------------------------- report
def write_report(results: dict, metrics: dict, mode: str, model: str | None) -> tuple[Path, Path]:
    REPORTS.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = sum(len(v) for v in results.values())
    passed = sum(r["passed"] for v in results.values() for r in v)
    payload = {"generated_at": ts, "llm_mode": mode, "model": model, "data": "SIMULATED",
               "summary": {"scenarios": total, "passed": passed, "failed": total - passed},
               "scenario_results": results, "dataset_metrics": metrics}
    jpath = REPORTS / "eval_report.json"
    jpath.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    banner = ("MOCK MODE - no LLM was called; text fields are deterministic templates labelled [MOCK]. "
              "Scores measure the deterministic rules + heuristic baseline, not Claude."
              if mode == "mock" else f"LIVE MODE - real Claude calls with model `{model}`.")
    lines = [f"# 9antra AI Agents - Evaluation Report", "", f"Generated: {ts}  ", f"**{banner}**  ",
             "All data is SIMULATED.", "", f"## Summary: {passed}/{total} scenarios passed", "",
             "| Agent | Passed | Total |", "|---|---|---|"]
    for k, v in results.items():
        lines.append(f"| {k} | {sum(r['passed'] for r in v)} | {len(v)} |")
    lines += ["", "## Dataset-level metrics", "", "```json", json.dumps(metrics, indent=2, default=str), "```", ""]
    for k, v in results.items():
        lines += [f"## {k}", "", "| ID | Category | Scenario | Mode | Expected | Actual | Result |", "|---|---|---|---|---|---|---|"]
        for r in v:
            exp = "; ".join(f"{c['path']} {c['op']} {json.dumps(c['expected'], ensure_ascii=False)}" for c in r["checks"])
            act = "; ".join(f"{json.dumps(c['actual'], ensure_ascii=False, default=str)[:60]}" for c in r["checks"])
            lines.append(f"| {r['id']} | {r['category']} | {r['description']} | {r['mode']} | "
                         f"{exp.replace('|', '/')} | {act.replace('|', '/')} | {'PASS' if r['passed'] else '**FAIL**'} |")
        lines.append("")
    mpath = REPORTS / "eval_report.md"
    mpath.write_text("\n".join(lines), encoding="utf-8")
    return mpath, jpath


def main() -> int:
    llm = get_default_client()
    results = run_scenarios(llm)
    metrics = dataset_metrics(llm)
    mpath, jpath = write_report(results, metrics, llm.mode, llm.model)
    total = sum(len(v) for v in results.values())
    passed = sum(r["passed"] for v in results.values() for r in v)
    print(f"LLM mode: {llm.mode}" + (f" ({llm.model})" if llm.model else " (no API calls)"))
    for k, v in results.items():
        fails = [r["id"] for r in v if not r["passed"]]
        print(f"  {k:15s} {sum(r['passed'] for r in v):2d}/{len(v):2d} passed" + (f"  FAILED: {fails}" if fails else ""))
    print(f"TOTAL {passed}/{total} scenarios passed")
    print("Dataset metrics:", json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("mismatches", "cross_checks",
                                                                                         "intent_errors", "confusion")}
                                          for k, v in metrics.items()}))
    print(f"Report: {mpath.relative_to(ROOT)} and {jpath.relative_to(ROOT)}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
