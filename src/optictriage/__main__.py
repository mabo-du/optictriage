"""__main__.py — Package execution entry point.
exports: N/A
used_by: optictriage CLI entrypoint
rules:
Simply proxy to app.main()
"""

from optictriage.app import main

if __name__ == "__main__":
    main()
