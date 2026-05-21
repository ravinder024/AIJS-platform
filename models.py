from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SearchProfile(Base):
    __tablename__ = "search_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    role_query: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False, default="Remote")
    target_locations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    role_queries: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    work_settings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    company_size_min: Mapped[int | None] = mapped_column(Integer)
    company_size_max: Mapped[int | None] = mapped_column(Integer)
    include_companies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    exclude_companies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    industries: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recently_funded_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    job_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    experience_min_years: Mapped[float | None] = mapped_column(Float)
    experience_max_years: Mapped[float | None] = mapped_column(Float)
    min_glassdoor_rating: Mapped[float | None] = mapped_column(Float)
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    posted_within_hours: Mapped[float | None] = mapped_column(Float)
    include_keywords: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    exclude_keywords: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    sources: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    runs: Mapped[list["Run"]] = relationship(back_populates="profile")
    feedback_events: Mapped[list["Feedback"]] = relationship(back_populates="profile")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("search_profiles.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="running", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    total_collected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_new: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    profile: Mapped["SearchProfile"] = relationship(back_populates="runs")
    jobs: Mapped[list["Job"]] = relationship(back_populates="run")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    profile_id: Mapped[int] = mapped_column(ForeignKey("search_profiles.id"), nullable=False)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(60), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    remote_type: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    employment_type: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    source_confidence: Mapped[float] = mapped_column(Float, default=0.6, nullable=False)
    ranking_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    run: Mapped["Run"] = relationship(back_populates="jobs")
    feedback_events: Mapped[list["Feedback"]] = relationship(back_populates="job")
    company: Mapped["Company"] = relationship(back_populates="jobs")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    profile_id: Mapped[int] = mapped_column(ForeignKey("search_profiles.id"), nullable=False)
    vote: Mapped[str] = mapped_column(String(20), nullable=False)  # like/dislike
    reason_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    job: Mapped["Job"] = relationship(back_populates="feedback_events")
    profile: Mapped["SearchProfile"] = relationship(back_populates="feedback_events")


class SourceHealth(Base):
    __tablename__ = "source_health"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime)
    success_rate: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    block_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_jobs: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class AgentState(Base):
    __tablename__ = "agent_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("search_profiles.id"), unique=True, nullable=False)
    learned_source_weights: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    learned_keyword_weights: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    paused_sources: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    target_sources_per_run: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_plan: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_eval: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_adapt: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class AgentRunArtifact(Base):
    __tablename__ = "agent_run_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), unique=True, nullable=False)
    profile_id: Mapped[int] = mapped_column(ForeignKey("search_profiles.id"), nullable=False)
    plan_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    eval_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    adapt_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Company(Base):
    """Company intelligence table for outreach and recruitment tracking."""
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(200), nullable=False, index=True, unique=True)
    industry: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    employee_count: Mapped[int | None] = mapped_column(Integer)
    funding_stage: Mapped[str] = mapped_column(String(100), default="", nullable=False)  # 'seed', 'series_a', 'series_b', 'public'
    funding_amount: Mapped[float | None] = mapped_column(Float)  # In USD
    remote_policy: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)  # 'remote', 'hybrid', 'onsite'
    hiring_signals: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # Recent job posts, LinkedIn updates
    ai_analysis: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # Full AI company assessment
    opportunity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0-100 priority score
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    jobs: Mapped[list["Job"]] = relationship(back_populates="company")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="company")


class Contact(Base):
    """Decision makers and hiring managers for outreach."""
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(300), nullable=False)
    title: Mapped[str] = mapped_column(String(300), default="", nullable=False)  # 'CPO', 'VP Product', 'Hiring Manager'
    seniority_level: Mapped[str] = mapped_column(String(100), default="", nullable=False)  # 'c_level', 'vp', 'director', 'manager'
    email: Mapped[str] = mapped_column(String(300), nullable=True, index=True)
    linkedin_url: Mapped[str] = mapped_column(String(500), nullable=True)
    decision_maker_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0-100, likelihood they influence hiring
    relationship_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0-100, current relationship strength
    response_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Historical response rate %
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    company: Mapped["Company"] = relationship(back_populates="contacts")
