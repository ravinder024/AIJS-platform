from __future__ import annotations

import os
import re
import smtplib
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from collectors import collect_from_source
from db import SessionLocal, engine
from models import (
    AgentRunArtifact,
    AgentState,
    Base,
    Feedback,
    Job,
    Run,
    SearchProfile,
    SourceHealth,
)
from ranking import compute_feedback_bias, score_job, score_job_explained


DEFAULT_SOURCES = [
    "linkedin_jobs",
    "remoteok",
    "indeed",
    "company_site:https://boards.greenhouse.io",
    "company_site:https://jobs.lever.co",
    "company_site:https://www.workday.com/en-us/company/careers.html",
]


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def _profile_to_dict(profile: SearchProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "name": profile.name,
        "role_query": profile.role_query,
        "location": profile.location,
        "target_locations": profile.target_locations or [],
        "role_queries": profile.role_queries or [],
        "work_settings": profile.work_settings or [],
        "company_size_min": profile.company_size_min,
        "company_size_max": profile.company_size_max,
        "include_companies": profile.include_companies or [],
        "exclude_companies": profile.exclude_companies or [],
        "industries": profile.industries or [],
        "recently_funded_only": bool(profile.recently_funded_only),
        "job_types": profile.job_types or [],
        "experience_min_years": profile.experience_min_years,
        "experience_max_years": profile.experience_max_years,
        "min_glassdoor_rating": profile.min_glassdoor_rating,
        "salary_min": profile.salary_min,
        "salary_max": profile.salary_max,
        "posted_within_hours": profile.posted_within_hours,
        "include_keywords": profile.include_keywords or [],
        "exclude_keywords": profile.exclude_keywords or [],
        "sources": profile.sources or [],
    }


def _safe_parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _feedback_for_profile(db: Session, profile_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        select(Feedback, Job.company_name)
        .join(Job, Job.id == Feedback.job_id)
        .where(Feedback.profile_id == profile_id)
        .order_by(desc(Feedback.created_at))
        .limit(2000)
    ).all()

    feedback_rows = []
    for fb, company_name in rows:
        feedback_rows.append(
            {
                "vote": fb.vote,
                "reason_tags": fb.reason_tags or [],
                "company_name": company_name,
            }
        )
    return feedback_rows


def _get_or_create_agent_state(db: Session, profile_id: int) -> AgentState:
    state = db.execute(select(AgentState).where(AgentState.profile_id == profile_id)).scalar_one_or_none()
    if state:
        return state

    state = AgentState(
        profile_id=profile_id,
        learned_source_weights={},
        learned_keyword_weights={},
        paused_sources={},
        target_sources_per_run=6,
        run_count=0,
        last_plan={},
        last_eval={},
        last_adapt={},
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _extract_years(text: str) -> float | None:
    if not text:
        return None
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", text.lower())
    if not matches:
        return None
    try:
        return max(float(v) for v in matches)
    except ValueError:
        return None


def _contains_any(text: str, values: list[str]) -> bool:
    t = (text or "").lower()
    return any(v.lower() in t for v in values)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    for candidate in [s, s.replace("Z", "+00:00")]:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass
    try:
        return parsedate_to_datetime(s)
    except Exception:
        return None


def _job_matches_profile_criteria(job: dict[str, Any], profile: dict[str, Any]) -> bool:
    title = (job.get("title") or "").lower()
    company = (job.get("company_name") or "").lower()
    location = (job.get("location") or "").lower()
    description = (job.get("description") or "").lower()
    remote_type = (job.get("remote_type") or "").lower()
    employment_type = (job.get("employment_type") or "").lower()
    industry = (job.get("industry") or "").lower()
    blob = " ".join([title, company, location, description, remote_type, employment_type, industry])

    roles = profile.get("role_queries") or []
    role_query = (profile.get("role_query") or "").strip()
    if role_query:
        roles = [*roles, role_query]
    roles = [r.lower() for r in roles if str(r).strip()]
    if roles and not any(r in blob for r in roles):
        return False

    target_locations = [x.lower() for x in (profile.get("target_locations") or []) if str(x).strip()]
    location_fallback = (profile.get("location") or "").strip().lower()
    if not target_locations and location_fallback:
        target_locations = [location_fallback]
    if target_locations and not any(loc in location or (loc == "remote" and "remote" in blob) for loc in target_locations):
        return False

    work_settings = [x.lower() for x in (profile.get("work_settings") or []) if str(x).strip()]
    if work_settings:
        ws_blob = " ".join([remote_type, description, title, location]).lower()
        normalized_ws = {"on-site" if w == "onsite" else w for w in work_settings}
        if not any(w in ws_blob for w in normalized_ws):
            return False

    exclude_companies = [c.lower() for c in (profile.get("exclude_companies") or []) if str(c).strip()]
    if exclude_companies and any(c in company for c in exclude_companies):
        return False

    include_companies = [c.lower() for c in (profile.get("include_companies") or []) if str(c).strip()]
    if include_companies and not any(c in company for c in include_companies):
        return False

    industries = [x.lower() for x in (profile.get("industries") or []) if str(x).strip()]
    if industries and not any(i in blob for i in industries):
        return False

    job_types = [x.lower() for x in (profile.get("job_types") or []) if str(x).strip()]
    if job_types:
        jt_blob = " ".join([employment_type, description, title]).lower()
        if not any(jt in jt_blob for jt in job_types):
            return False

    salary_floor = _to_float(profile.get("salary_min"))
    salary_ceiling = _to_float(profile.get("salary_max"))
    job_salary_min = _to_float(job.get("salary_min"))
    job_salary_max = _to_float(job.get("salary_max"))
    if salary_floor is not None and job_salary_max is not None and job_salary_max < salary_floor:
        return False
    if salary_ceiling is not None and job_salary_min is not None and job_salary_min > salary_ceiling:
        return False

    posted_within_hours = _to_float(profile.get("posted_within_hours"))
    if posted_within_hours is not None:
        posted_dt = (
            _parse_dt(job.get("posted_at"))
            or _parse_dt((job.get("raw_payload") or {}).get("posted_at"))
            or _parse_dt((job.get("raw_payload") or {}).get("date"))
            or _parse_dt((job.get("raw_payload") or {}).get("created_at"))
            or _parse_dt((job.get("raw_payload") or {}).get("published_at"))
        )
        if not posted_dt:
            return False
        age_hours = (datetime.utcnow().replace(tzinfo=None) - posted_dt.replace(tzinfo=None)).total_seconds() / 3600
        if age_hours < 0 or age_hours > posted_within_hours:
            return False

    exp_min = _to_float(profile.get("experience_min_years"))
    exp_max = _to_float(profile.get("experience_max_years"))
    job_exp_years = _extract_years(blob)
    if exp_min is not None and job_exp_years is not None and job_exp_years < exp_min:
        return False
    if exp_max is not None and job_exp_years is not None and job_exp_years > exp_max:
        return False

    if _to_bool(profile.get("recently_funded_only")):
        if not _contains_any(blob, ["series a", "series b", "seed", "recently funded", "funding", "raised"]):
            return False

    min_rating = _to_float(profile.get("min_glassdoor_rating"))
    if min_rating is not None:
        job_rating = _to_float(job.get("glassdoor_rating")) or _to_float((job.get("raw_payload") or {}).get("glassdoor_rating"))
        if job_rating is not None and job_rating < min_rating:
            return False

    company_size_min = _to_int(profile.get("company_size_min"))
    company_size_max = _to_int(profile.get("company_size_max"))
    if company_size_min is not None or company_size_max is not None:
        job_size = _to_int(job.get("company_size")) or _to_int((job.get("raw_payload") or {}).get("company_size"))
        if job_size is not None:
            if company_size_min is not None and job_size < company_size_min:
                return False
            if company_size_max is not None and job_size > company_size_max:
                return False

    return True


def create_profile(payload: dict[str, Any]) -> SearchProfile:
    with SessionLocal() as db:
        sources = payload.get("sources") or DEFAULT_SOURCES
        profile = SearchProfile(
            name=payload["name"],
            role_query=payload["role_query"],
            location=payload.get("location", "Remote"),
            target_locations=payload.get("target_locations", []),
            role_queries=payload.get("role_queries", []),
            work_settings=payload.get("work_settings", []),
            company_size_min=_to_int(payload.get("company_size_min")),
            company_size_max=_to_int(payload.get("company_size_max")),
            include_companies=payload.get("include_companies", []),
            exclude_companies=payload.get("exclude_companies", []),
            industries=payload.get("industries", []),
            recently_funded_only=_to_bool(payload.get("recently_funded_only")),
            job_types=payload.get("job_types", []),
            experience_min_years=_to_float(payload.get("experience_min_years")),
            experience_max_years=_to_float(payload.get("experience_max_years")),
            min_glassdoor_rating=_to_float(payload.get("min_glassdoor_rating")),
            salary_min=_to_float(payload.get("salary_min")),
            salary_max=_to_float(payload.get("salary_max")),
            posted_within_hours=_to_float(payload.get("posted_within_hours")),
            include_keywords=payload.get("include_keywords", []),
            exclude_keywords=payload.get("exclude_keywords", []),
            sources=sources,
            is_active=payload.get("is_active", True),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        _get_or_create_agent_state(db, profile.id)
        return profile


def list_profiles() -> list[SearchProfile]:
    with SessionLocal() as db:
        return db.execute(select(SearchProfile).order_by(SearchProfile.id)).scalars().all()


def get_profile(profile_id: int) -> SearchProfile | None:
    with SessionLocal() as db:
        return db.get(SearchProfile, profile_id)


def _update_source_health(db: Session, source: str, collected_count: int, blocked: bool = False) -> None:
    row = db.execute(select(SourceHealth).where(SourceHealth.source == source)).scalar_one_or_none()
    if not row:
        row = SourceHealth(source=source)
        db.add(row)

    alpha = 0.35
    avg_jobs = float(row.avg_jobs or 0.0)
    success_rate = float(row.success_rate or 1.0)
    block_rate = float(row.block_rate or 0.0)
    row.last_run_at = datetime.utcnow()
    row.avg_jobs = ((1 - alpha) * avg_jobs) + (alpha * collected_count)
    row.success_rate = ((1 - alpha) * success_rate) + (alpha * (1.0 if collected_count > 0 else 0.2))
    row.block_rate = ((1 - alpha) * block_rate) + (alpha * (1.0 if blocked else 0.0))


def _feedback_stats_by_source(db: Session, profile_id: int, window_days: int = 30) -> dict[str, dict[str, float]]:
    cutoff = datetime.utcnow() - timedelta(days=window_days)
    rows = db.execute(
        select(Feedback.vote, Job.source)
        .join(Job, Job.id == Feedback.job_id)
        .where(Feedback.profile_id == profile_id)
        .where(Feedback.created_at >= cutoff)
    ).all()

    agg: dict[str, Counter[str]] = defaultdict(Counter)
    for vote, source in rows:
        agg[source or "unknown"][vote or "unknown"] += 1

    stats: dict[str, dict[str, float]] = {}
    for source, ctr in agg.items():
        total = ctr["like"] + ctr["dislike"]
        if total == 0:
            continue
        stats[source] = {"like_ratio": ctr["like"] / total, "count": float(total)}
    return stats


def build_agent_plan(db: Session, profile: SearchProfile, state: AgentState) -> dict[str, Any]:
    profile_sources = profile.sources or DEFAULT_SOURCES
    health_rows = db.execute(select(SourceHealth)).scalars().all()
    health_map = {row.source: row for row in health_rows}
    feedback_source_stats = _feedback_stats_by_source(db, profile.id, window_days=30)

    now = datetime.utcnow()
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for source in profile_sources:
        pause_until = _safe_parse_iso((state.paused_sources or {}).get(source))
        if pause_until and pause_until > now:
            skipped.append({"source": source, "reason": f"paused_until:{pause_until.isoformat()}"})
            continue

        learned_weight = float((state.learned_source_weights or {}).get(source, 1.0))
        health = health_map.get(source)
        success_rate = health.success_rate if health else 0.85
        block_rate = health.block_rate if health else 0.0
        feedback_like_ratio = feedback_source_stats.get(source, {}).get("like_ratio", 0.5)
        feedback_count = feedback_source_stats.get(source, {}).get("count", 0.0)
        confidence = min(1.0, feedback_count / 15.0)
        feedback_term = ((feedback_like_ratio - 0.5) * 0.4) * confidence

        priority = (learned_weight * 1.0) + (success_rate * 0.35) - (block_rate * 0.5) + feedback_term
        candidates.append(
            {
                "source": source,
                "priority": round(priority, 5),
                "learned_weight": round(learned_weight, 5),
                "success_rate": round(success_rate, 5),
                "block_rate": round(block_rate, 5),
                "feedback_like_ratio": round(feedback_like_ratio, 5),
            }
        )

    candidates.sort(key=lambda x: x["priority"], reverse=True)
    max_sources = min(len(candidates), max(1, state.target_sources_per_run))
    selected = [c["source"] for c in candidates[:max_sources]]

    plan = {
        "created_at": now.isoformat(),
        "selected_sources": selected,
        "candidates_ranked": candidates,
        "skipped_sources": skipped,
        "target_sources_per_run": state.target_sources_per_run,
        "strategy": "conservative_adaptive",
    }
    return plan


def evaluate_agent_run(
    db: Session,
    profile: SearchProfile,
    run: Run,
    source_counts: dict[str, int],
    inserted: int,
    plan: dict[str, Any],
) -> dict[str, Any]:
    selected_sources = plan.get("selected_sources", [])
    jobs = db.execute(select(Job).where(Job.run_id == run.id)).scalars().all()
    top_jobs = sorted(jobs, key=lambda x: x.ranking_score, reverse=True)[:25]
    avg_score = round(sum(j.ranking_score for j in jobs) / len(jobs), 5) if jobs else 0.0
    avg_top_score = round(sum(j.ranking_score for j in top_jobs) / len(top_jobs), 5) if top_jobs else 0.0

    source_yield = {s: int(source_counts.get(s, 0)) for s in selected_sources}
    source_zero_yield = [s for s in selected_sources if source_counts.get(s, 0) == 0]

    feedback_source_stats = _feedback_stats_by_source(db, profile.id, window_days=30)
    eval_result = {
        "evaluated_at": datetime.utcnow().isoformat(),
        "selected_sources": selected_sources,
        "source_yield": source_yield,
        "source_zero_yield": source_zero_yield,
        "feedback_source_stats": feedback_source_stats,
        "total_collected": int(run.total_collected),
        "total_new": int(inserted),
        "avg_score": avg_score,
        "avg_top_score": avg_top_score,
        "novelty_ratio": round((inserted / run.total_collected), 5) if run.total_collected else 0.0,
    }
    return eval_result


def adapt_agent_state(
    db: Session,
    profile: SearchProfile,
    state: AgentState,
    plan: dict[str, Any],
    eval_result: dict[str, Any],
) -> dict[str, Any]:
    source_weights = dict(state.learned_source_weights or {})
    keyword_weights = dict(state.learned_keyword_weights or {})
    paused_sources = dict(state.paused_sources or {})
    now = datetime.utcnow()

    source_updates: dict[str, float] = {}
    for source in plan.get("selected_sources", []):
        current = float(source_weights.get(source, 1.0))
        source_yield = eval_result.get("source_yield", {}).get(source, 0)
        feedback_like_ratio = eval_result.get("feedback_source_stats", {}).get(source, {}).get("like_ratio")

        delta = 0.0
        if source_yield == 0:
            delta -= 0.06
        elif source_yield >= 8:
            delta += 0.03

        if feedback_like_ratio is not None:
            if feedback_like_ratio >= 0.65:
                delta += 0.08
            elif feedback_like_ratio <= 0.35:
                delta -= 0.08

        new_weight = max(0.4, min(1.8, current + delta))
        source_weights[source] = round(new_weight, 5)
        source_updates[source] = round(new_weight - current, 5)

        if source_yield == 0 and new_weight <= 0.55:
            paused_sources[source] = (now + timedelta(days=2)).isoformat()
        elif source in paused_sources and new_weight >= 0.75:
            paused_sources.pop(source, None)

    cutoff = now - timedelta(days=45)
    recent_feedback = db.execute(
        select(Feedback).where(Feedback.profile_id == profile.id).where(Feedback.created_at >= cutoff)
    ).scalars().all()

    keyword_deltas: Counter[str] = Counter()
    for row in recent_feedback:
        step = 0.03 if row.vote == "like" else -0.04
        for tag in row.reason_tags or []:
            keyword_deltas[tag.strip().lower()] += step

    keyword_updates: dict[str, float] = {}
    for key, delta in keyword_deltas.items():
        current = float(keyword_weights.get(key, 0.0))
        updated = max(-0.5, min(0.8, current + delta))
        keyword_weights[key] = round(updated, 5)
        keyword_updates[key] = round(updated - current, 5)

    state.learned_source_weights = source_weights
    state.learned_keyword_weights = keyword_weights
    state.paused_sources = paused_sources
    state.run_count = (state.run_count or 0) + 1
    state.last_plan = plan
    state.last_eval = eval_result

    adapt_summary = {
        "adapted_at": now.isoformat(),
        "source_updates": source_updates,
        "keyword_updates": keyword_updates,
        "paused_sources": paused_sources,
        "run_count": state.run_count,
    }
    state.last_adapt = adapt_summary
    db.commit()
    return adapt_summary


def run_daily_search(profile_id: int, run_date: datetime | None = None) -> dict[str, Any]:
    run_date = run_date or datetime.utcnow()
    with SessionLocal() as db:
        profile = db.get(SearchProfile, profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")

        profile_dict = _profile_to_dict(profile)
        state = _get_or_create_agent_state(db, profile.id)
        plan = build_agent_plan(db, profile, state)
        sources = plan["selected_sources"] or (profile_dict["sources"] or DEFAULT_SOURCES)

        run = Run(profile_id=profile.id, status="running", started_at=run_date)
        db.add(run)
        db.commit()
        db.refresh(run)

        feedback_rows = _feedback_for_profile(db, profile_id)
        feedback_bias = compute_feedback_bias(feedback_rows)

        total_collected = 0
        inserted = 0
        source_counts: dict[str, int] = defaultdict(int)

        existing_fingerprints = set(
            db.execute(select(Job.fingerprint).where(Job.profile_id == profile.id)).scalars().all()
        )

        for source in sources:
            blocked = False
            try:
                jobs = collect_from_source(source, profile_dict)
            except Exception:
                jobs = []
                blocked = True

            source_counts[source] += len(jobs)
            total_collected += len(jobs)

            for job in jobs:
                if not job.get("title") or not job.get("source_url"):
                    continue
                if not _job_matches_profile_criteria(job, profile_dict):
                    continue
                fingerprint = job["fingerprint"]
                if fingerprint in existing_fingerprints:
                    continue

                ranking_score = score_job(
                    job,
                    profile_dict,
                    feedback_bias,
                    source_weight_overrides=state.learned_source_weights or {},
                    keyword_weight_overrides=state.learned_keyword_weights or {},
                )
                db_job = Job(
                    run_id=run.id,
                    profile_id=profile.id,
                    source=job["source"],
                    source_url=job["source_url"],
                    title=job["title"],
                    company_name=job["company_name"],
                    location=job.get("location", ""),
                    description=job.get("description", ""),
                    salary_min=job.get("salary_min"),
                    salary_max=job.get("salary_max"),
                    remote_type=job.get("remote_type", ""),
                    employment_type=job.get("employment_type", ""),
                    source_confidence=job.get("source_confidence", 0.6),
                    ranking_score=ranking_score,
                    fingerprint=fingerprint,
                    collected_at=job.get("collected_at", datetime.utcnow()),
                    raw_payload=job.get("raw_payload", {}),
                )
                db.add(db_job)
                existing_fingerprints.add(fingerprint)
                inserted += 1

            _update_source_health(db, source, len(jobs), blocked=blocked)
            db.commit()

        run.total_collected = total_collected
        run.total_new = inserted
        run.status = "completed"
        run.finished_at = datetime.utcnow()
        run.notes = f"Sources: {dict(source_counts)}"
        db.commit()

        eval_result = evaluate_agent_run(db, profile, run, source_counts, inserted, plan)
        adapt_summary = adapt_agent_state(db, profile, state, plan, eval_result)

        artifact = AgentRunArtifact(
            run_id=run.id,
            profile_id=profile.id,
            plan_json=plan,
            eval_json=eval_result,
            adapt_json=adapt_summary,
        )
        db.add(artifact)
        db.commit()

        top_jobs = (
            db.execute(
                select(Job)
                .where(Job.run_id == run.id)
                .order_by(desc(Job.ranking_score))
                .limit(30)
            )
            .scalars()
            .all()
        )
        send_digest_email(profile, top_jobs)

        return {
            "run_id": run.id,
            "profile_id": profile.id,
            "status": run.status,
            "total_collected": total_collected,
            "total_new": inserted,
            "source_counts": dict(source_counts),
            "agent_plan": plan,
            "agent_eval": eval_result,
            "agent_adapt": adapt_summary,
        }


def submit_feedback(payload: dict[str, Any]) -> Feedback:
    with SessionLocal() as db:
        job = db.get(Job, payload["job_id"])
        if not job:
            raise ValueError(f"Job {payload['job_id']} not found")

        feedback = Feedback(
            job_id=payload["job_id"],
            profile_id=payload["profile_id"],
            vote=payload["vote"],
            reason_tags=payload.get("reason_tags", []),
            note=payload.get("note", ""),
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback


def _job_to_dict(job: Job) -> dict[str, Any]:
    return {
        "id": job.id,
        "profile_id": job.profile_id,
        "run_id": job.run_id,
        "source": job.source,
        "source_url": job.source_url,
        "title": job.title,
        "company_name": job.company_name,
        "location": job.location,
        "description": job.description,
        "ranking_score": job.ranking_score,
        "source_confidence": job.source_confidence,
        "collected_at": job.collected_at.isoformat(),
    }


def get_jobs(profile_id: int, run_id: int | None = None, min_score: float = 0.0, limit: int = 100) -> list[Job]:
    with SessionLocal() as db:
        query = (
            select(Job)
            .where(Job.profile_id == profile_id)
            .where(Job.ranking_score >= min_score)
            .order_by(desc(Job.ranking_score), desc(Job.collected_at))
            .limit(limit)
        )
        if run_id:
            query = query.where(Job.run_id == run_id)
        return db.execute(query).scalars().all()


def get_jobs_for_api(
    profile_id: int,
    run_id: int | None = None,
    min_score: float = 0.0,
    limit: int = 100,
    include_explanations: bool = False,
) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        profile = db.get(SearchProfile, profile_id)
        if not profile:
            return []
        state = _get_or_create_agent_state(db, profile.id)
        profile_dict = _profile_to_dict(profile)
        feedback_rows = _feedback_for_profile(db, profile_id)
        feedback_bias = compute_feedback_bias(feedback_rows)

        query = (
            select(Job)
            .where(Job.profile_id == profile_id)
            .where(Job.ranking_score >= min_score)
            .order_by(desc(Job.ranking_score), desc(Job.collected_at))
            .limit(limit)
        )
        if run_id:
            query = query.where(Job.run_id == run_id)
        jobs = db.execute(query).scalars().all()

        payload = []
        for j in jobs:
            row = _job_to_dict(j)
            if include_explanations:
                _, explanation = score_job_explained(
                    {
                        "source": j.source,
                        "source_url": j.source_url,
                        "title": j.title,
                        "company_name": j.company_name,
                        "location": j.location,
                        "description": j.description,
                        "collected_at": j.collected_at,
                    },
                    profile_dict,
                    feedback_bias,
                    source_weight_overrides=state.learned_source_weights or {},
                    keyword_weight_overrides=state.learned_keyword_weights or {},
                )
                row["ranking_explanation"] = explanation
            payload.append(row)
        return payload


def list_runs(profile_id: int, limit: int = 30) -> list[Run]:
    with SessionLocal() as db:
        return (
            db.execute(
                select(Run).where(Run.profile_id == profile_id).order_by(desc(Run.started_at)).limit(limit)
            )
            .scalars()
            .all()
        )


def get_agent_state(profile_id: int) -> dict[str, Any]:
    with SessionLocal() as db:
        profile = db.get(SearchProfile, profile_id)
        if not profile:
            raise ValueError("Profile not found")

        state = _get_or_create_agent_state(db, profile_id)
        recent_artifact = (
            db.execute(
                select(AgentRunArtifact)
                .where(AgentRunArtifact.profile_id == profile_id)
                .order_by(desc(AgentRunArtifact.created_at))
                .limit(1)
            )
            .scalars()
            .first()
        )

        return {
            "profile_id": profile_id,
            "run_count": state.run_count,
            "target_sources_per_run": state.target_sources_per_run,
            "learned_source_weights": state.learned_source_weights,
            "learned_keyword_weights": state.learned_keyword_weights,
            "paused_sources": state.paused_sources,
            "last_plan": state.last_plan,
            "last_eval": state.last_eval,
            "last_adapt": state.last_adapt,
            "latest_run_artifact": {
                "run_id": recent_artifact.run_id if recent_artifact else None,
                "plan_json": recent_artifact.plan_json if recent_artifact else {},
                "eval_json": recent_artifact.eval_json if recent_artifact else {},
                "adapt_json": recent_artifact.adapt_json if recent_artifact else {},
            },
        }


def send_digest_email(profile: SearchProfile, jobs: list[Job]) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    recipient = os.getenv("DIGEST_TO_EMAIL")
    sender = os.getenv("DIGEST_FROM_EMAIL", smtp_user or "")

    if not smtp_host or not smtp_user or not smtp_pass or not recipient:
        return

    lines = []
    for j in jobs[:20]:
        lines.append(f"- [{j.ranking_score:.2f}] {j.title} @ {j.company_name} ({j.location})\n  {j.source_url}")

    body = "\n".join(lines) or "No new jobs found in this run."

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = f"Daily Job Digest - {profile.name} - {datetime.utcnow().strftime('%Y-%m-%d')}"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(sender, [recipient], msg.as_string())
