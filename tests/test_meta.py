"""Meta checks (projekt.md P2.7): translations parity with strings.json,
connection-event keys in sync with docs/PROTOCOL.md, manifest pointing at
the own repository."""

import json
import re
from pathlib import Path

from custom_components.helios import identity

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "helios"
INSTALLATION = "0f3c1b2a-9d8e-4c7b-a6f5-1e2d3c4b5a69"


def _leaves(node, prefix=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _leaves(value, f"{prefix}.{key}" if prefix else key)
    else:
        yield prefix, node


def _placeholders(text):
    return set(re.findall(r"\{([^}]+)\}", text))


def test_every_translation_covers_exactly_the_strings_keys():
    strings = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    expected = dict(_leaves(strings))
    translations = sorted((COMPONENT / "translations").glob("*.json"))
    assert translations, "no translations at all"
    for path in translations:
        actual = dict(_leaves(json.loads(path.read_text(encoding="utf-8"))))
        assert set(actual) == set(expected), (
            f"{path.name}: keys differ from strings.json "
            f"(missing={sorted(set(expected) - set(actual))}, extra={sorted(set(actual) - set(expected))})"
        )
        for key, value in expected.items():
            assert _placeholders(str(value)) == _placeholders(str(actual[key])), f"{path.name}: placeholders differ at {key}"


async def test_connection_payload_keys_match_protocol_doc(hass):
    text = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
    section = text.split("**`connection`**", 1)[1]
    block = section.split("```json", 1)[1].split("```", 1)[0]
    documented = set(json.loads(block))
    payload = identity.connection_payload(hass, {"installation_id": INSTALLATION}, {})
    assert set(payload) == documented, f"connection event keys out of sync with PROTOCOL.md: code={sorted(payload)} doc={sorted(documented)}"


def test_manifest_points_at_the_own_repo():
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["codeowners"] == ["@Hendy59"]
    assert manifest["documentation"] == "https://github.com/Hendy59/ha-Eos"
    assert manifest["issue_tracker"] == "https://github.com/Hendy59/ha-Eos/issues"
