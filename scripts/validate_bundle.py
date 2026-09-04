from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SC = ROOT / "dataset" / "Kath6_Q" / "base" / "kath6-r1-static-route-removed.txt"
LAB = ROOT / "topology_kathara" / "Kath6" / "lab.conf"

text = SC.read_text(encoding="utf-8")
required_headers = ["Scenario:", "Topology:", "Fault family:", "Ticket style:"]
required_sections = [
    "PROMPT-TO-AGENT", "INJECTION", "POST-INJECT-CHECK",
    "GROUND-TRUTH", "FIX", "SCORING-AXES", "DIAGNOSTIC-PROCESS"
]

for h in required_headers:
    assert re.search(rf"^{re.escape(h)}\s*\S+", text, re.M), f"missing header {h}"
for s in required_sections:
    assert f"[{s}]" in text, f"missing section [{s}]"

check_re = re.compile(r"^(\S+)\s+(.+?)\s*=>\s*expect\s+(.+?)\s*$")
for section in ("PRE-CHECK", "POST-INJECT-CHECK"):
    m = re.search(rf"\[{section}\]\n(.*?)(?=\n\[|\Z)", text, re.S)
    if m:
        for raw in m.group(1).splitlines():
            raw = raw.strip()
            if raw and not raw.startswith("#"):
                assert check_re.match(raw), f"bad check line: {raw}"

lab = LAB.read_text(encoding="utf-8")
for dev in ("pc1", "r1", "r2", "pc2"):
    assert re.search(rf"^{dev}\[\d+\]", lab, re.M), f"{dev} missing from lab.conf"
    assert (LAB.parent / f"{dev}.startup").exists(), f"missing {dev}.startup"

print("Static bundle validation: PASS")
print(f"Scenario: {SC}")
print(f"Lab:      {LAB}")
