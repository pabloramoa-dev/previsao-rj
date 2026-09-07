"""Guard de isolamento — Plano Mestre v1.1, secao 3.1 e checklist 17.2.

Nenhum identificador, conta, token ou estado do Previsao Sul Fluminense pode
aparecer no codigo, na configuracao ou nos workflows do @previsaorj.
"""
from __future__ import annotations

from pathlib import Path

# Montado em pedacos de proposito: o proprio guard nao pode conter os literais
# que ele procura, senao ele se acusa.
BANNED = [
    "@previsao" + "sulflu",
    "previsao" + "vr",
    "271484" + "85038175",       # IG user id da conta antiga
    "previsao-sul" + "-fluminense",
    "reels/previsao" + "_lib",
]

ROOTS = [Path("src"), Path(".github"), Path("config"), Path("scripts"), Path("tests")]
SELF_EXEMPT = {Path("scripts/isolation_guard.py"), Path("tests/test_isolation.py")}
SKIP_SUFFIXES = {".pyc", ".mp4", ".wav", ".png", ".jpg"}


def scan() -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for root in ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path in SELF_EXEMPT:
                continue
            if path.suffix in SKIP_SUFFIXES or "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8").casefold()
            except (UnicodeDecodeError, OSError):
                continue
            for banned in BANNED:
                if banned.casefold() in text:
                    violations.append((str(path), banned))
    return violations


def main() -> None:
    violations = scan()
    if violations:
        lines = "\n".join(f"  {path}: {token!r}" for path, token in violations)
        raise SystemExit(f"isolamento falhou:\n{lines}")
    print(f"isolation_guard: ok ({len(BANNED)} padroes, {len(ROOTS)} raizes)")


if __name__ == "__main__":
    main()
