
# Print DB info (path, exists, count). Usage: python -m tools.print_db_info
from __future__ import annotations
from data.prompt_repository import PromptRepository
from pathlib import Path

def main():
    repo = PromptRepository()
    p = Path(repo.db_path)
    print(f"DB path: {repo.db_path}")
    print(f"Exists: {p.exists()}  Size: {p.stat().st_size if p.exists() else 0} bytes")
    try:
        print(f"Count: {repo.count()} items")
    except Exception as e:
        print(f"Count failed: {e}")

if __name__ == '__main__':
    main()
