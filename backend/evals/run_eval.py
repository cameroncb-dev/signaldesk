"""Measure how often the triage agent routes incidents to the correct team.

Usage (from backend/):  python -m evals.run_eval [--min-accuracy 0.8]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR.parent))

_db_file = Path(tempfile.gettempdir()) / "signaldesk_eval.db"
_db_file.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file.as_posix()}"

from app.agents.orchestrator import run_triage  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import AgentRun, Ticket  # noqa: E402
from app.seed import seed_if_empty  # noqa: E402


def run(cases_path: Path) -> list[dict]:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_if_empty(db)
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    results = []
    try:
        for index, case in enumerate(cases, start=1):
            ticket = Ticket(
                sys_id=str(uuid4()),
                number=f"EVAL{index:04d}",
                short_description=case["short_description"],
                description=case["description"],
                urgency=case.get("urgency", 2),
                impact=case.get("impact", 2),
                priority=3,
                state="new",
                category="inquiry",
                cmdb_ci=case.get("cmdb_ci", ""),
                caller="eval",
            )
            db.add(ticket)
            db.commit()
            db.refresh(ticket)

            recommendation = run_triage(db, ticket)
            predicted = recommendation.recommendation.assignment_group
            results.append(
                {
                    "case": index,
                    "title": case["short_description"],
                    "expected": case["expected_group"],
                    "predicted": predicted,
                    "correct": predicted == case["expected_group"],
                    "model": recommendation.model,
                }
            )

            db.query(AgentRun).filter(AgentRun.ticket_id == ticket.id).delete()
            db.delete(ticket)
            db.commit()
    finally:
        db.close()
        engine.dispose()
        _db_file.unlink(missing_ok=True)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=EVAL_DIR / "incidents.json")
    parser.add_argument("--min-accuracy", type=float, default=0.0)
    args = parser.parse_args()

    results = run(args.cases)
    correct = sum(row["correct"] for row in results)
    accuracy = correct / len(results)

    for row in results:
        mark = "PASS" if row["correct"] else "FAIL"
        line = f"{mark}  #{row['case']:<2} {row['title'][:52]:<52}  expected={row['expected']}"
        if not row["correct"]:
            line += f"  got={row['predicted']}"
        print(line)

    by_group: dict[str, list[bool]] = {}
    for row in results:
        by_group.setdefault(row["expected"], []).append(row["correct"])
    print()
    for group, outcomes in sorted(by_group.items()):
        print(f"  {group:<24} {sum(outcomes)}/{len(outcomes)}")
    print(f"\nRouting accuracy: {correct}/{len(results)} = {accuracy:.0%} (model: {results[0]['model']})")

    return 0 if accuracy >= args.min_accuracy else 1


if __name__ == "__main__":
    raise SystemExit(main())
