#!/usr/bin/env python3
"""
Persona Research Virtual Survey — Analysis & Visualization Pipeline

Usage:
    python analyze_results.py --input results.json --survey-type concept-test
    python analyze_results.py --input results.json --survey-type brand-map
    python analyze_results.py --input results.json --survey-type price-test
    python analyze_results.py --input results.json --survey-type usage-habits
    python analyze_results.py --input results.json --survey-type survey
    python analyze_results.py --input results.json --survey-type ask
    python analyze_results.py --input results.json --survey-type concept-test --report-only
    python analyze_results.py --input results.json --survey-type concept-test --report-llm --backend codex-cli

Outputs (in same directory as input):
    - results.csv           All responses as flat table
    - summary.json          Aggregate statistics
    - cross_tabs.csv        Segment × response cross-tabulation (concept-test)
    - persona_comparison.csv Persona comparison table (degenerate segment case)
    - chart_*.png           Survey-specific charts (skipped with --report-only)
    - report.md             Markdown one-pager report
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SKILL_DIR = SCRIPT_DIR.parent

from llm_backends import (
    BACKEND_CHOICES,
    REPORT_BACKEND_CHOICES,
    format_model_label,
    resolve_backend,
    resolve_model,
    resolve_report_backend,
    run_text_completion,
)


# ─── Lazy chart imports ────────────────────────────────────────────────────

_chart_libs_loaded = False


def _load_chart_libs():
    """Load matplotlib/seaborn on first use (skipped in --report-only mode)."""
    global _chart_libs_loaded, matplotlib, plt, sns, COLORS, OPTION_COLORS, FIG_SIZE, DPI
    if _chart_libs_loaded:
        return
    import matplotlib as _matplotlib
    _matplotlib.use("Agg")
    import matplotlib.pyplot as _plt
    import seaborn as _sns
    matplotlib = _matplotlib
    plt = _plt
    sns = _sns
    sns.set_theme(style="whitegrid", palette="Set2", font_scale=1.05)
    COLORS = sns.color_palette("Set2")
    OPTION_COLORS = {"A": "#66c2a5", "B": "#fc8d62", "C": "#8da0cb", "D": "#e78ac3"}
    FIG_SIZE = (10, 6)
    DPI = 150
    _chart_libs_loaded = True


# ─── Core: Load, Normalize, Flatten ────────────────────────────────────────

META_KEYS = {"name", "segment", "age", "gender", "occupation", "responses"}
FREQUENCY_ORDER = {"daily": 5, "weekly": 4, "monthly": 3, "rarely": 2, "never": 1}


def load_results(path: Path) -> list[dict]:
    """Load results JSON (array of persona response objects)."""
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of response objects")
    return data


def normalize_result_entry(result: dict) -> dict:
    """Normalize legacy and canonical result rows to a single contract."""
    if not isinstance(result, dict):
        raise ValueError("Each result entry must be a JSON object")

    responses = {}
    if isinstance(result.get("responses"), dict):
        responses.update(result["responses"])

    for key, value in result.items():
        if key in META_KEYS:
            continue
        responses.setdefault(key, value)

    return {
        "name": result.get("name", ""),
        "segment": result.get("segment", "Unknown") or "Unknown",
        "age": result.get("age"),
        "gender": result.get("gender", ""),
        "occupation": result.get("occupation", ""),
        "responses": responses,
    }


def normalize_results(results: list[dict]) -> list[dict]:
    """Normalize all result entries."""
    return [normalize_result_entry(result) for result in results]


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def _display_label(value: str) -> str:
    text = str(value).replace("_", " ").strip()
    return re.sub(r"\s+", " ", text).title()


def _truncate(text: object, limit: int = 140, sentence_aware: bool = False) -> str:
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    if sentence_aware:
        window = text[:limit]
        for marker in (". ", "! ", "? ", "。", "！", "？"):
            idx = window.rfind(marker)
            if idx >= limit // 2:
                return text[: idx + len(marker)].rstrip()
    return text[: limit - 3].rstrip() + "..."


def _short_text_label(text: object, max_words: int = 6) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    line = value.splitlines()[0].strip()
    for separator in [" — ", " – ", " - ", ",", ";", "."]:
        if separator in line:
            candidate = line.split(separator, 1)[0].strip()
            if 1 <= len(candidate) <= 48:
                return candidate
    words = line.split()
    if len(words) <= max_words:
        return line
    return " ".join(words[:max_words])


def _format_value(value: object, limit: int = 140) -> str:
    if isinstance(value, list):
        return _truncate(", ".join(str(item) for item in value), limit=limit)
    if isinstance(value, dict):
        parts = []
        for key, item in list(value.items())[:4]:
            if isinstance(item, list):
                item_text = ", ".join(str(v) for v in item[:3])
            else:
                item_text = str(item)
            parts.append(f"{key}: {item_text}")
        return _truncate("; ".join(parts), limit=limit)
    return _truncate(value, limit=limit)


def _normalize_usage_label(value: object) -> str:
    text = str(value or "").lower()
    text = re.sub(r"\([^)]*\)", "", text)
    text = text.replace("/", " ")
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def flatten_responses(results: list[dict]) -> pd.DataFrame:
    """Flatten canonical response objects into a flat DataFrame."""
    rows = []
    for result in results:
        row = {
            "name": result.get("name", ""),
            "segment": result.get("segment", "Unknown"),
            "age": result.get("age"),
            "gender": result.get("gender", ""),
            "occupation": result.get("occupation", ""),
        }
        for key, value in result.get("responses", {}).items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                row[key] = value
            elif isinstance(value, list):
                row[key] = "; ".join(str(item) for item in value)
            elif isinstance(value, dict):
                row[key] = json.dumps(value, ensure_ascii=False)
                for subkey, subvalue in value.items():
                    flat_key = f"{key}_{_normalize_key(subkey)}"
                    if isinstance(subvalue, list):
                        row[flat_key] = "; ".join(str(item) for item in subvalue)
                    elif isinstance(subvalue, (str, int, float, bool)) or subvalue is None:
                        row[flat_key] = subvalue
                    else:
                        row[flat_key] = json.dumps(subvalue, ensure_ascii=False)
            else:
                row[key] = str(value)
        rows.append(row)
    return pd.DataFrame(rows)


def _is_degenerate_crosstab(df: pd.DataFrame) -> bool:
    """Check if segment values are all unique (topic-only mode with archetype labels)."""
    return not df.empty and df["segment"].nunique() == len(df)


def _generate_persona_comparison(df: pd.DataFrame, output_dir: Path):
    """Generate persona comparison table instead of cross-tab when segments are unique."""
    cols = ["name", "segment", "age", "gender", "occupation"]
    preferred_cols = [
        "preferred_option",
        "purchase_likelihood",
        "max_wtp",
        "current_product",
        "purchase_channel",
        "reasoning",
        "pain_points",
    ]
    for col in preferred_cols:
        if col in df.columns:
            cols.append(col)
    comparison = df[[col for col in cols if col in df.columns]].copy()
    comparison.to_csv(output_dir / "persona_comparison.csv", index=False)
    return comparison


# ─── Utilities ─────────────────────────────────────────────────────────────



def _parse_price_label(label: str) -> tuple[float, str]:
    """Parse a price label for sorting while preserving the original label."""
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", str(label))
    numeric = float(match.group(1)) if match else float("inf")
    cleaned = str(label)
    if cleaned and not cleaned.startswith("$") and match:
        cleaned = f"${cleaned}"
    return numeric, cleaned


def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    """Return a numeric series with NaNs dropped."""
    if column not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[column], errors="coerce").dropna()


def _summarize_numeric(series: pd.Series) -> dict | None:
    if series.empty:
        return None
    return {
        "mean": round(float(series.mean()), 2),
        "median": round(float(series.median()), 2),
        "min": round(float(series.min()), 2),
        "max": round(float(series.max()), 2),
    }


def _sorted_counter(counter: Counter, limit: int | None = None) -> dict:
    items = counter.most_common(limit)
    return {key: value for key, value in items}


def _top_ranked_factor(factor_ranking: dict) -> str:
    if not isinstance(factor_ranking, dict) or not factor_ranking:
        return ""
    best = None
    for factor, rank in factor_ranking.items():
        try:
            numeric = float(rank)
        except (TypeError, ValueError):
            continue
        if best is None or numeric < best[1]:
            best = (str(factor), numeric)
    return best[0] if best else ""


def _favorite_price_point(intent_by_price: dict) -> tuple[str, float] | tuple[None, None]:
    if not isinstance(intent_by_price, dict) or not intent_by_price:
        return (None, None)
    best = None
    for label, intent in intent_by_price.items():
        try:
            numeric_intent = float(intent)
        except (TypeError, ValueError):
            continue
        price_value, cleaned = _parse_price_label(label)
        candidate = (numeric_intent, -price_value, cleaned)
        if best is None or candidate > best:
            best = candidate
    if best is None:
        return (None, None)
    return best[2], best[0]


def _summarize_usage_frequency(usage_frequency: dict) -> str:
    if not isinstance(usage_frequency, dict) or not usage_frequency:
        return ""
    ranked = []
    for occasion, frequency in usage_frequency.items():
        score = FREQUENCY_ORDER.get(str(frequency).lower(), 0)
        if score > 1:
            ranked.append((score, str(occasion), str(frequency)))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    if not ranked:
        return "No active usage occasions mentioned"
    parts = [f"{occasion} ({frequency})" for _, occasion, frequency in ranked[:3]]
    return ", ".join(parts)


def _collect_verbatims(results: list[dict], survey_type: str) -> list[tuple[str, str, object, str]]:
    """Collect candidate verbatims for the report. Max 1 per persona."""
    candidates = []
    seen = set()
    for result in results:
        responses = result.get("responses", {})
        texts = []
        if survey_type == "concept-test":
            texts = [responses.get("reasoning", "")]
        elif survey_type == "brand-map":
            associations = responses.get("brand_associations", {})
            if isinstance(associations, dict):
                texts = list(associations.values())
        elif survey_type == "price-test":
            texts = [responses.get("reasoning", ""), responses.get("value_perception", "")]
        elif survey_type == "usage-habits":
            texts = [responses.get("pain_points", ""), responses.get("current_product", "")]
        elif survey_type == "ask":
            texts = [responses.get("reasoning", ""), responses.get("short_answer", "")]
        else:
            for value in responses.values():
                if isinstance(value, str):
                    texts.append(value)
        # Pick the single best (longest non-duplicate) text for this persona
        best = None
        for text in texts:
            cleaned = str(text).strip()
            if len(cleaned) < 20 or cleaned in seen:
                continue
            if best is None or len(cleaned) > len(best):
                best = cleaned
        if best is not None:
            seen.add(best)
            candidates.append(
                (best, result.get("name", "Unknown"), result.get("age", "?"), result.get("occupation", ""))
            )
    # Sort by length descending so the most articulate quotes appear first
    candidates.sort(key=lambda c: len(c[0]), reverse=True)
    return candidates[:3]


# ─── Analysis: Concept Test ───────────────────────────────────────────────


def analyze_concept_test(results: list[dict], df: pd.DataFrame, output_dir: Path, report_only: bool = False):
    """Analyze concept test results: cross-tabs, charts, summary."""
    if df.empty:
        print("WARNING: No valid responses to analyze")
        return {"total_respondents": 0}
    if "preferred_option" not in df.columns:
        print("WARNING: No 'preferred_option' column found, skipping concept analysis")
        return {}

    degenerate = _is_degenerate_crosstab(df)
    if degenerate:
        _generate_persona_comparison(df, output_dir)
    else:
        cross_tab = pd.crosstab(df["segment"], df["preferred_option"], margins=True)
        cross_tab.to_csv(output_dir / "cross_tabs.csv")
        cross_pct = pd.crosstab(df["segment"], df["preferred_option"], normalize="index") * 100
        cross_pct.to_csv(output_dir / "cross_tabs_pct.csv", float_format="%.1f")

    if not report_only:
        _load_chart_libs()
        options = sorted(df["preferred_option"].dropna().unique())
        colors = [OPTION_COLORS.get(opt, COLORS[i % len(COLORS)]) for i, opt in enumerate(options)]

        if not degenerate:
            cross_tab_local = pd.crosstab(df["segment"], df["preferred_option"], margins=True)
            fig, ax = plt.subplots(figsize=FIG_SIZE)
            cross_tab_no_margin = cross_tab_local.drop("All", errors="ignore")
            cross_tab_no_margin = cross_tab_no_margin[[c for c in options if c in cross_tab_no_margin.columns]]
            cross_tab_no_margin.plot(kind="bar", stacked=True, color=colors, ax=ax, edgecolor="white")
            ax.set_title("Concept Preference by Segment", fontsize=14, fontweight="bold")
            ax.set_ylabel("Count")
            ax.set_xlabel("")
            ax.legend(title="Option", bbox_to_anchor=(1.02, 1), loc="upper left")
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            fig.savefig(output_dir / "chart_preference.png", dpi=DPI, bbox_inches="tight")
            plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 5))
        counts = df["preferred_option"].value_counts().reindex(options, fill_value=0)
        bars = ax.bar(
            counts.index,
            counts.values,
            color=[OPTION_COLORS.get(option, "#999") for option in counts.index],
            edgecolor="white",
            linewidth=1.5,
        )
        for bar, value in zip(bars, counts.values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3, str(value),
                    ha="center", va="bottom", fontweight="bold")
        ax.set_ylim(0, (max(counts.values) * 1.35 + 1) if len(counts) > 0 else 1)
        ax.set_title("Overall Concept Preference", fontsize=14, fontweight="bold")
        ax.set_ylabel("Count")
        ax.set_xlabel("Option")
        plt.tight_layout()
        fig.savefig(output_dir / "chart_overall.png", dpi=DPI, bbox_inches="tight")
        plt.close(fig)

        if "purchase_likelihood" in df.columns:
            purchase = pd.to_numeric(df["purchase_likelihood"], errors="coerce").dropna()
            if not purchase.empty:
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.hist(purchase, bins=[0.5, 1.5, 2.5, 3.5, 4.5, 5.5], color=COLORS[0], edgecolor="white")
                ax.set_title("Purchase Likelihood Distribution", fontsize=14, fontweight="bold")
                ax.set_xlabel("Likelihood (1-5)")
                ax.set_ylabel("Count")
                ax.set_xticks([1, 2, 3, 4, 5])
                plt.tight_layout()
                fig.savefig(output_dir / "chart_purchase_likelihood.png", dpi=DPI, bbox_inches="tight")
                plt.close(fig)

    summary = {
        "total_respondents": len(df),
        "segments": df["segment"].value_counts().to_dict(),
        "overall_preference": df["preferred_option"].value_counts().to_dict(),
        "preference_by_segment": {},
    }
    for segment in df["segment"].unique():
        seg_df = df[df["segment"] == segment]
        summary["preference_by_segment"][segment] = {
            "count": len(seg_df),
            "preferences": seg_df["preferred_option"].value_counts().to_dict(),
        }
    purchase = _numeric_series(df, "purchase_likelihood")
    purchase_summary = _summarize_numeric(purchase)
    if purchase_summary:
        summary["purchase_likelihood"] = purchase_summary
    return summary


# ─── Analysis: Brand Map ──────────────────────────────────────────────────


def analyze_brand_map(results: list[dict], df: pd.DataFrame, output_dir: Path, report_only: bool = False):
    """Analyze brand perception results."""
    if df.empty:
        print("WARNING: No valid responses to analyze")
        return {"total_respondents": 0}
    summary = {
        "total_respondents": len(df),
        "segments": df["segment"].value_counts().to_dict(),
    }

    if _is_degenerate_crosstab(df):
        _generate_persona_comparison(df, output_dir)

    awareness_counts = Counter()
    consideration_counts = Counter()
    sentiment_counts = defaultdict(Counter)
    familiarity_counts = defaultdict(Counter)

    for result in results:
        responses = result.get("responses", {})

        awareness = responses.get("unaided_awareness", [])
        if isinstance(awareness, str):
            awareness = [item.strip() for item in awareness.split(";") if item.strip()]
        for brand in awareness:
            awareness_counts[str(brand).strip()] += 1

        consideration = responses.get("consideration_set", [])
        if isinstance(consideration, str):
            consideration = [item.strip() for item in consideration.split(";") if item.strip()]
        for brand in consideration:
            consideration_counts[str(brand).strip()] += 1

        familiarity = responses.get("aided_familiarity", {})
        if isinstance(familiarity, dict):
            for brand, status in familiarity.items():
                familiarity_counts[str(brand).strip()][str(status).strip()] += 1

        buckets = responses.get("brand_buckets", {})
        if isinstance(buckets, dict):
            for bucket_name in ("like", "dislike", "neutral"):
                brands = buckets.get(bucket_name, [])
                if isinstance(brands, str):
                    brands = [item.strip() for item in brands.split(";") if item.strip()]
                for brand in brands:
                    sentiment_counts[str(brand).strip()][bucket_name] += 1

    summary["unaided_awareness_top10"] = _sorted_counter(awareness_counts, 10)
    summary["consideration_top10"] = _sorted_counter(consideration_counts, 10)
    summary["brand_sentiment"] = {
        brand: dict(counts)
        for brand, counts in sorted(
            sentiment_counts.items(),
            key=lambda item: sum(item[1].values()),
            reverse=True,
        )[:10]
    }
    summary["aided_familiarity"] = {
        brand: dict(counts)
        for brand, counts in sorted(
            familiarity_counts.items(),
            key=lambda item: sum(item[1].values()),
            reverse=True,
        )[:10]
    }

    if awareness_counts and not report_only:
        _load_chart_libs()
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        brands, counts = zip(*awareness_counts.most_common(10))
        ax.barh(list(reversed(brands)), list(reversed(counts)), color=COLORS[0], edgecolor="white")
        ax.set_title("Top-of-Mind Brand Awareness", fontsize=14, fontweight="bold")
        ax.set_xlabel("Mentions")
        plt.tight_layout()
        fig.savefig(output_dir / "chart_awareness.png", dpi=DPI, bbox_inches="tight")
        plt.close(fig)

    if consideration_counts and not report_only:
        _load_chart_libs()
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        brands, counts = zip(*consideration_counts.most_common(10))
        ax.barh(list(reversed(brands)), list(reversed(counts)), color=COLORS[1], edgecolor="white")
        ax.set_title("Brand Consideration Set Mentions", fontsize=14, fontweight="bold")
        ax.set_xlabel("Mentions")
        plt.tight_layout()
        fig.savefig(output_dir / "chart_consideration.png", dpi=DPI, bbox_inches="tight")
        plt.close(fig)

    return summary


# ─── Analysis: Price Sensitivity ──────────────────────────────────────────


def analyze_price_test(results: list[dict], df: pd.DataFrame, output_dir: Path, report_only: bool = False):
    """Analyze price sensitivity results."""
    if df.empty:
        print("WARNING: No valid responses to analyze")
        return {"total_respondents": 0}
    summary = {
        "total_respondents": len(df),
        "segments": df["segment"].value_counts().to_dict(),
    }

    if _is_degenerate_crosstab(df):
        _generate_persona_comparison(df, output_dir)

    wtp = _numeric_series(df, "max_wtp")
    wtp_summary = _summarize_numeric(wtp)
    if wtp_summary:
        summary["willingness_to_pay"] = wtp_summary

        if not report_only:
            _load_chart_libs()
            fig, ax = plt.subplots(figsize=FIG_SIZE)
            ax.hist(wtp, bins=min(10, max(4, len(wtp))), color=COLORS[0], edgecolor="white")
            ax.set_title("Willingness to Pay Distribution", fontsize=14, fontweight="bold")
            ax.set_xlabel("Maximum WTP ($)")
            ax.set_ylabel("Count")
            plt.tight_layout()
            fig.savefig(output_dir / "chart_wtp.png", dpi=DPI, bbox_inches="tight")
            plt.close(fig)

    intent_by_price = defaultdict(list)
    for result in results:
        price_map = result.get("responses", {}).get("intent_by_price", {})
        if not isinstance(price_map, dict):
            continue
        for label, intent in price_map.items():
            try:
                numeric_intent = float(intent)
            except (TypeError, ValueError):
                continue
            _, cleaned_label = _parse_price_label(str(label))
            intent_by_price[cleaned_label].append(numeric_intent)

    if intent_by_price:
        summary["mean_intent_by_price"] = {
            label: round(sum(values) / len(values), 2)
            for label, values in sorted(intent_by_price.items(), key=lambda item: _parse_price_label(item[0])[0])
        }

        if not report_only:
            _load_chart_libs()
            fig, ax = plt.subplots(figsize=FIG_SIZE)
            prices = list(summary["mean_intent_by_price"].keys())
            intents = list(summary["mean_intent_by_price"].values())
            ax.plot(prices, intents, "o-", color=COLORS[0], linewidth=2, markersize=8)
            ax.set_title("Purchase Intent by Price Point", fontsize=14, fontweight="bold")
            ax.set_xlabel("Price")
            ax.set_ylabel("Mean Purchase Intent (1-5)")
            ax.set_ylim(0.5, 5.5)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            fig.savefig(output_dir / "chart_demand_curve.png", dpi=DPI, bbox_inches="tight")
            plt.close(fig)

    if "price_quality_preference" in df.columns:
        summary["price_quality_preference"] = df["price_quality_preference"].dropna().value_counts().to_dict()

    competitive = _numeric_series(df, "competitive_reference")
    competitive_summary = _summarize_numeric(competitive)
    if competitive_summary:
        summary["competitive_reference"] = competitive_summary

    return summary


# ─── Analysis: Usage Habits ───────────────────────────────────────────────


def analyze_usage_habits(results: list[dict], df: pd.DataFrame, output_dir: Path, report_only: bool = False):
    """Analyze usage-habits responses with dedicated summary logic."""
    if df.empty:
        print("WARNING: No valid responses to analyze")
        return {"total_respondents": 0}
    summary = {
        "total_respondents": len(df),
        "segments": df["segment"].value_counts().to_dict(),
    }

    if _is_degenerate_crosstab(df):
        _generate_persona_comparison(df, output_dir)

    usage_counts = defaultdict(Counter)
    usage_labels = {}
    factor_scores = defaultdict(list)
    factor_labels = {}
    purchase_channels = Counter()
    current_products = Counter()
    info_sources = Counter()

    for result in results:
        responses = result.get("responses", {})

        usage_frequency = responses.get("usage_frequency", {})
        if isinstance(usage_frequency, dict):
            for occasion, frequency in usage_frequency.items():
                key = _normalize_usage_label(occasion)
                usage_labels.setdefault(key, _display_label(key))
                usage_counts[key][str(frequency).lower()] += 1

        factor_ranking = responses.get("factor_ranking", {})
        if isinstance(factor_ranking, dict):
            for factor, rank in factor_ranking.items():
                try:
                    numeric_rank = float(rank)
                except (TypeError, ValueError):
                    continue
                key = _normalize_key(factor)
                factor_labels.setdefault(key, str(factor))
                factor_scores[key].append(numeric_rank)

        channel = _short_text_label(responses.get("purchase_channel", ""))
        if channel:
            purchase_channels[channel] += 1

        product = _short_text_label(responses.get("current_product", ""))
        if product:
            current_products[product] += 1

        source_list = responses.get("info_sources", [])
        if isinstance(source_list, str):
            source_list = [item.strip() for item in source_list.split(";") if item.strip()]
        for source in source_list:
            label = _short_text_label(source)
            if label:
                info_sources[label] += 1

    summary["usage_frequency_by_occasion"] = {
        usage_labels[key]: dict(counts)
        for key, counts in sorted(usage_counts.items(), key=lambda item: usage_labels.get(item[0], item[0]))
    }
    summary["factor_importance"] = {
        factor_labels[key]: round(sum(values) / len(values), 2)
        for key, values in sorted(factor_scores.items(), key=lambda item: sum(item[1]) / len(item[1]))
    }
    summary["top_purchase_channels"] = _sorted_counter(purchase_channels, 5)
    summary["top_current_products"] = _sorted_counter(current_products, 5)
    summary["top_info_sources"] = _sorted_counter(info_sources, 8)

    if factor_scores and not report_only:
        _load_chart_libs()
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ordered = list(summary["factor_importance"].items())[:7]
        labels = [label for label, _ in ordered]
        values = [value for _, value in ordered]
        ax.barh(list(reversed(labels)), list(reversed(values)), color=COLORS[0], edgecolor="white")
        ax.set_title("Average Factor Importance (Lower = More Important)", fontsize=14, fontweight="bold")
        ax.set_xlabel("Average Rank")
        plt.tight_layout()
        fig.savefig(output_dir / "chart_factor_importance.png", dpi=DPI, bbox_inches="tight")
        plt.close(fig)

    return summary


# ─── Analysis: Generic Survey ─────────────────────────────────────────────


def analyze_generic(results: list[dict], df: pd.DataFrame, output_dir: Path, report_only: bool = False):
    """Basic analysis for custom surveys."""
    if df.empty:
        print("WARNING: No valid responses to analyze")
        return {"total_respondents": 0}
    summary = {
        "total_respondents": len(df),
        "segments": df["segment"].value_counts().to_dict(),
        "response_keys": sorted(
            {
                key
                for result in results
                for key in result.get("responses", {}).keys()
            }
        ),
    }

    if _is_degenerate_crosstab(df):
        _generate_persona_comparison(df, output_dir)

    numeric_summary = {}
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    numeric_cols = [column for column in numeric_cols if column != "age"]
    for column in numeric_cols:
        series = _numeric_series(df, column)
        stats = _summarize_numeric(series)
        if stats:
            numeric_summary[column] = stats
    if numeric_summary:
        summary["numeric_summary"] = numeric_summary

    categorical_summary = {}
    for column in df.columns:
        if column in {"name", "segment", "age", "gender", "occupation"}:
            continue
        series = df[column].dropna()
        if series.empty:
            continue
        if pd.api.types.is_numeric_dtype(series):
            continue
        unique_values = series.astype(str).nunique()
        if unique_values <= 8:
            categorical_summary[column] = series.astype(str).value_counts().head(8).to_dict()
    if categorical_summary:
        summary["categorical_summary"] = categorical_summary

    text_columns = []
    for column in df.columns:
        if column in {"name", "segment", "age", "gender", "occupation"}:
            continue
        series = df[column].dropna().astype(str)
        if series.empty:
            continue
        avg_length = series.map(len).mean()
        if avg_length >= 25:
            text_columns.append(column)
    return summary


# ─── Analysis: Ask ─────────────────────────────────────────────────────────


def analyze_ask(results: list[dict], df: pd.DataFrame, output_dir: Path, report_only: bool = False):
    """Analyze open-question ask results: themes, emotions."""
    if df.empty:
        print("WARNING: No valid responses to analyze")
        return {"total_respondents": 0}
    all_themes: list[str] = []
    all_emotions: list[str] = []

    for result in results:
        responses = result.get("responses", {})
        themes = responses.get("themes", [])
        if isinstance(themes, list):
            all_themes.extend(t.strip().lower() for t in themes if isinstance(t, str) and t.strip())
        emotion = responses.get("emotion", "")
        if isinstance(emotion, str) and emotion.strip():
            all_emotions.append(emotion.strip().lower())

    theme_counts = Counter(all_themes)
    emotion_counts = Counter(all_emotions)

    summary = {
        "total_respondents": len(results),
        "segments": df["segment"].value_counts().to_dict(),
        "top_signals": [{"theme": t, "count": c} for t, c in theme_counts.most_common(10)],
        "emotion_distribution": dict(emotion_counts.most_common()),
    }

    if _is_degenerate_crosstab(df):
        _generate_persona_comparison(df, output_dir)

    return summary


# ─── Report Generation ─────────────────────────────────────────────────────


def _build_panel_overview(results: list[dict], survey_type: str) -> list[str]:
    headers = ["#", "Name", "Age", "Occupation", "Profile"]
    rows = []

    for index, result in enumerate(results, 1):
        responses = result.get("responses", {})
        row = [
            str(index),
            result.get("name", ""),
            str(int(result["age"])) if pd.notna(result.get("age")) else "",
            result.get("occupation", ""),
            result.get("segment", ""),
        ]
        if survey_type == "concept-test":
            headers.append("Preferred") if "Preferred" not in headers else None
            row.append(str(responses.get("preferred_option", "")))
        elif survey_type == "brand-map":
            headers.append("Consideration") if "Consideration" not in headers else None
            row.append(_truncate(", ".join(responses.get("consideration_set", [])[:3]), 40))
        elif survey_type == "price-test":
            headers.extend(["Max WTP"]) if "Max WTP" not in headers else None
            row.append(str(responses.get("max_wtp", "")))
        elif survey_type == "usage-habits":
            headers.append("Current Product") if "Current Product" not in headers else None
            row.append(_truncate(_short_text_label(responses.get("current_product", "")), 30))
        elif survey_type == "ask":
            headers.append("Emotion") if "Emotion" not in headers else None
            row.append(str(responses.get("emotion", "")))
        else:
            first_items = []
            for key, value in list(responses.items())[:2]:
                first_items.append(f"{key}: {_format_value(value, limit=30)}")
            headers.append("Key Response") if "Key Response" not in headers else None
            row.append(_truncate("; ".join(first_items), 40))
        rows.append(row)

    lines = ["## Panel Overview", "| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return lines


def _render_concept_analysis(results: list[dict]) -> list[str]:
    """Concept-centric section: support reasons, who passed, and improvement themes."""
    lines = ["## Concept Analysis", ""]
    total = len(results)

    by_concept: dict[str, list[dict]] = {}
    for r in results:
        opt = r.get("responses", {}).get("preferred_option", "")
        if opt:
            by_concept.setdefault(opt, []).append(r)

    all_improvements: list[tuple[str, str, str]] = []

    for opt in sorted(by_concept.keys()):
        choosers = by_concept[opt]
        passers = [r for r in results if r.get("responses", {}).get("preferred_option", "") != opt]
        lines.append(f"### Concept {opt} — {len(choosers)}/{total} chose this")

        lines.append("**Support reasons:**")
        for r in choosers:
            name = r.get("name", "")
            reasoning = _truncate(r.get("responses", {}).get("reasoning", ""), 600, sentence_aware=True)
            if reasoning:
                lines.append(f"- {name}: {reasoning}")
        lines.append("")

        if passers:
            passer_desc = ", ".join(
                f"{r['name']} (chose {r.get('responses', {}).get('preferred_option', '')})"
                for r in passers
            )
            lines.append(f"**Who passed:** {passer_desc}")
            lines.append("")

        for r in choosers:
            imp = r.get("responses", {}).get("improvement", "")
            if imp:
                all_improvements.append((opt, r.get("name", ""), imp))

    if all_improvements:
        lines.append("### Improvement Themes")
        for opt, name, text in all_improvements:
            lines.append(f"- **Concept {opt}** ({name}): {_truncate(text, 400, sentence_aware=True)}")
        lines.append("")

    return lines


def _render_concept_profiles(results: list[dict]) -> list[str]:
    lines = ["## Profile Analysis"]
    for result in results:
        responses = result.get("responses", {})
        preferred = responses.get("preferred_option", "")
        purchase = responses.get("purchase_likelihood")
        improvement = responses.get("improvement", "")
        detail = _truncate(responses.get("reasoning", ""), 600, sentence_aware=True)
        prefix = f"**{result.get('segment', '')}** ({result.get('name', '')}, {result.get('age', '?')}):"
        if preferred:
            prefix += f" Chose option {preferred}"
            if purchase not in (None, ""):
                prefix += f" with purchase likelihood {purchase}/5."
            else:
                prefix += "."
        lines.append(prefix)
        if detail:
            lines.append(detail)
        if improvement:
            lines.append(f"Suggested improvement: {_truncate(improvement, 300, sentence_aware=True)}")
        lines.append("")
    return lines


def _render_brand_profiles(results: list[dict]) -> list[str]:
    lines = ["## Brand Profiles"]
    for result in results:
        responses = result.get("responses", {})
        awareness = ", ".join(responses.get("unaided_awareness", [])[:3]) or "no clear top-of-mind brands"
        consideration = ", ".join(responses.get("consideration_set", [])[:3]) or "no active consideration set"
        buckets = responses.get("brand_buckets", {}) if isinstance(responses.get("brand_buckets"), dict) else {}
        likes = ", ".join(buckets.get("like", [])[:3])
        associations = responses.get("brand_associations", {}) if isinstance(responses.get("brand_associations"), dict) else {}
        association_line = ""
        if associations:
            brand, text = next(iter(associations.items()))
            association_line = f"{brand}: {_truncate(text, 220)}"
        lines.append(
            f"**{result.get('segment', '')}** ({result.get('name', '')}, {result.get('age', '?')}): "
            f"Top-of-mind brands are {awareness}. Consideration set includes {consideration}."
        )
        if likes:
            lines.append(f"Positive leaning: {likes}.")
        if association_line:
            lines.append(association_line)
        lines.append("")
    return lines


def _render_price_profiles(results: list[dict]) -> list[str]:
    lines = ["## Price Profiles"]
    for result in results:
        responses = result.get("responses", {})
        favorite_price, favorite_intent = _favorite_price_point(responses.get("intent_by_price", {}))
        preference = responses.get("price_quality_preference", "")
        reasoning = _truncate(responses.get("reasoning", ""), 260)
        value_perception = _truncate(responses.get("value_perception", ""), 220)
        lead = (
            f"**{result.get('segment', '')}** ({result.get('name', '')}, {result.get('age', '?')}): "
            f"Max WTP is ${responses.get('max_wtp', 'n/a')}."
        )
        if favorite_price:
            lead += f" Highest stated intent is at {favorite_price} ({favorite_intent}/5)."
        if preference:
            lead += f" Leans {preference} on price-quality tradeoffs."
        lines.append(lead)
        if reasoning:
            lines.append(reasoning)
        if value_perception:
            lines.append(f"Value perception: {value_perception}")
        lines.append("")
    return lines


def _render_usage_profiles(results: list[dict]) -> list[str]:
    lines = ["## Usage Profiles"]
    for result in results:
        responses = result.get("responses", {})
        usage_summary = _summarize_usage_frequency(responses.get("usage_frequency", {}))
        top_factor = _top_ranked_factor(responses.get("factor_ranking", {}))
        current_product = _truncate(responses.get("current_product", ""), 180)
        purchase_channel = _truncate(responses.get("purchase_channel", ""), 160)
        pain_points = _truncate(responses.get("pain_points", ""), 240)
        lines.append(
            f"**{result.get('segment', '')}** ({result.get('name', '')}, {result.get('age', '?')}): "
            f"Current product is {_short_text_label(current_product) or 'not specified'}. "
            f"Most active occasions: {usage_summary}."
        )
        if top_factor:
            lines.append(f"Top decision factor: {top_factor}.")
        if purchase_channel:
            lines.append(f"Purchase channel: {purchase_channel}")
        if pain_points:
            lines.append(f"Pain points: {pain_points}")
        lines.append("")
    return lines


def _render_ask_synthesis(results: list[dict], summary: dict) -> list[str]:
    """Render signal and emotion synthesis section for ask reports."""
    lines = ["## Signal Analysis", ""]

    top_signals = summary.get("top_signals", [])
    if top_signals:
        lines.append("### Top Signals")
        for item in top_signals[:6]:
            count = item["count"]
            total = summary.get("total_respondents", len(results))
            lines.append(f"- **{item['theme']}** — {count}/{total} personas")
        lines.append("")

    emotions = summary.get("emotion_distribution", {})
    if emotions:
        lines.append("### Emotion Landscape")
        for emotion, count in list(emotions.items())[:6]:
            lines.append(f"- {emotion}: {count}")
        lines.append("")

    return lines


def _render_ask_profiles(results: list[dict]) -> list[str]:
    """Render per-persona answer profiles for ask reports."""
    lines = ["## Response Profiles"]
    for result in results:
        responses = result.get("responses", {})
        short_answer = _truncate(responses.get("short_answer", ""), 400, sentence_aware=True)
        emotion = responses.get("emotion", "")
        themes = responses.get("themes", [])
        theme_str = ", ".join(themes[:3]) if isinstance(themes, list) else ""
        profile_label = result.get("segment", "")
        name = result.get("name", "")
        age = result.get("age", "?")
        suffix = f" [{emotion}]" if emotion else ""
        lines.append(
            f"**{profile_label}** ({name}, {age}){suffix}: {short_answer}"
        )
        if theme_str:
            lines.append(f"  *Themes*: {theme_str}")
        lines.append("")
    return lines


def _render_generic_profiles(results: list[dict]) -> list[str]:
    lines = ["## Response Profiles"]
    for result in results:
        responses = result.get("responses", {})
        parts = []
        for key, value in list(responses.items())[:4]:
            parts.append(f"{key}: {_format_value(value, limit=140)}")
        lines.append(
            f"**{result.get('segment', '')}** ({result.get('name', '')}, {result.get('age', '?')}): "
            + "; ".join(parts)
        )
        lines.append("")
    return lines


def _extract_findings(df: pd.DataFrame, summary: dict, survey_type: str) -> list[str]:
    """Extract 3-5 key findings from the summary data."""
    findings = []
    n = len(df)

    if survey_type == "concept-test" and "overall_preference" in summary:
        preferences = summary["overall_preference"]
        if preferences:
            winner = max(preferences, key=preferences.get)
            winner_pct = round(preferences[winner] / n * 100)
            if winner_pct > 60:
                findings.append(f"Concept {winner} is the clear winner with {winner_pct}% preference.")
            elif winner_pct > 40:
                findings.append(f"Concept {winner} leads with {winner_pct}%, but the panel is still split.")
            else:
                findings.append(f"No clear winner emerged; the leading option is {winner} at {winner_pct}%.")
        if "purchase_likelihood" in summary:
            findings.append(f"Average purchase likelihood is {summary['purchase_likelihood']['mean']}/5.")

    elif survey_type == "brand-map":
        awareness = summary.get("unaided_awareness_top10", {})
        if awareness:
            findings.append(
                "Top-of-mind awareness is led by "
                + ", ".join(list(awareness.keys())[:3])
                + "."
            )
        consideration = summary.get("consideration_top10", {})
        if consideration:
            findings.append(
                "Active consideration clusters around "
                + ", ".join(list(consideration.keys())[:3])
                + "."
            )
        for brand, counts in summary.get("brand_sentiment", {}).items():
            if counts.get("like", 0) and counts.get("dislike", 0):
                findings.append(
                    f"{brand} is polarizing: {counts.get('like', 0)} positive mentions vs {counts.get('dislike', 0)} negative mentions."
                )
                break

    elif survey_type == "price-test":
        wtp = summary.get("willingness_to_pay")
        if wtp:
            findings.append(f"Mean WTP is ${wtp['mean']} with a median of ${wtp['median']}.")
        intent = summary.get("mean_intent_by_price", {})
        if intent:
            best_price = max(intent, key=intent.get)
            worst_price = min(intent, key=intent.get)
            findings.append(f"Purchase intent peaks at {best_price} and is weakest at {worst_price}.")
        preference = summary.get("price_quality_preference", {})
        if preference:
            leader = max(preference, key=preference.get)
            findings.append(f"The dominant price-quality stance is `{leader}`.")

    elif survey_type == "usage-habits":
        factor_importance = summary.get("factor_importance", {})
        if factor_importance:
            top_factors = list(factor_importance.keys())[:2]
            findings.append("Top decision factors are " + " and ".join(top_factors) + ".")
        channels = summary.get("top_purchase_channels", {})
        if channels:
            findings.append(
                "Purchase happens primarily through "
                + ", ".join(list(channels.keys())[:3])
                + "."
            )
        occasions = summary.get("usage_frequency_by_occasion", {})
        if occasions:
            best = max(
                occasions.items(),
                key=lambda item: item[1].get("daily", 0),
            )
            findings.append(f"The strongest daily usage occasion is {best[0]}.")

    elif survey_type == "survey":
        numeric_summary = summary.get("numeric_summary", {})
        if numeric_summary:
            field, stats = next(iter(numeric_summary.items()))
            findings.append(f"{field} averages {stats['mean']} across the panel.")
        categorical = summary.get("categorical_summary", {})
        if categorical:
            field, counts = next(iter(categorical.items()))
            leading = max(counts, key=counts.get)
            findings.append(f"The most common response on {field} is `{leading}`.")

    elif survey_type == "ask":
        top_signals = summary.get("top_signals", [])
        if top_signals:
            signal_labels = ", ".join(item["theme"] for item in top_signals[:3])
            findings.append(f"Recurring signals: {signal_labels}.")
        emotions = summary.get("emotion_distribution", {})
        if emotions:
            dominant = max(emotions, key=emotions.get)
            findings.append(f"Dominant emotional tone is `{dominant}` ({emotions[dominant]}/{n} personas).")

    return findings[:5]


def resolve_report_date(output_dir: Path) -> str:
    """Prefer the original run timestamp when metadata is available."""
    metadata = _load_run_metadata(output_dir)
    if metadata:
        timestamp = metadata.get("timestamp")
        if timestamp:
            return str(timestamp).split("T", 1)[0]
    return date.today().isoformat()


def _load_run_metadata(output_dir: Path) -> dict | None:
    metadata_path = output_dir / "run_metadata.json"
    if not metadata_path.exists():
        return None
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _read_topic_from_config(config_path: Path) -> str | None:
    if not config_path.exists():
        return None
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    topic = config.get("topic")
    return str(topic).strip() if topic else None


def _read_user_question_from_config(config_path: Path) -> str | None:
    if not config_path.exists():
        return None
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    uq = config.get("variables", {}).get("user_question")
    return str(uq).strip() if uq else None


def _resolve_topic(output_dir: Path, df: pd.DataFrame, survey_type: str | None = None) -> str:
    """Resolve report topic from metadata, config, or segment labels."""
    metadata = _load_run_metadata(output_dir)
    if metadata:
        if survey_type == "ask":
            user_question = metadata.get("user_question")
            if user_question:
                return str(user_question).strip()
            # Fallback: read user_question from config file before using generic topic
            config_file = metadata.get("config_file")
            if config_file:
                config_path = Path(str(config_file))
                if not config_path.is_absolute():
                    config_path = Path.cwd() / config_path
                uq = _read_user_question_from_config(config_path)
                if uq:
                    return uq
        topic = metadata.get("topic")
        if topic:
            return str(topic)

        config_file = metadata.get("config_file")
        if config_file:
            config_path = Path(str(config_file))
            if not config_path.is_absolute():
                config_path = Path.cwd() / config_path
            topic = _read_topic_from_config(config_path)
            if topic:
                return topic

    for candidate in [output_dir / "config.json", output_dir.parent / "config.json",
                      output_dir / "ask-config.json"]:
        if survey_type == "ask":
            uq = _read_user_question_from_config(candidate)
            if uq:
                return uq
        topic = _read_topic_from_config(candidate)
        if topic:
            return topic

    segments = list(df["segment"].unique())[:3] if not df.empty else []
    return ", ".join(segments) if segments else "Survey"


def generate_markdown_report(
    results: list[dict],
    df: pd.DataFrame,
    summary: dict,
    survey_type: str,
    output_dir: Path,
    report_date: str | None = None,
    topic: str | None = None,
) -> str:
    """Generate a one-pager markdown report from survey results."""
    today = report_date or resolve_report_date(output_dir)
    survey_label = survey_type.replace("-", " ").title()
    if not topic:
        topic = _resolve_topic(output_dir, df, survey_type=survey_type)
    if survey_type == "ask":
        lines = [
            f"# Ask: {topic}",
            "",
            f"**Date**: {today} | **Panel**: {len(results)} personas",
            "",
        ]
    else:
        lines = [
            f"# {survey_label}: {topic} — Virtual Research Report",
            "",
            f"**Date**: {today} | **Panel**: {len(results)} personas",
            "",
        ]

    lines.extend(_build_panel_overview(results, survey_type))

    lines.append("## Key Findings")
    for index, finding in enumerate(_extract_findings(df, summary, survey_type), 1):
        lines.append(f"{index}. {finding}")
    lines.append("")

    if survey_type == "concept-test":
        lines.extend(_render_concept_analysis(results))
        lines.extend(_render_concept_profiles(results))
    elif survey_type == "brand-map":
        lines.extend(_render_brand_profiles(results))
    elif survey_type == "price-test":
        lines.extend(_render_price_profiles(results))
    elif survey_type == "usage-habits":
        lines.extend(_render_usage_profiles(results))
    elif survey_type == "ask":
        lines.extend(_render_ask_synthesis(results, summary))
        lines.extend(_render_ask_profiles(results))
    else:
        lines.extend(_render_generic_profiles(results))

    lines.append("## Notable Verbatims")
    verbatims = _collect_verbatims(results, survey_type)
    if verbatims:
        for text, name, age, occupation in verbatims:
            lines.append(f'> "{_truncate(text, 600, sentence_aware=True)}" — {name}, {age}, {occupation}')
            lines.append("")
    else:
        lines.append("No verbatim text was captured in this run.")
        lines.append("")

    lines.append("## Caveats")
    lines.append(f"- Virtual panel of {len(results)} personas; directional only")
    lines.append("- Not statistically representative; use for hypothesis generation")
    lines.append("- AI-generated responses may exhibit positivity bias")
    lines.append("")

    report = "\n".join(lines)
    report_path = output_dir / "report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Saved report: {report_path}")
    return report


# ─── LLM Report Generation ────────────────────────────────────────────────

GENERIC_REPORT_SYSTEM_PROMPT = """\
You are a consumer research analyst writing a one-pager report from virtual persona survey results.

## Report Structure

Write a markdown report with these sections:

# [Survey Type]: [Topic] — Virtual Research Report

**Date**: {date} | **Panel**: {n} personas

## Panel Overview
[Table: #, Name, Age, Occupation, Profile, and any survey-specific columns like Preferred Option or Max WTP]

## Key Findings
[3-5 insights focusing on PATTERNS, SPLITS, and SURPRISES across the panel.
DO NOT just summarize each persona — synthesize across them.
Highlight: which personas agree/disagree, what drives the split, any unexpected choices.]

## Profile Analysis
[One paragraph per persona. For each, explain:
- What they chose and why (grounded in their personality/background)
- How their Big Five traits or life circumstances influenced the response
- What makes their perspective unique vs. the rest of the panel
Write in third person, not persona voice.]

## Notable Verbatims
[Pick 2-3 direct quotes from the most relevant free-text fields.
Include full quotes, do not truncate.
Format: > "quote" — Name, Age, Occupation]

## Caveats
- Virtual panel of {n} personas; directional only
- Not statistically representative; use for hypothesis generation
- AI-generated responses may exhibit positivity bias

## Rules
- Write for a marketing manager audience — insightful but accessible
- Use data from the summary statistics to support findings with numbers
- DO NOT invent data or statistics not present in the results
- Total length: 400-800 words (excluding panel table and verbatims)
"""


ASK_REPORT_SYSTEM_PROMPT = """\
You are a consumer research analyst writing a qualitative synthesis report from an open-ended
"ask" study where a virtual persona panel answered a single research question.

Your job is cross-persona SYNTHESIS, not per-persona summarization. A reader should be able to
skim this and understand what the panel collectively said, where they agreed, and where the
interesting splits live.

## Report Structure

Use this exact markdown skeleton. All sections are required.

# Ask: [Topic]

**Date**: {date} | **Panel**: {n} personas

## Panel Overview
[Markdown table: #, Name, Age, Occupation, Profile, Emotion]

## Direct Answer
[2-3 sentences. Summarize what the panel said overall — the dominant response pattern —
WITHOUT attributing to any single persona. Lead with the most important takeaway.]

## Key Findings
1. [First synthesized insight — a pattern, split, or surprise]
2. [Second insight]
3. [Third insight]
[Include 3-5 findings. Every finding must be cross-persona; no per-persona summary sentences.
No-occurrence observations are valuable ("0 positive emotions across 10 responses").
Absolutely NO filler like "Panel size is N personas" or "Panel covers N segments".]

## Where They Agreed
[What most or all personas said in common. 1-3 sentences. Focus on the shared belief/complaint/
experience, not on listing names.]

## Where They Differed
[Notable splits — by age, segment, personality, circumstance, emotional register, engagement level.
2-4 sentences. Name the axis of difference explicitly.]

## Notable Verbatims
[3-4 direct quotes from `reasoning` fields. Use FULL SENTENCES — do NOT truncate mid-sentence.
Pick quotes that deliver the panel's feeling, not generic statements.
Format: > "quote" — Name, Age, Occupation]

## Top Signals
[Cluster semantically-similar themes before counting. For example, "greenwashing and false claims",
"greenwashing with no accountability", and "greenwashing by brands" are ONE cluster mentioned by 3
personas — not three separate signals of 1 each. Output as:
- **cluster label** (N) — short gloss
List 3-7 clusters ordered by count.]

## Emotion Distribution
[Raw emotion counts with a one-line observation. Call out striking patterns:
three-way ties, skewed-negative panels, absent positive emotions, single outlier emotions.
Format: emotion (N), emotion (N), ...  followed by a 1-sentence takeaway.]

## Caveats
- Virtual panel of {n} personas; directional only
- Not statistically representative; use for hypothesis generation
- AI-generated responses may exhibit positivity bias

## Rules
- Write for a marketing / consumer-insights audience.
- Synthesis over summary: no "Profile Analysis" section with one paragraph per persona.
- Do NOT invent data not present in results.
- Do NOT use mechanical filler findings.
- Do NOT truncate verbatim quotes mid-sentence; prefer shorter quotes to mid-sentence cuts.
- When in doubt, ground every claim in specific personas or `reasoning` snippets.
"""


CONCEPT_TEST_REPORT_SYSTEM_PROMPT = """\
You are a consumer research analyst writing a concept-test synthesis report from a virtual persona
panel that evaluated multiple product concepts (typically A/B/C).

Your job is cross-persona, cross-concept SYNTHESIS. A reader should be able to decide:
(1) which concept leads, (2) for whom, (3) what to fix, and (4) whether to move forward.

## Report Structure

Use this exact markdown skeleton. All sections are required.

# Concept Test: [Topic] — Virtual Research Report

**Date**: {date} | **Panel**: {n} personas

## Panel Overview
[Markdown table: #, Name, Age, Occupation, Profile, Preferred, Purchase Likelihood]

## Preference Verdict
[2-3 sentences. State the leader, the margin, and the confidence. Use precise language:
"Clear winner" (>60% preference), "Narrow lead" (40-60%), "No winner; tied" (ties),
"Fragmented" (every concept below 40% with multiple near-ties). Include raw counts.]

## Key Findings
1. [Cross-persona insight — who preferred what and why; not a per-persona summary]
2. [Second insight]
3. [Third insight]
[3-5 findings. Absolutely NO filler like "Panel size is N personas" or "Panel covers N segments".]

## Segment / Profile Splits
[Who picked what. Organize by segment/profile, not by persona. For each segment with a notable
pattern, state: segment → preference → the shared reason. 3-6 lines.]

## Purchase-Intent Drivers
[What moved `purchase_likelihood` up or down across the panel. Look for cross-concept patterns:
ingredient transparency, price, claim credibility, packaging, etc. Cite specific factors that
personas explicitly credited. 2-4 sentences.]

## Per-Concept Strengths and Weaknesses
[For each concept that received at least one vote or meaningful reaction:

### Concept [X] — N/total chose this
**Strengths (cross-persona):** What multiple personas liked. Synthesize, do not per-chooser-dump.
**Weaknesses (cross-persona):** What passers (and sometimes choosers) flagged as issues.

Write in third person. Reference 2-3 personas by name inline where it adds credibility, but
do NOT list every chooser's verbatim reasoning — that is noise, not analysis.]

## Improvement Theme Clusters
[Cluster semantically-similar `improvement` suggestions. Example: "disclose ceramide percentages",
"list niacinamide %", "show active concentrations" are ONE cluster about ingredient transparency.
Output as:
- **Cluster label** (N mentions across Concepts X, Y) — one-line gloss with 1-2 persona attributions.
List 3-6 clusters ordered by cross-concept relevance.]

## Notable Verbatims
[3-4 direct quotes from `reasoning` fields. FULL SENTENCES — do NOT truncate mid-sentence.
Pick quotes that illuminate the split or the verdict, not generic praise.
Format: > "quote" — Name, Age, Occupation]

## Caveats
- Virtual panel of {n} personas; directional only
- Not statistically representative; use for hypothesis generation
- AI-generated responses may exhibit positivity bias

## Rules
- Synthesis over summary. NO "Profile Analysis" section with one paragraph per persona.
- NO per-concept "support reasons" list that just repeats each chooser's reasoning verbatim.
- Cluster improvement suggestions; do not dump them.
- Do NOT invent data not present in results.
- Do NOT truncate verbatim quotes mid-sentence.
- When segments are small (N=1 per segment), state that explicitly rather than over-generalize.
"""


def _select_report_system_prompt(survey_type: str) -> str:
    """Pick the survey-type-specific LLM report prompt; fall back to generic."""
    return {
        "ask": ASK_REPORT_SYSTEM_PROMPT,
        "concept-test": CONCEPT_TEST_REPORT_SYSTEM_PROMPT,
    }.get(survey_type, GENERIC_REPORT_SYSTEM_PROMPT)


REPORT_SYSTEM_PROMPT = GENERIC_REPORT_SYSTEM_PROMPT


def generate_llm_report(
    results: list[dict],
    df: pd.DataFrame,
    summary: dict,
    survey_type: str,
    output_dir: Path,
    *,
    backend: str,
    model: str | None = None,
    report_date: str | None = None,
    topic: str | None = None,
) -> str:
    """Generate a narrative one-pager report using the resolved LLM backend."""
    system_prompt = _select_report_system_prompt(survey_type).format(
        date=report_date or resolve_report_date(output_dir),
        n=len(results),
    )

    resolved_topic = topic or _resolve_topic(output_dir, df, survey_type=survey_type)

    user_message = (
        f"Survey type: {survey_type}\n"
        f"Topic: {resolved_topic}\n\n"
        f"## Results Data ({len(results)} personas)\n\n"
        f"{json.dumps(results, indent=2, ensure_ascii=False)}\n\n"
        f"## Summary Statistics\n\n"
        f"{json.dumps(summary, indent=2, ensure_ascii=False)}\n\n"
        f"Generate the one-pager report now. Return only the markdown report content."
    )

    try:
        completion = run_text_completion(
            backend=backend,
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            cwd=output_dir,
        )
    except (FileNotFoundError, RuntimeError, TimeoutError, json.JSONDecodeError) as error:
        print(f"WARNING: LLM report generation failed: {error}", file=sys.stderr)
        print("Falling back to Python report generation...", file=sys.stderr)
        fallback_report = generate_markdown_report(
            results,
            df,
            summary,
            survey_type,
            output_dir,
            report_date=report_date,
            topic=resolved_topic,
        )
        fallback_note = (
            "> **Note**: This report was generated using the Python template engine "
            f"(LLM report generation failed: {error}). "
            "Re-run with `--report-llm` to retry.\n\n"
        )
        return fallback_note + fallback_report

    report_text = completion["text"]

    report_text = re.sub(r"^```(?:markdown)?\s*\n", "", report_text)
    report_text = re.sub(r"\n```\s*$", "", report_text)

    report_path = output_dir / "report.md"
    report_path.write_text(report_text, encoding="utf-8")
    print(f"Saved LLM report: {report_path}")
    return report_text


# ─── Main ──────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Persona Research Survey Analysis")
    parser.add_argument("--input", required=True, help="Path to results.json")
    parser.add_argument(
        "--survey-type",
        default="concept-test",
        choices=["concept-test", "brand-map", "price-test", "usage-habits", "survey", "ask"],
        help="Type of survey to analyze",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Skip chart generation, produce report.md only",
    )
    parser.add_argument(
        "--topic",
        help="Research topic for report title (auto-detected from config/manifest if omitted)",
    )
    parser.add_argument(
        "--report-llm",
        action="store_true",
        help="Generate report using the selected LLM backend for narrative synthesis",
    )
    parser.add_argument(
        "--model",
        help="Model override for the selected report backend",
    )
    parser.add_argument(
        "--backend",
        choices=BACKEND_CHOICES,
        default="auto",
        help="Default execution backend (`auto` infers from runtime markers/CLI availability)",
    )
    parser.add_argument(
        "--report-backend",
        choices=REPORT_BACKEND_CHOICES,
        default="same",
        help="Backend for LLM report generation (`same` uses --backend)",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    output_dir = input_path.parent
    resolved_backend = None
    resolved_report_backend = "python"
    resolved_report_model = None
    if args.report_llm:
        resolved_backend = resolve_backend(args.backend)
        resolved_report_backend = resolve_report_backend(
            args.report_backend,
            resolved_backend,
        )
        if resolved_report_backend != "python":
            resolved_report_model = resolve_model(args.model, resolved_report_backend)

    print(f"Loading results from: {input_path}")
    raw_results = load_results(input_path)
    results = normalize_results(raw_results)
    print(f"Loaded {len(results)} responses")
    if args.report_llm:
        print(
            "LLM report backend: "
            f"{resolved_report_backend} | model: {format_model_label(resolved_report_model)}"
        )

    df = flatten_responses(results)
    csv_path = output_dir / "results.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved flat CSV: {csv_path}")

    analyzers = {
        "concept-test": analyze_concept_test,
        "brand-map": analyze_brand_map,
        "price-test": analyze_price_test,
        "usage-habits": analyze_usage_habits,
        "survey": analyze_generic,
        "ask": analyze_ask,
    }
    analyzer = analyzers[args.survey_type]
    summary = analyzer(results, df, output_dir, report_only=args.report_only)

    summary_path = output_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved summary: {summary_path}")

    report_date = resolve_report_date(output_dir)
    if args.report_llm and resolved_report_backend != "python":
        generate_llm_report(
            results,
            df,
            summary,
            args.survey_type,
            output_dir,
            backend=resolved_report_backend,
            model=resolved_report_model,
            report_date=report_date,
            topic=args.topic,
        )
    else:
        generate_markdown_report(
            results,
            df,
            summary,
            args.survey_type,
            output_dir,
            report_date=report_date,
            topic=args.topic,
        )

    print("\n" + "=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("=" * 60)
    print(f"\nOutput files in: {output_dir}")
    for path in sorted(output_dir.glob("*")):
        if path.name != "results.json":
            print(f"  {path.name}")


if __name__ == "__main__":
    main()
