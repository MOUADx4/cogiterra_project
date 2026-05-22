"""Configuration commune des tests."""
import os
import sys

# Permet aux tests d'importer les modules du projet sans installation
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name: str) -> bytes:
    """Charge un email RFC 2822 depuis tests/fixtures/."""
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, "rb") as f:
        return f.read()
