"""Poet - poetry assistant. Usage: python main.py [poem.txt]"""

import sys

from poet_tk.app import run

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
