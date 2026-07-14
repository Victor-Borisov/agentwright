#!/usr/bin/env python3
"""Scorecard integrity seal — tamper-EVIDENCE, not proof.

`stamp` writes scorecard.integrity = sha256(install_salt + canonical scorecard
without the integrity field). `check` recomputes and compares. The journal is
deliberately NOT part of the seal — it grows with every session, and the seal
must stay valid between score runs.

What this catches: a scorecard edited outside Agentwright (text editor, script)
— the seal no longer matches and the show skill says so.
What this does NOT do: prove anything to a third party. The salt lives on the
same machine as the scorecard, and this script is open source — a determined
user can re-stamp. Any real cross-machine verification needs a signature by a
key the user does not hold, which a local plugin cannot provide by definition.

Usage: card_integrity.py stamp|check
Exit codes for check: 0 sealed+matching · 3 no scorecard · 4 no seal · 5 mismatch
"""
import hashlib
import json
import os
import sys

DATA_DIR = os.path.join(os.path.expanduser("~"), ".claude", "agentwright")
CARD = os.path.join(DATA_DIR, "scorecard.json")
SALT_FILE = os.path.join(DATA_DIR, "state", "install-salt")


def salt():
    try:
        with open(SALT_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        s = os.urandom(16).hex()
        os.makedirs(os.path.dirname(SALT_FILE), exist_ok=True)
        with open(SALT_FILE, "w", encoding="utf-8") as f:
            f.write(s)
        return s


def seal(card):
    body = {k: v for k, v in card.items() if k != "integrity"}
    payload = salt() + json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    try:
        with open(CARD, encoding="utf-8") as f:
            card = json.load(f)
    except (OSError, ValueError):
        print("no-scorecard")
        sys.exit(3)

    if mode == "stamp":
        card["integrity"] = seal(card)
        with open(CARD, "w", encoding="utf-8") as f:
            json.dump(card, f, ensure_ascii=False, indent=2)
        print("stamped")
        sys.exit(0)

    stored = card.get("integrity")
    if not stored:
        print("unsealed")  # scorecard predates sealing, or score skill skipped it
        sys.exit(4)
    if stored == seal(card):
        print("sealed-ok")
        sys.exit(0)
    print("MODIFIED-OUTSIDE-AGENTWRIGHT")
    sys.exit(5)


if __name__ == "__main__":
    main()
