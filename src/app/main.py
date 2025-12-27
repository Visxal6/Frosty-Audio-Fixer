import os
import sys
from PySide6.QtWidgets import QApplication
from app.window import MainWindow


def _patch_path() -> None:
    extra = ["/opt/homebrew/bin", "/usr/local/bin"]
    cur = os.environ.get("PATH", "")
    parts = [p for p in extra if p and p not in cur.split(":")]
    os.environ["PATH"] = ":".join(parts + [cur]) if cur else ":".join(parts)


def main() -> int:
    _patch_path()
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())