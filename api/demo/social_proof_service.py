"""
委任型（Delegator）向け：購入者レビュー・有識者の声の取得（Neo4j + フォールバック）
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent / "config" / "delegator-social-proof.json"
)

_AGE_LABELS = {
    "20s": "20代",
    "30s": "30代",
    "40s": "40代",
    "50s": "50代",
    "60s": "60代",
    "70s": "70代以上",
}

_GENDER_LABELS = {"male": "男性", "female": "女性", "M": "男性", "F": "女性"}


def _load_config() -> dict[str, Any]:
    if not _CONFIG_PATH.exists():
        return {}
    return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))


def _truncate(text: str, max_len: int = 140) -> str:
    t = (text or "").strip().replace("\n", " ")
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _consumer_meta(record: dict[str, Any]) -> str:
    parts: list[str] = []
    age = record.get("age_group") or ""
    if age:
        parts.append(_AGE_LABELS.get(age, age))
    gender = record.get("gender") or ""
    if gender:
        parts.append(_GENDER_LABELS.get(gender, gender))
    loc = record.get("location") or ""
    if loc:
        parts.append(loc)
    fs = record.get("family_size")
    if fs:
        parts.append(f"家族{fs}人")
    return "・".join(parts) if parts else "購入者"


def _fetch_reviews_from_neo4j(
    vehicle_name: str,
    need_names: Optional[list[str]],
    limit: int,
) -> list[dict[str, Any]]:
    try:
        from engine.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        try:
            with engine.driver.session() as session:
                if need_names:
                    rows = session.run(
                        """
                        MATCH (vo:VehicleOwnership {is_current: true})-[:OF_MODEL]->
                              (v:VehicleModel {name: $vname})
                        MATCH (c:Consumer)-[:OWNED]->(vo)
                        MATCH (vo)-[ri:RESULTED_IN]->(o:Outcome)
                        WHERE size(o.name) > 15
                          AND (o.label = 'Satisfied' OR ri.score >= 4)
                        OPTIONAL MATCH (c)-[:HAS_NEED]->(n:Need)
                        WHERE n.name IN $needs
                        WITH c, o, ri, count(n) AS need_hits
                        ORDER BY need_hits DESC, ri.score DESC
                        RETURN o.name AS quote,
                               c.age_group AS age_group,
                               c.gender AS gender,
                               c.location AS location,
                               c.family_size AS family_size,
                               ri.score AS score
                        LIMIT $lim
                        """,
                        vname=vehicle_name,
                        needs=need_names[:8],
                        lim=limit,
                    )
                else:
                    rows = session.run(
                        """
                        MATCH (vo:VehicleOwnership {is_current: true})-[:OF_MODEL]->
                              (v:VehicleModel {name: $vname})
                        MATCH (c:Consumer)-[:OWNED]->(vo)
                        MATCH (vo)-[ri:RESULTED_IN]->(o:Outcome)
                        WHERE size(o.name) > 15
                          AND (o.label = 'Satisfied' OR ri.score >= 4)
                        RETURN o.name AS quote,
                               c.age_group AS age_group,
                               c.gender AS gender,
                               c.location AS location,
                               c.family_size AS family_size,
                               ri.score AS score
                        ORDER BY ri.score DESC
                        LIMIT $lim
                        """,
                        vname=vehicle_name,
                        lim=limit,
                    )
                out: list[dict[str, Any]] = []
                for r in rows:
                    quote = _truncate(r.get("quote") or "")
                    if len(quote) < 12:
                        continue
                    out.append(
                        {
                            "quote": quote,
                            "meta": _consumer_meta(dict(r)),
                            "rating": int(r.get("score") or 5),
                            "model": vehicle_name,
                            "source": "kg_outcome",
                        }
                    )
                return out
        finally:
            engine.close()
    except Exception:
        return []
    return []


def _fallback_reviews(cfg: dict[str, Any], vehicle_name: str, limit: int) -> list[dict[str, Any]]:
    by_vehicle: dict = cfg.get("vehicle_reviews", {})
    items = list(by_vehicle.get(vehicle_name) or by_vehicle.get("_default") or [])
    out: list[dict[str, Any]] = []
    for item in items[:limit]:
        out.append(
            {
                "quote": item.get("quote", ""),
                "meta": item.get("meta", "購入者"),
                "rating": int(item.get("rating") or 5),
                "model": vehicle_name,
                "source": "fallback",
            }
        )
    return out


def _fallback_experts(
    cfg: dict[str, Any],
    vehicle_name: str,
    capabilities: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    by_vehicle: dict = cfg.get("vehicle_experts", {})
    cap_map: dict = cfg.get("expert_by_capability", {})
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    for cap in capabilities:
        if len(out) >= limit:
            break
        entry = cap_map.get(cap)
        if not entry or entry.get("source") in seen:
            continue
        seen.add(entry["source"])
        out.append(
            {
                "source": entry.get("source", ""),
                "title": entry.get("title", ""),
                "quote": entry.get("quote", "").replace("{model}", vehicle_name),
                "topic": cap,
                "source_type": "capability",
            }
        )

    for item in by_vehicle.get(vehicle_name) or []:
        if len(out) >= limit:
            break
        key = item.get("source", "")
        if key in seen:
            continue
        seen.add(key)
        out.append({**item, "source_type": "vehicle"})

    for item in by_vehicle.get("_default") or []:
        if len(out) >= limit:
            break
        key = item.get("source", "")
        if key in seen:
            continue
        seen.add(key)
        out.append({**item, "source_type": "default"})

    return out[:limit]


def fetch_delegator_social_proof(
    session: dict[str, Any],
    vehicle_name: str,
    *,
    review_limit: int = 4,
    expert_limit: int = 3,
) -> dict[str, Any]:
    """委任型UI用：購入者レビュー + 有識者・専門家の声"""
    profile_data = session.get("profile") or {}
    need_names: list[str] = list(profile_data.get("mapped_needs") or [])[:8]
    capabilities: list[str] = list(profile_data.get("mapped_capabilities") or [])[:5]

    reviews = _fetch_reviews_from_neo4j(vehicle_name, need_names or None, review_limit)
    cfg = _load_config()
    if len(reviews) < 2:
        fb = _fallback_reviews(cfg, vehicle_name, review_limit)
        seen_quotes = {r["quote"] for r in reviews}
        for item in fb:
            if item["quote"] not in seen_quotes and len(reviews) < review_limit:
                reviews.append(item)
                seen_quotes.add(item["quote"])

    experts = _fallback_experts(cfg, vehicle_name, capabilities, expert_limit)

    return {
        "buyer_reviews": reviews,
        "expert_voices": experts,
        "review_count_label": f"{len(reviews)}件の購入者の声",
        "expert_count_label": f"{len(experts)}件の専門家・有識者コメント",
    }

