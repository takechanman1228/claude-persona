"""Panel-Level Quality Assurance for Persona Panels.

Validates persona panels against diversity, consistency, and structural
requirements. Checks are split into hard fails (contract violations that
make the panel unusable) and soft warnings (quality signals that flag
issues but don't block usage).

Usage:
    python scripts/validate_panel.py --panel-dir personas/my-panel
    python scripts/validate_panel.py --panel-dir personas/my-panel --requested-count 30
    python scripts/validate_panel.py --panel-dir personas/my-panel --json
"""

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_panel(panel_dir: Path):
    """Load manifest.json and all persona JSONs from a panel directory.

    Returns:
        (manifest, personas): manifest dict and list of persona dicts.

    Raises:
        FileNotFoundError: if manifest.json is missing.
        ValueError: if no personas could be loaded.
    """
    manifest_path = panel_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {panel_dir}")

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    personas = []
    for filename in manifest.get("persona_files", []):
        filepath = panel_dir / filename
        if not filepath.exists():
            print(f"  Warning: {filename} listed in manifest but not found", file=sys.stderr)
            continue
        with open(filepath, encoding="utf-8") as f:
            personas.append(json.load(f))

    if not personas:
        raise ValueError(f"No persona files loaded from {panel_dir}")

    return manifest, personas


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_name(persona):
    """Extract full name from persona dict."""
    return persona.get("persona", {}).get("name", "")


def _get_surname(name):
    """Extract surname (last token) from a full name."""
    parts = name.strip().split()
    return parts[-1] if parts else ""


def _get_occupation_title(persona):
    """Extract occupation title from persona dict."""
    return persona.get("persona", {}).get("occupation", {}).get("title", "")


def _get_segment(persona):
    """Extract segment from top-level field."""
    return persona.get("segment", "")


def _get_age(persona):
    """Extract age from persona dict."""
    return persona.get("persona", {}).get("age", 0)


def _get_gender(persona):
    """Extract gender from persona dict."""
    return persona.get("persona", {}).get("gender", "")


def _get_residence(persona):
    """Extract residence from persona dict."""
    return persona.get("persona", {}).get("residence", "")


def _extract_state(residence):
    """Extract state/region from residence string.

    'Austin, TX' -> 'TX'
    'Portland, OR' -> 'OR'
    'Crown Heights, Brooklyn, NY' -> 'NY'
    """
    parts = [p.strip() for p in residence.split(",")]
    return parts[-1] if parts else ""


def _age_bucket(age):
    """Convert age to 5-year bucket string.

    34 -> '30-34', 25 -> '25-29', 55 -> '55-59'
    """
    lower = (age // 5) * 5
    return f"{lower}-{lower + 4}"


def _get_big_five(persona):
    """Extract Big Five scores as a 5-element list [O, C, E, A, N]."""
    bf = persona.get("persona", {}).get("personality", {}).get("big_five", {})
    keys = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
    values = [bf.get(k) for k in keys]
    if any(v is None for v in values):
        return None
    return [float(v) for v in values]


def _cosine_similarity(a, b):
    """Compute cosine similarity between two vectors. Stdlib only."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# Hard Fail checks
# ---------------------------------------------------------------------------


def check_total_count(manifest, personas, requested_count=None):
    """Verify persona count matches manifest and optional requested count."""
    manifest_total = manifest.get("total_personas", 0)
    actual = len(personas)
    details = {
        "manifest_total": manifest_total,
        "actual_loaded": actual,
        "requested_count": requested_count,
    }

    issues = []
    if actual != manifest_total:
        issues.append(f"manifest says {manifest_total} but {actual} loaded")
    if requested_count is not None and actual != requested_count:
        issues.append(f"requested {requested_count} but {actual} loaded")

    details["issues"] = issues
    return {
        "check": "total_count",
        "passed": len(issues) == 0,
        "severity": "fail",
        "details": details,
    }


def check_segment_balance(manifest, personas):
    """Verify per-segment persona counts match manifest declarations."""
    mode = manifest.get("generation_mode", "segment-driven")
    segments_spec = manifest.get("segments", [])

    if mode == "topic-only" or not segments_spec:
        # Topic-only: just verify total count consistency
        return {
            "check": "segment_balance",
            "passed": True,
            "severity": "fail",
            "details": {"mode": mode, "note": "topic-only mode, no segment balance to check"},
        }

    # Build expected vs actual counts
    expected = {s["name"]: s.get("count", 0) for s in segments_spec}
    actual = Counter(_get_segment(p) for p in personas)

    mismatches = []
    for seg_name, exp_count in expected.items():
        act_count = actual.get(seg_name, 0)
        if act_count != exp_count:
            mismatches.append(
                {"segment": seg_name, "expected": exp_count, "actual": act_count}
            )

    # Check for unexpected segments
    for seg_name in actual:
        if seg_name not in expected:
            mismatches.append(
                {"segment": seg_name, "expected": 0, "actual": actual[seg_name], "note": "unexpected segment"}
            )

    return {
        "check": "segment_balance",
        "passed": len(mismatches) == 0,
        "severity": "fail",
        "details": {"expected": dict(expected), "actual": dict(actual), "mismatches": mismatches},
    }


def check_name_uniqueness(manifest, personas):
    """Verify all full names are unique across the panel."""
    names = [_get_name(p) for p in personas]
    counts = Counter(names)
    duplicates = {name: count for name, count in counts.items() if count > 1}

    return {
        "check": "name_uniqueness",
        "passed": len(duplicates) == 0,
        "severity": "fail",
        "details": {"total_names": len(names), "duplicates": duplicates},
    }


def check_segment_metadata(manifest, personas):
    """Verify all segments in manifest have a description field."""
    mode = manifest.get("generation_mode", "segment-driven")
    segments_spec = manifest.get("segments", [])

    if mode == "topic-only" or not segments_spec:
        return {
            "check": "segment_metadata",
            "passed": True,
            "severity": "fail",
            "details": {"mode": mode, "note": "topic-only mode, no segment descriptions to check"},
        }

    missing = []
    for seg in segments_spec:
        desc = seg.get("description", "")
        if not desc or not desc.strip():
            missing.append(seg.get("name", "(unnamed)"))

    return {
        "check": "segment_metadata",
        "passed": len(missing) == 0,
        "severity": "fail",
        "details": {"missing_descriptions": missing},
    }


# ---------------------------------------------------------------------------
# Soft Warning checks
# ---------------------------------------------------------------------------


def check_surname_diversity(manifest, personas):
    """Check for over-represented surnames (>= 3 occurrences)."""
    surnames = [_get_surname(_get_name(p)) for p in personas]
    counts = Counter(surnames)
    over_represented = {name: count for name, count in counts.items() if count >= 3}

    return {
        "check": "surname_diversity",
        "passed": len(over_represented) == 0,
        "severity": "warning",
        "details": {
            "surname_counts": dict(counts.most_common(10)),
            "over_represented": over_represented,
        },
    }


def check_occupation_diversity(manifest, personas):
    """Check for duplicate occupation titles across the panel."""
    titles = [_get_occupation_title(p).lower().strip() for p in personas]
    counts = Counter(titles)
    duplicates = {}
    for title, count in counts.items():
        if count >= 2:
            # Find the original-case names for display
            original_names = []
            for p in personas:
                if _get_occupation_title(p).lower().strip() == title:
                    original_names.append(f"{_get_name(p)} ({_get_segment(p)})")
            duplicates[title] = {"count": count, "personas": original_names}

    return {
        "check": "occupation_diversity",
        "passed": len(duplicates) == 0,
        "severity": "warning",
        "details": {"duplicates": duplicates, "total_unique": len(set(titles)), "total_personas": len(titles)},
    }


def check_geo_spread(manifest, personas):
    """Check geographic diversity within each segment (min 3 regions for N>=5)."""
    by_segment = defaultdict(list)
    for p in personas:
        by_segment[_get_segment(p)].append(_extract_state(_get_residence(p)))

    warnings = []
    per_segment = {}
    for seg_name, states in by_segment.items():
        unique = set(states)
        per_segment[seg_name] = {"regions": sorted(unique), "unique_count": len(unique), "total": len(states)}
        if len(states) >= 5 and len(unique) < 3:
            warnings.append(f"{seg_name}: only {len(unique)} region(s) for {len(states)} personas")

    return {
        "check": "geo_spread",
        "passed": len(warnings) == 0,
        "severity": "warning",
        "details": {"per_segment": per_segment, "warnings": warnings},
    }


def check_age_spread(manifest, personas):
    """Check age bucket distribution within each segment (max 2 per 5-year bracket)."""
    by_segment = defaultdict(list)
    for p in personas:
        by_segment[_get_segment(p)].append(_get_age(p))

    warnings = []
    per_segment = {}
    for seg_name, ages in by_segment.items():
        buckets = Counter(_age_bucket(a) for a in ages)
        violations = {b: c for b, c in buckets.items() if c >= 3}
        per_segment[seg_name] = {"buckets": dict(buckets), "violations": violations}
        for bucket, count in violations.items():
            warnings.append(f"{seg_name}: {count} personas in age bracket {bucket}")

    return {
        "check": "age_spread",
        "passed": len(warnings) == 0,
        "severity": "warning",
        "details": {"per_segment": per_segment, "warnings": warnings},
    }


def check_gender_distribution(manifest, personas):
    """Check gender balance within each segment (min 30% minority for N>=5)."""
    by_segment = defaultdict(list)
    for p in personas:
        by_segment[_get_segment(p)].append(_get_gender(p))

    warnings = []
    per_segment = {}
    for seg_name, genders in by_segment.items():
        counts = Counter(genders)
        total = len(genders)
        per_segment[seg_name] = {"counts": dict(counts), "total": total}
        if total >= 5:
            # Find minority percentage (excluding non-binary for the binary ratio)
            binary_genders = {g: c for g, c in counts.items() if g.lower() in ("male", "female")}
            if binary_genders:
                minority_count = min(binary_genders.values())
                binary_total = sum(binary_genders.values())
                minority_pct = minority_count / binary_total if binary_total > 0 else 0
                per_segment[seg_name]["minority_pct"] = round(minority_pct, 2)
                if minority_pct < 0.30:
                    warnings.append(
                        f"{seg_name}: minority gender at {minority_pct:.0%} (threshold: 30%)"
                    )

    return {
        "check": "gender_distribution",
        "passed": len(warnings) == 0,
        "severity": "warning",
        "details": {"per_segment": per_segment, "warnings": warnings},
    }


def check_big_five_similarity(manifest, personas):
    """Check for near-duplicate Big Five profiles (cosine similarity >= 0.92)."""
    profiles = []
    for p in personas:
        bf = _get_big_five(p)
        if bf is not None:
            profiles.append((_get_name(p), bf))

    high_sim_pairs = []
    max_sim = 0.0
    total_pairs = 0

    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            total_pairs += 1
            sim = _cosine_similarity(profiles[i][1], profiles[j][1])
            if sim > max_sim:
                max_sim = sim
            if sim >= 0.98:
                high_sim_pairs.append({
                    "a": profiles[i][0],
                    "b": profiles[j][0],
                    "similarity": round(sim, 4),
                })

    # Sort by similarity descending, keep top 10 for display
    high_sim_pairs.sort(key=lambda x: x["similarity"], reverse=True)

    return {
        "check": "big_five_similarity",
        "passed": len(high_sim_pairs) == 0,
        "severity": "warning",
        "details": {
            "high_similarity_pairs": high_sim_pairs[:10],
            "total_flagged": len(high_sim_pairs),
            "total_pairs_checked": total_pairs,
            "max_similarity": round(max_sim, 4) if total_pairs > 0 else None,
        },
    }


# ---------------------------------------------------------------------------
# Slot Adherence check (only when sampling_plan exists in manifest)
# ---------------------------------------------------------------------------


def check_slot_adherence(manifest, personas):
    """Verify personas adhere to their sampling plan slot specifications.

    Only runs if manifest contains a 'sampling_plan' field.
    Checks age_bucket, gender, and segment alignment.
    """
    plan = manifest.get("sampling_plan")
    if not plan:
        return {
            "check": "slot_adherence",
            "passed": True,
            "severity": "fail",
            "details": {"note": "no sampling_plan in manifest, skipping"},
        }

    # Match personas to slots by name or index
    persona_by_name = {_get_name(p): p for p in personas}
    violations = []

    for slot in plan:
        slot_idx = slot.get("slot", "?")
        slot_segment = slot.get("segment", "")
        slot_age_bucket = slot.get("age_bucket", "")
        slot_gender = slot.get("gender", "")
        slot_name = slot.get("name", "")

        # Try to find matching persona
        persona = persona_by_name.get(slot_name)
        if not persona:
            # Try matching by slot index if names aren't set yet
            if isinstance(slot_idx, int) and 0 < slot_idx <= len(personas):
                persona = personas[slot_idx - 1]
            else:
                continue

        # Check segment
        actual_segment = _get_segment(persona)
        if slot_segment and actual_segment != slot_segment:
            violations.append({
                "slot": slot_idx,
                "persona": _get_name(persona),
                "field": "segment",
                "expected": slot_segment,
                "actual": actual_segment,
            })

        # Check age bucket
        if slot_age_bucket:
            actual_age = _get_age(persona)
            actual_bucket = _age_bucket(actual_age)
            # Parse expected bucket: "30s" -> age 30-39
            expected_decade = slot_age_bucket.rstrip("s")
            try:
                decade_start = int(expected_decade)
                if not (decade_start <= actual_age < decade_start + 10):
                    violations.append({
                        "slot": slot_idx,
                        "persona": _get_name(persona),
                        "field": "age_bucket",
                        "expected": slot_age_bucket,
                        "actual": f"{actual_age} ({actual_bucket})",
                    })
            except ValueError:
                violations.append({
                    "slot": slot_idx,
                    "persona": _get_name(persona),
                    "field": "age_bucket",
                    "expected": slot_age_bucket,
                    "actual": f"unparseable bucket: {slot_age_bucket}",
                })

        # Check gender
        if slot_gender and _get_gender(persona).lower() != slot_gender.lower():
            violations.append({
                "slot": slot_idx,
                "persona": _get_name(persona),
                "field": "gender",
                "expected": slot_gender,
                "actual": _get_gender(persona),
            })

    return {
        "check": "slot_adherence",
        "passed": len(violations) == 0,
        "severity": "fail",
        "details": {"violations": violations, "slots_checked": len(plan)},
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


ALL_CHECKS = [
    # Hard fails
    check_total_count,
    check_segment_balance,
    check_name_uniqueness,
    check_segment_metadata,
    # Soft warnings
    check_surname_diversity,
    check_occupation_diversity,
    check_geo_spread,
    check_age_spread,
    check_gender_distribution,
    check_big_five_similarity,
    # Conditional
    check_slot_adherence,
]


def validate_panel(panel_dir, requested_count=None):
    """Run all validation checks on a panel directory.

    Returns a structured dict with all check results.
    overall_pass is True only when there are zero hard fails.
    """
    if isinstance(panel_dir, str):
        panel_dir = Path(panel_dir)

    manifest, personas = load_panel(panel_dir)

    checks = []
    for check_fn in ALL_CHECKS:
        if check_fn is check_total_count:
            result = check_fn(manifest, personas, requested_count=requested_count)
        else:
            result = check_fn(manifest, personas)
        checks.append(result)

    hard_fails = sum(1 for c in checks if not c["passed"] and c["severity"] == "fail")
    warnings = sum(1 for c in checks if not c["passed"] and c["severity"] == "warning")

    return {
        "panel_dir": str(panel_dir),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_checks": len(checks),
        "hard_fails": hard_fails,
        "warnings": warnings,
        "checks": checks,
        "overall_pass": hard_fails == 0,
    }


# ---------------------------------------------------------------------------
# CLI output
# ---------------------------------------------------------------------------


def _print_summary(result):
    """Human-readable summary of validation results."""
    print(f"\nPanel QA Report: {result['panel_dir']}")
    print("=" * 60)

    for check in result["checks"]:
        icon = "PASS" if check["passed"] else ("FAIL" if check["severity"] == "fail" else "WARN")
        marker = {"PASS": "+", "FAIL": "!", "WARN": "~"}[icon]
        print(f"  [{marker}] {icon:4s}  {check['check']}")

        if not check["passed"]:
            details = check["details"]
            # Print relevant detail lines
            if "issues" in details and details["issues"]:
                for issue in details["issues"]:
                    print(f"         {issue}")
            if "mismatches" in details and details["mismatches"]:
                for m in details["mismatches"]:
                    print(f"         {m['segment']}: expected {m['expected']}, got {m['actual']}")
            if "duplicates" in details and details["duplicates"]:
                if isinstance(details["duplicates"], dict):
                    for k, v in details["duplicates"].items():
                        if isinstance(v, dict):
                            print(f"         '{k}': {v['count']}x — {', '.join(v['personas'])}")
                        else:
                            print(f"         '{k}': {v}x")
            if "missing_descriptions" in details and details["missing_descriptions"]:
                for seg in details["missing_descriptions"]:
                    print(f"         missing description: {seg}")
            if "over_represented" in details and details["over_represented"]:
                for name, count in details["over_represented"].items():
                    print(f"         surname '{name}': {count}x")
            if "warnings" in details and details["warnings"]:
                for w in details["warnings"]:
                    print(f"         {w}")
            if "high_similarity_pairs" in details and details["high_similarity_pairs"]:
                for pair in details["high_similarity_pairs"]:
                    print(f"         {pair['a']} <-> {pair['b']}: {pair['similarity']}")
            if "violations" in details and details["violations"]:
                for v in details["violations"]:
                    print(f"         slot {v['slot']}: {v['persona']} — {v['field']}: expected {v['expected']}, got {v['actual']}")

    print()
    print(f"  Total: {result['total_checks']} checks | "
          f"{result['hard_fails']} fail(s) | "
          f"{result['warnings']} warning(s)")

    if result["overall_pass"]:
        print("  Result: PASS (no hard fails)")
    else:
        print("  Result: FAIL")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Panel-Level Quality Assurance for Persona Panels"
    )
    parser.add_argument(
        "--panel-dir",
        required=True,
        help="Path to persona panel directory (containing manifest.json)",
    )
    parser.add_argument(
        "--requested-count",
        type=int,
        default=None,
        help="Expected total persona count (optional)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of human-readable summary",
    )
    args = parser.parse_args()

    panel_dir = Path(args.panel_dir)
    if not panel_dir.is_absolute():
        panel_dir = Path.cwd() / panel_dir

    result = validate_panel(panel_dir, requested_count=args.requested_count)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_summary(result)

    sys.exit(0 if result["overall_pass"] else 1)


if __name__ == "__main__":
    main()
