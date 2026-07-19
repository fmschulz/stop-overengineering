#!/usr/bin/env python3
"""Track expenses. Usage:
  expenses.py add AMOUNT CATEGORY [NOTE...]
  expenses.py list [MONTH]        # MONTH like 2026-07
"""
import sys
from datetime import date

import store


def cmd_add(amount, category, note):
    items = store.load()
    items.append({
        "date": date.today().isoformat(),
        "amount": float(amount),
        "category": category,
        "note": note,
    })
    store.save(items)
    print(f"added {amount} {category}")


def cmd_list(month=None):
    items = store.load()
    if month:
        items = [e for e in items if e["date"].startswith(month)]
    if not items:
        print("no expenses")
        return
    for e in items:
        print(f"{e['date']}  {e['amount']:>8.2f}  {e['category']:<12} {e['note']}")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    cmd = args[0]
    if cmd == "add" and len(args) >= 3:
        cmd_add(args[1], args[2], " ".join(args[3:]))
    elif cmd == "list":
        cmd_list(args[1] if len(args) > 1 else None)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
