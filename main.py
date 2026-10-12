"""Payment Reminder Bot."""
import argparse
import csv
import json
from datetime import date
from pathlib import Path

import llm


def stage_for(days_overdue: int, stages: list):
    for s in stages:
        if s["min_days"] <= days_overdue <= s["max_days"]:
            return s
    return None


def draft(inv: dict, stage: dict, days: int) -> str:
    base = stage["template"].format(client=inv["client"], invoice=inv["invoice"],
                                    amount=f"{float(inv['amount']):,.0f}",
                                    due=inv["due_date"], days=abs(days))
    better = llm.complete(f"Rewrite this payment reminder for {inv['channel']} so it sounds "
                          f"natural and keeps the same firmness ({stage['name']}). Keep all "
                          f"figures exactly:\n{base}")
    return (better or base).strip()


def run(rows, stages, today):
    outbox, escalations, skipped = {"whatsapp": [], "email": []}, [], []
    for inv in rows:
        if inv["status"] in ("paid", "disputed"):
            skipped.append((inv["invoice"], inv["status"]))
            continue
        days = (today - date.fromisoformat(inv["due_date"])).days
        st = stage_for(days, stages)
        if st is None:
            skipped.append((inv["invoice"], "not due yet"))
            continue
        msg = {"invoice": inv["invoice"], "to": inv["contact"], "stage": st["name"],
               "days_overdue": days, "message": draft(inv, st, days)}
        outbox[inv["channel"]].append(msg)
        if st.get("escalate"):
            escalations.append(msg)
    return outbox, escalations, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="sample_invoices.csv")
    ap.add_argument("--today", default="2026-10-09")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.input, encoding="utf-8")))
    stages = json.loads(Path("stages.json").read_text())
    outbox, esc, skipped = run(rows, stages, date.fromisoformat(a.today))
    Path("output").mkdir(exist_ok=True)
    for ch, msgs in outbox.items():
        Path(f"output/outbox_{ch}.json").write_text(json.dumps(msgs, indent=2))
        for m in msgs:
            print(f"[{ch.upper():<8}] {m['invoice']} {m['stage']:<9} ({m['days_overdue']:+d} days) -> {m['to']}")
            print(f"           {m['message']}\n")
    print(f"Escalate to account manager: {[m['invoice'] for m in esc]}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()
