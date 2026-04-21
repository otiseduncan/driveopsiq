import json
from pathlib import Path

REPORTS_DIR = Path("reports")
INPUT_FILE = REPORTS_DIR / "summary.json"
OUTPUT_FILE = REPORTS_DIR / "summary.md"

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Missing input JSON report: {INPUT_FILE}")

data = json.loads(INPUT_FILE.read_text())

def emoji_for_severity(sev: str) -> str:
    s = sev.lower()
    if "high" in s:
        return "🔴"
    if "medium" in s:
        return "🟡"
    if "low" in s:
        return "🟢"
    return "⚪"

md = ["# 🧩 SyferStackV2 Full Production Audit Summary\n"]

for key, value in data.items():
    md.append(f"## {key.capitalize()}")
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, dict):
                sev = v.get("severity", "")
                emoji = emoji_for_severity(sev)
                msg = v.get("message", "")
                md.append(f"- **{k}** ({emoji} {sev}) → {msg}")
            else:
                md.append(f"- **{k}:** {v}")
    elif isinstance(value, list):
        for item in value:
            md.append(f"- {item}")
    else:
        md.append(str(value))
    md.append("")

OUTPUT_FILE.write_text("\n".join(md))
print(f"✅ Enhanced Markdown summary generated → {OUTPUT_FILE}")

