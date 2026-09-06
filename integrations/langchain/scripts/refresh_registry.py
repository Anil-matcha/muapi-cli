#!/usr/bin/env python3
"""Generate muapi_langchain/data/models.json and skills.json from muapiapp source.

Usage:
    python3 scripts/refresh_registry.py \
        --schema /path/to/muapiapp/server/data/schema_data.json \
        --skills /path/to/muapiapp/skills/library
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "muapi_langchain" / "data"

# schema_data.json category → registry category string (matches CATEGORY_FOR_KIND values)
CATEGORY_MAP = {
    "Text to Image": "text-to-image",
    "Image to Image": "image-edit",
    "Text to Video": "text-to-video",
    "Image to Video": "image-to-video",
    "Video to Video": "video-edit",
    "Text to Audio": "audio",
    "Audio to Video": "lipsync",
    "Image to 3D": "3d",
    "Text to Text": "text",
}

# Tier heuristic: classify by cost per generation (dollars)
def _infer_tier(cost: float, name: str) -> str:
    nm = (name or "").lower()
    if any(k in nm for k in ("schnell", "lite", "fast", "turbo", "flash", "mini")):
        return "fast"
    if any(k in nm for k in ("pro", "max", "ultra", "premium", "plus")):
        return "best"
    if cost == 0 or cost < 0.02:
        return "budget"
    if cost >= 1.0:
        return "best"
    if cost >= 0.2:
        return "balanced"
    return "balanced"


def build_models(schema_path: Path) -> list[dict]:
    data = json.loads(schema_path.read_text())
    out = []
    seen = set()
    for m in data:
        if not m.get("isEnabled"):
            continue
        raw_cat = m.get("category", "")
        cat = CATEGORY_MAP.get(raw_cat)
        if cat is None:
            continue
        name = m["name"]
        if name in seen:
            continue
        seen.add(name)
        cost = float(m.get("cost") or 0)
        out.append({
            "name": name,
            "description": (m.get("description") or "").strip(),
            "category": cat,
            "tier": _infer_tier(cost, name),
            "cost": cost,
            "provider": m.get("provider_name", ""),
        })
    return out


def _parse_frontmatter(text: str) -> dict:
    """Extract simple key: value frontmatter from a SKILL.md file."""
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"')
    return fm


def _parse_inputs(text: str) -> list[dict]:
    """Pull the Inputs table rows from a SKILL.md body."""
    inputs = []
    in_table = False
    for line in text.splitlines():
        if re.match(r"\|\s*Name\s*\|", line, re.I):
            in_table = True
            continue
        if in_table:
            if line.strip().startswith("|:-") or line.strip().startswith("| :-"):
                continue
            if not line.strip().startswith("|"):
                break
            cols = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
            if len(cols) >= 3:
                inputs.append({
                    "name": cols[0],
                    "type": cols[1] if len(cols) > 1 else "text",
                    "required": cols[2].lower() == "yes" if len(cols) > 2 else False,
                })
    return inputs


def _extract_keywords(text: str, name: str, description: str) -> list[str]:
    words = set()
    for src in (name, description):
        words.update(re.findall(r"[a-z]{4,}", src.lower()))
    return sorted(words - {"with", "that", "this", "from", "your", "will", "have", "muapi"})[:12]


def build_skills(skills_root: Path) -> list[dict]:
    out = []
    seen = set()
    for skill_md in sorted(skills_root.rglob("SKILL.md")):
        text = skill_md.read_text(errors="replace")
        fm = _parse_frontmatter(text)
        name = fm.get("name") or fm.get("slug") or skill_md.parent.name
        if not name or name in seen:
            continue
        seen.add(name)
        description = fm.get("description", "")
        out.append({
            "name": name,
            "description": description,
            "trigger_keywords": _extract_keywords(text, name, description),
            "inputs": _parse_inputs(text),
            "estimated_credits": None,
        })
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh muapi_langchain registry data files.")
    parser.add_argument(
        "--schema",
        default=str(Path(__file__).parent.parent.parent.parent.parent /
                    "muapiapp/server/data/schema_data.json"),
        help="Path to muapiapp/server/data/schema_data.json",
    )
    parser.add_argument(
        "--skills",
        default=str(Path(__file__).parent.parent.parent.parent.parent /
                    "muapiapp/skills/library"),
        help="Path to muapiapp/skills/library",
    )
    args = parser.parse_args()

    schema_path = Path(args.schema)
    skills_root = Path(args.skills)

    if not schema_path.exists():
        sys.exit(f"schema_data.json not found at {schema_path}")
    if not skills_root.exists():
        sys.exit(f"skills/library not found at {skills_root}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    models = build_models(schema_path)
    (DATA_DIR / "models.json").write_text(json.dumps(models, indent=2))
    print(f"Wrote {len(models)} models → {DATA_DIR / 'models.json'}")

    skills = build_skills(skills_root)
    (DATA_DIR / "skills.json").write_text(json.dumps(skills, indent=2))
    print(f"Wrote {len(skills)} skills → {DATA_DIR / 'skills.json'}")


if __name__ == "__main__":
    main()
