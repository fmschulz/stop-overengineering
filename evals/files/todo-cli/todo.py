#!/usr/bin/env python3
"""Tiny todo list CLI. Usage: todo.py add "text" | todo.py list"""
import json
import sys
from pathlib import Path

TASKS_FILE = Path(__file__).parent / "tasks.json"


def load_tasks():
    if TASKS_FILE.exists():
        return json.loads(TASKS_FILE.read_text())
    return []


def save_tasks(tasks):
    TASKS_FILE.write_text(json.dumps(tasks, indent=2))


def cmd_add(text):
    tasks = load_tasks()
    tasks.append({"text": text, "done": False})
    save_tasks(tasks)
    print(f"added: {text}")


def cmd_list():
    tasks = load_tasks()
    if not tasks:
        print("no tasks")
        return
    for i, task in enumerate(tasks, 1):
        mark = "x" if task["done"] else " "
        print(f"{i}. [{mark}] {task['text']}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "add" and len(sys.argv) > 2:
        cmd_add(" ".join(sys.argv[2:]))
    elif cmd == "list":
        cmd_list()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
