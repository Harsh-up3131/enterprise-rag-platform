"""CLI: print suggested chunk texts for eval cases missing ground-truth.

Usage:
  python scripts/suggest_eval_chunks.py [path_to_eval_json]

If no path is provided, the bundled sample_eval_set.json is used.
"""
import json
import sys
from app.database import SessionLocal
from app.services.evaluation.runner import load_eval_set, get_suggested_chunks_for_cases


def main():
    db = SessionLocal()
    path = sys.argv[1] if len(sys.argv) > 1 else None
    cases = load_eval_set(path) if path else load_eval_set()
    from app.models import Organization
    org_obj = db.query(Organization).first()
    if not org_obj:
        print("No organization found in DB")
        return
    suggestions = get_suggested_chunks_for_cases(db, org_obj.id, cases)
    print(json.dumps(suggestions, indent=2))


if __name__ == "__main__":
    main()
