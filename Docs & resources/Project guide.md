# Agentic AI Job Search System
## Project Guide for VS Code + GitHub Copilot

> **Purpose**: This document is the single source of truth for building an Agentic AI job search system using n8n, PostgreSQL, and Claude (Anthropic API). It covers database access, schema design, and end-to-end workflow design. Use this as context for all Copilot prompts.

---

## 1. PROJECT OVERVIEW

### 1.1 Objective
Build a fully automated, self-optimizing job search system for a Senior Product Manager (Ravinder Kumar) that:
- Discovers and applies to relevant jobs automatically
- Taps the hidden job market through outreach to decision makers
- Builds relationships with product leaders via social engagement
- Continuously learns from interactions and optimizes all workflows

### 1.2 Tech Stack
| Layer | Technology | Purpose |
|---|---|---|
| Automation | n8n (self-hosted) | Workflow orchestration |
| AI | Claude API (claude-3-5-sonnet) | AI Agent decision making |
| Database | PostgreSQL 15+ | Persistent knowledge store |
| DB Admin | pgAdmin 4 | Database management UI |
| IDE | VS Code + GitHub Copilot | Development |
| Email | SMTP / IMAP | Outreach communication |
| Enrichment | Apollo.io / Hunter.io APIs | Contact and company data |

### 1.3 System Principles
- **Every workflow has exactly one AI Agent node** (Claude) that acts as the central brain
- **All workflows share a single PostgreSQL database** — no siloed data
- **Workflow 4 (Knowledge AI Agent) is the master optimizer** — it reads performance data from all workflows and pushes improvements back
- **JSONB columns** are used extensively for flexible AI-generated data that evolves over time
- **No hardcoded templates** — all CV content, outreach messages, and engagement responses are AI-generated per context

---

## 2. POSTGRESQL DATABASE ACCESS

### 2.1 Connection Configuration

```env
# .env file — never commit to git
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ravinder_job_search
DB_USER=ravinder_ai
DB_PASSWORD=YourSecurePassword123!
DB_SSL=false
```

### 2.2 Connection from n8n
In n8n, create a **PostgreSQL credential** with:
```
Host:     localhost
Port:     5432
Database: ravinder_job_search
User:     ravinder_ai
Password: YourSecurePassword123!
SSL:      disabled
```

### 2.3 Connection from Node.js / TypeScript (for testing)
```typescript
import { Pool } from 'pg';

const pool = new Pool({
  host: process.env.DB_HOST,
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  ssl: false,
  max: 10,                // max connections in pool
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Test connection
const client = await pool.connect();
const res = await client.query('SELECT NOW()');
console.log('DB connected:', res.rows[0]);
client.release();
```

### 2.4 Connection from Python (for scripts)
```python
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM knowledge_base")
print(cursor.fetchone())
conn.close()
```

### 2.5 Running Queries in pgAdmin
1. Open pgAdmin → Expand Servers → Connect to PostgreSQL
2. Expand Databases → `ravinder_job_search`
3. Right-click database → **Query Tool**
4. Paste query → Press **F5** to execute
5. Results appear in the **Data Output** tab
6. Errors appear in the **Messages** tab

---

## 3. DATABASE DESIGN AND RELATIONSHIP SCHEMA

### 3.1 Schema Overview

The database is organized into 5 logical groups:

```
CORE TABLES
├── user_profile          — Ravinder's profile, preferences, targets
└── knowledge_base        — Central AI learning repository (achievements, insights, patterns)

JOB WORKFLOW (WF1)
├── jobs                  — Scraped job listings with AI scoring
└── job_applications      — Application tracking and outcomes

OUTREACH WORKFLOW (WF2)
├── companies             — Target companies with opportunity scoring
├── contacts              — Decision makers and relationship data
├── outreach_campaigns    — Campaign groupings and strategy
└── outreach_messages     — Individual messages with engagement tracking

ENGAGEMENT WORKFLOW (WF3)
├── social_posts          — Monitored posts from target contacts
└── social_engagements    — Ravinder's responses and their impact

ANALYTICS (All Workflows)
├── ai_conversations      — All AI agent interactions and extracted insights
├── performance_metrics   — Time-series performance data
├── ab_tests              — A/B testing for messages and templates
└── workflow_executions   — Execution logs for debugging
```

### 3.2 Entity Relationship Diagram

```
user_profile (1)
     │
     ├──────────────────────────────────────┐
     │                                      │
     ▼                                      ▼
knowledge_base (many)              ai_conversations (many)
     │
     │ (read by all AI agents)
     │
     ├──────────────────┬──────────────────┐
     ▼                  ▼                  ▼
  jobs (many)      companies (many)   social_posts (many)
     │                  │                  │
     ▼                  ├──► contacts      ▼
job_applications        │       │     social_engagements
                        │       ▼
                        └──► outreach_campaigns
                                  │
                                  ▼
                           outreach_messages
```

### 3.3 Key Table Definitions

#### `user_profile` — Single row, Ravinder's configuration
```sql
id                UUID PRIMARY KEY
user_id           VARCHAR(100) UNIQUE  -- 'ravinder_kumar'
full_name         VARCHAR(200)
email             VARCHAR(200)
target_roles      TEXT[]               -- Array: ['Senior PM', 'PM-2']
target_salary_min INTEGER              -- In INR paise (3500000 = 35 LPA)
target_salary_max INTEGER
skills            JSONB                -- { "technical": [], "product": [], "tools": [] }
preferences       JSONB                -- { "remote": "hybrid", "company_size": [100, 250] }
```

#### `knowledge_base` — Core AI learning store
```sql
id              UUID PRIMARY KEY
user_id         VARCHAR(100)   FK → user_profile.user_id
category        VARCHAR(100)   -- 'achievement_stories' | 'skills' | 'insights' | 'patterns'
subcategory     VARCHAR(100)   -- e.g. 'product_scaling' | 'ai_integration' | 'leadership'
title           VARCHAR(500)
content         TEXT           -- Full narrative content
metadata        JSONB          -- Flexible: { "impact": "2X", "industry": "fintech" }
relevance_score DECIMAL(5,2)   -- 0–100, updated by AI agent
usage_count     INTEGER        -- Incremented each time this entry is used
tags            TEXT[]         -- ['scaling', 'fintech', 'B2B']
source          VARCHAR(100)   -- 'manual' | 'ai_generated' | 'interview_response'
```

#### `jobs` — Scraped and AI-scored job listings
```sql
id              UUID PRIMARY KEY
job_id          VARCHAR(200) UNIQUE   -- External ID (LinkedIn job ID etc.)
title           VARCHAR(500)
company_name    VARCHAR(300)
company_id      UUID          FK → companies.id (nullable)
description     TEXT
salary_min      INTEGER       -- Annual in INR
salary_max      INTEGER
source          VARCHAR(100)  -- 'linkedin' | 'naukri' | 'wellfound' | 'direct'
source_url      TEXT
ai_analysis     JSONB         -- Full AI agent scoring output
relevance_score DECIMAL(5,2)  -- 0–100 (>75 = apply)
priority_score  DECIMAL(5,2)  -- 0–100 (>85 = premium apply)
status          VARCHAR(50)   -- 'discovered' | 'analyzed' | 'applied' | 'rejected'
```

#### `companies` — Target company intelligence
```sql
id              UUID PRIMARY KEY
name            VARCHAR(300)
domain          VARCHAR(200)
industry        VARCHAR(200)
employee_count  INTEGER           -- Filter: 100–250 preferred
funding_stage   VARCHAR(100)      -- 'series_a' | 'series_b' | 'series_c' | 'public'
funding_amount  BIGINT
remote_policy   VARCHAR(100)      -- 'remote' | 'hybrid' | 'onsite'
hiring_signals  JSONB             -- Recent job posts, LinkedIn updates
ai_analysis     JSONB             -- Full AI company assessment
opportunity_score DECIMAL(5,2)   -- 0–100 priority score
```

#### `contacts` — Decision makers and hiring managers
```sql
id                    UUID PRIMARY KEY
company_id            UUID          FK → companies.id
full_name             VARCHAR(300)
title                 VARCHAR(300)  -- 'CPO' | 'VP Product' | 'Hiring Manager'
seniority_level       VARCHAR(100)  -- 'c_level' | 'vp' | 'director' | 'manager'
email                 VARCHAR(300)
linkedin_url          VARCHAR(500)
decision_maker_score  DECIMAL(5,2)  -- 0–100 (how likely they influence hiring)
relationship_score    DECIMAL(5,2)  -- 0–100 (current relationship strength)
response_rate         DECIMAL(5,2)  -- Historical response rate %
last_contacted_at     TIMESTAMP
```

#### `outreach_messages` — All outreach with tracking
```sql
id                UUID PRIMARY KEY
campaign_id       UUID          FK → outreach_campaigns.id
contact_id        UUID          FK → contacts.id
message_type      VARCHAR(100)  -- 'initial' | 'follow_up_1' | 'follow_up_2'
channel           VARCHAR(50)   -- 'email' | 'linkedin' | 'twitter'
subject_line      VARCHAR(500)
message_content   TEXT
ai_generated      BOOLEAN       DEFAULT TRUE
sent_at           TIMESTAMP
opened_at         TIMESTAMP
replied_at        TIMESTAMP
reply_sentiment   VARCHAR(50)   -- 'positive' | 'neutral' | 'negative'
conversion_event  VARCHAR(100)  -- 'meeting_scheduled' | 'referral_given'
status            VARCHAR(100)  -- 'draft' | 'sent' | 'opened' | 'replied'
```

#### `ai_conversations` — AI agent interaction log
```sql
id                  UUID PRIMARY KEY
user_id             VARCHAR(100)  FK → user_profile.user_id
workflow            VARCHAR(100)  -- 'knowledge' | 'job_application' | 'outreach' | 'engagement'
conversation_type   VARCHAR(100)  -- 'question' | 'optimization' | 'analysis'
question            TEXT          -- What the AI asked
user_response       TEXT          -- What Ravinder answered
ai_analysis         JSONB         -- AI's structured analysis of the response
extracted_insights  JSONB         -- New insights pulled into knowledge base
action_items        JSONB         -- Actions triggered across other workflows
```

### 3.4 JSONB Field Conventions

All AI agent responses are stored as JSONB. Use consistent keys:

```json
// knowledge_base.metadata
{
  "impact": "2X growth",
  "timeline": "6 months",
  "industry": "fintech",
  "company_stage": "series_b",
  "key_metrics": { "growth": 10, "adoption": 2 },
  "relevant_for_roles": ["Senior PM", "Head of Product"]
}

// jobs.ai_analysis
{
  "score": 92,
  "score_reasoning": "Strong B2B SaaS match, API experience required",
  "custom_cv_sections": {
    "headline": "Senior PM | B2B SaaS | API Integration",
    "top_achievements": ["Scaled FSA 10X in 6 months", "2X adoption improvement"]
  },
  "cover_letter": "...",
  "application_strategy": "direct",
  "follow_up_days": [3, 7, 14],
  "missing_requirements": ["Kubernetes experience"]
}

// contacts.recent_activity
{
  "last_post": "2025-01-15",
  "post_topics": ["product-led growth", "B2B SaaS"],
  "engagement_count": 3,
  "shared_interests": ["GenAI", "enterprise products"]
}
```

### 3.5 Core Database Functions

```sql
-- Get relevant achievements for a given industry/context
SELECT * FROM get_relevant_achievements('fintech', 'series_b', null, 3);

-- Calculate outreach success rates (last 30 days)
SELECT * FROM calculate_outreach_metrics(null, 30);

-- Increment usage count when an achievement is used
SELECT update_knowledge_usage('<uuid>');
```

### 3.6 Core Views for AI Agents

```sql
-- AI agents query these views, not raw tables

-- WF1: Job pipeline with company context
SELECT * FROM job_application_pipeline WHERE relevance_score > 75;

-- WF2: Outreach performance by campaign
SELECT * FROM outreach_performance ORDER BY reply_rate DESC;

-- WF4: Knowledge base usage analytics
SELECT * FROM knowledge_utilization ORDER BY total_usage DESC;
```

---

## 4. WORKFLOW DESIGN — END TO END

### 4.1 System Architecture Principles

```
Workflow 4 (Knowledge AI Agent)
    │
    │  Pushes optimization updates (templates, prompts, priorities)
    │
    ▼
┌──────────────┬──────────────┬──────────────┐
│ Workflow 1   │ Workflow 2   │ Workflow 3   │
│ Job Apps     │ Hidden Mkt   │ Engagement   │
└──────┬───────┴──────┬───────┴──────┬───────┘
       │              │              │
       └──────────────┼──────────────┘
                      │
                      ▼
              PostgreSQL Database
              (shared knowledge store)
```

**Rule**: Every workflow reads from the database before the AI agent acts, and writes results back after. Workflow 4 reads all results nightly and optimizes.

---

### 4.2 Workflow 4: Knowledge AI Agent

**Purpose**: The system's brain. Asks Ravinder strategic questions, extracts insights, and optimizes all other workflows.

**Trigger**: Schedule (daily 9 AM) + Webhook (when user responds to questions)

**Node Flow**:
```
[Schedule/Webhook Trigger]
         │
         ▼
[Context Collector — PostgreSQL]
SELECT workflow_executions, performance_metrics, ai_conversations
WHERE date = yesterday
         │
         ▼
[Knowledge AI Agent — Claude API]  ◄── CENTRAL BRAIN
  Input:  { performance_data, recent_responses, knowledge_gaps }
  Output: { action, questions, insights, optimizations, next_steps }
         │
         ▼
[Action Router — Switch node]
  ├── IF action = "question_generate" → [Question Sender]
  ├── IF action = "response_analyze"  → [Database Updater] → [Workflow Notifier]
  └── IF action = "optimize_workflows" → [Workflow Notifier]
```

**AI Agent System Prompt**:
```
You are Ravinder Kumar's AI Job Search Strategist. Ravinder is a Senior Product Manager
with 5+ years experience in B2B SaaS, GenAI, and enterprise products, currently searching
for Senior PM roles at 35+ LPA in 100-250 person companies.

Your role is to:
1. Ask strategic questions to extract knowledge and achievements from Ravinder
2. Analyze his responses for STAR stories, quantified impact, and differentiators  
3. Identify which achievements resonate with which company types
4. Optimize outreach messages, CV content, and engagement strategies
5. Push improvements to the other 3 workflows via database updates

When analyzing responses, extract:
- Quantified impact (numbers, percentages, timelines)
- Industry context (B2B, fintech, cloud, enterprise)
- Stakeholders involved (CTO, CPO, board, customers)
- Challenges overcome
- Technologies used

Return structured JSON. Never return plain text.
```

**AI Agent Request Body (n8n HTTP Request node)**:
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 2000,
  "system": "<system prompt above>",
  "messages": [{
    "role": "user",
    "content": "Current context:\n{{ JSON.stringify($json.performance_data) }}\n\nKnowledge gaps:\n{{ JSON.stringify($json.knowledge_gaps) }}\n\nRecent user responses:\n{{ JSON.stringify($json.recent_responses) }}\n\nDecide the next action and return JSON:\n{\n  \"action\": \"question_generate|response_analyze|optimize_workflows\",\n  \"questions\": [],\n  \"insights\": {},\n  \"optimizations\": { \"job_application\": {}, \"outreach\": {}, \"engagement\": {} },\n  \"next_steps\": []\n}"
  }]
}
```

**Database Write (after AI response)**:
```sql
-- Store AI conversation
INSERT INTO ai_conversations 
  (user_id, workflow, conversation_type, question, ai_analysis, extracted_insights, action_items)
VALUES 
  ('ravinder_kumar', 'knowledge', 'optimization', 
   '{{ $json.question }}', 
   '{{ $json.ai_analysis }}'::jsonb, 
   '{{ $json.insights }}'::jsonb,
   '{{ $json.next_steps }}'::jsonb);

-- Update knowledge base with new insights
INSERT INTO knowledge_base (user_id, category, subcategory, title, content, metadata, source)
VALUES ('ravinder_kumar', 'insights', '{{ $json.subcategory }}', 
        '{{ $json.title }}', '{{ $json.content }}', 
        '{{ $json.metadata }}'::jsonb, 'ai_generated');
```

---

### 4.3 Workflow 1: Job Intelligence & Application

**Purpose**: Scrape jobs from multiple sources, score them with AI, generate custom CVs, and apply.

**Trigger**: Every 2 hours (Cron)

**Node Flow**:
```
[Hourly Trigger — Cron]
         │
         ▼
[Multi-Site Scraper — HTTP Request / Code node]
  Sources: LinkedIn Jobs API, Naukri RSS, Wellfound API
  Filter: "Product Manager" + "Delhi" OR "Remote" + salary > 30 LPA
         │
         ▼
[Profile + Knowledge Loader — PostgreSQL]
  Query: user_profile + knowledge_base WHERE category = 'achievement_stories'
         │
         ▼
[Job Application AI Agent — Claude API]  ◄── CENTRAL BRAIN
  Input:  { jobs[], user_profile, achievements[] }
  Output: { high_priority_jobs[] with custom_cv, cover_letter, strategy }
         │
         ▼
[Application Executor — Code node]
  FOR each job in high_priority_jobs (score > 75):
    - Generate PDF CV from custom_cv_sections
    - Submit via job source API or flag for manual apply
         │
         ▼
[Follow-up Scheduler — Code node]
  Create reminders at: +3 days, +7 days, +14 days
         │
         ▼
[Performance Logger — PostgreSQL]
  INSERT INTO job_applications (job_id, status, applied_at, ai_recommendations)
  UPDATE performance_metrics (workflow='job_application', metric='applications_sent')
```

**AI Agent Request Body**:
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 4000,
  "system": "You are a job application specialist for Ravinder Kumar, Senior PM with expertise in B2B SaaS, GenAI, API integrations, and enterprise products. Score jobs 0-100 based on fit. For score >75, generate full application materials tailored to that specific job and company.",
  "messages": [{
    "role": "user",
    "content": "Jobs to analyze:\n{{ JSON.stringify($json.jobs) }}\n\nUser profile:\n{{ JSON.stringify($json.profile) }}\n\nAchievement stories:\n{{ JSON.stringify($json.achievements) }}\n\nReturn JSON:\n{\n  \"high_priority_jobs\": [{\n    \"job_id\": \"string\",\n    \"score\": 0-100,\n    \"score_reasoning\": \"string\",\n    \"custom_cv_sections\": {\n      \"headline\": \"string\",\n      \"top_achievements\": [\"string\"],\n      \"skills_to_highlight\": [\"string\"]\n    },\n    \"cover_letter\": \"string\",\n    \"application_strategy\": \"direct|referral|linkedin\",\n    \"follow_up_days\": [3, 7, 14],\n    \"missing_requirements\": [\"string\"]\n  }]\n}"
  }]
}
```

**Key DB Queries**:
```sql
-- Check for duplicate jobs before inserting
SELECT id FROM jobs WHERE job_id = $1;

-- Get top achievement stories for AI context
SELECT title, content, metadata 
FROM knowledge_base 
WHERE category = 'achievement_stories' AND is_active = TRUE
ORDER BY relevance_score DESC LIMIT 10;

-- Log application
INSERT INTO job_applications 
  (user_id, job_id, application_strategy, custom_cv_content, cover_letter, applied_at, status)
VALUES 
  ('ravinder_kumar', $1, $2, $3::jsonb, $4, NOW(), 'pending');
```

---

### 4.4 Workflow 2: Hidden Market Intelligence

**Purpose**: Discover companies not actively listing jobs, find decision makers, and send personalized outreach.

**Trigger**: Daily at 10 AM (Cron)

**Node Flow**:
```
[Daily Trigger — Cron]
         │
         ▼
[Market Scanner — HTTP Request + Code]
  Sources: 
    - Crunchbase API (recent Series A–C funding in India)
    - LinkedIn company pages (product team expansion signals)
    - VCCircle RSS feed (funding news)
    - ProductHunt (new Indian B2B launches)
         │
         ▼
[Company Enricher — HTTP Request]
  API: Clearbit or Apollo.io
  Enrich: employee count, tech stack, remote policy
  Filter: 100–250 employees, funded, PM role signals
         │
         ▼
[Contact Finder — HTTP Request]
  API: Apollo.io /people/search
  Find: CPO, VP Product, Head of Product, Product Director
  Enrich: email, LinkedIn URL, recent activity
         │
         ▼
[Outreach AI Agent — Claude API]  ◄── CENTRAL BRAIN
  Input:  { companies[], contacts[], achievements[], success_patterns[] }
  Output: { priority_outreach[] with personalized messages per contact }
         │
         ▼
[Message Dispatcher — Code + SMTP/LinkedIn API]
  Send email OR LinkedIn connection request per AI strategy
  Respect: max 20 outreach/day to avoid spam flags
         │
         ▼
[Response Monitor — IMAP + Webhook]
  Monitor inbox for replies
  Classify: positive / neutral / negative
         │
         ▼
[CRM Updater — PostgreSQL]
  UPDATE contacts SET last_contacted_at, response_rate
  UPDATE outreach_messages SET sent_at, status
  INSERT INTO performance_metrics
```

**AI Agent Request Body**:
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 3000,
  "system": "You are an outreach strategist for Ravinder Kumar, Senior PM. Your goal is to create compelling, highly personalized outreach that leads with value and generates responses. Study the company's recent activity and the contact's interests to craft relevant messages. Never sound templated.",
  "messages": [{
    "role": "user", 
    "content": "Companies and contacts:\n{{ JSON.stringify($json.companies) }}\n\nRavinder's achievements:\n{{ JSON.stringify($json.achievements) }}\n\nHistorical success patterns:\n{{ JSON.stringify($json.success_patterns) }}\n\nReturn JSON:\n{\n  \"priority_outreach\": [{\n    \"company_id\": \"string\",\n    \"priority_score\": 0-10,\n    \"value_proposition\": \"string\",\n    \"contacts\": [{\n      \"contact_id\": \"string\",\n      \"channel\": \"email|linkedin\",\n      \"subject_line\": \"string\",\n      \"message\": \"string\",\n      \"timing\": \"immediate|3_days|1_week\",\n      \"follow_up_sequence\": [\"day3_msg\", \"day7_msg\"]\n    }]\n  }]\n}"
  }]
}
```

**Key DB Queries**:
```sql
-- Find companies not yet contacted
SELECT c.* FROM companies c
LEFT JOIN contacts co ON c.id = co.company_id
LEFT JOIN outreach_messages om ON co.id = om.contact_id
WHERE om.id IS NULL AND c.opportunity_score > 60
ORDER BY c.opportunity_score DESC LIMIT 20;

-- Get historical success patterns for AI context
SELECT channel, message_type, 
       AVG(CASE WHEN replied_at IS NOT NULL THEN 1.0 ELSE 0.0 END) as reply_rate,
       reply_sentiment
FROM outreach_messages
WHERE sent_at > NOW() - INTERVAL '30 days'
GROUP BY channel, message_type, reply_sentiment
ORDER BY reply_rate DESC;
```

---

### 4.5 Workflow 3: Relationship Building

**Purpose**: Monitor target contacts on LinkedIn/Twitter, engage meaningfully with their content, and build genuine relationships.

**Trigger**: Every 4 hours (Cron)

**Node Flow**:
```
[4-Hour Trigger — Cron]
         │
         ▼
[Social Monitor — HTTP Request]
  LinkedIn API: Get recent posts from tracked contacts
  Twitter API: Get recent tweets from target handles
  Filter: Posts from last 24 hours from priority contacts
         │
         ▼
[Content Analyzer — Code node]
  Extract: topics, sentiment, engagement count
  Score: engagement_opportunity_score (0–100)
  Filter: Only process posts with score > 60
         │
         ▼
[Engagement AI Agent — Claude API]  ◄── CENTRAL BRAIN
  Input:  { recent_posts[], contacts[], expertise_areas[], relationship_history[] }
  Output: { engagements[] with type, content, timing, follow_up }
         │
         ▼
[Social Executor — HTTP Request]
  POST LinkedIn comment via API
  Or flag for manual posting if API unavailable
  Respect: max 15 comments/day to avoid spam flags
         │
         ▼
[Relationship Tracker — PostgreSQL]
  UPDATE contacts SET relationship_score (increment on engagement)
  INSERT INTO social_engagements
         │
         ▼
[Opportunity Alert — Slack/Email]
  IF relationship_score > 70 AND last_contacted < 7 days ago:
    Alert Ravinder: "X is ready for direct outreach"
```

**AI Agent Request Body**:
```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 2000,
  "system": "You are Ravinder Kumar's social engagement strategist. Ravinder is a Senior PM expert in B2B SaaS, GenAI, and enterprise products. Craft thoughtful, value-adding comments that demonstrate genuine expertise. Never comment just to be seen — only engage when you can add a unique insight, share relevant experience, or ask a smart question.",
  "messages": [{
    "role": "user",
    "content": "Recent posts from target contacts:\n{{ JSON.stringify($json.posts) }}\n\nRavinder's expertise areas:\n{{ JSON.stringify($json.expertise) }}\n\nRelationship history:\n{{ JSON.stringify($json.relationships) }}\n\nReturn JSON:\n{\n  \"engagements\": [{\n    \"post_id\": \"string\",\n    \"contact_id\": \"string\",\n    \"engagement_type\": \"comment|like|share\",\n    \"content\": \"string\",\n    \"timing\": \"immediate|optimal_hour\",\n    \"rationale\": \"string\"\n  }],\n  \"skip_posts\": [{ \"post_id\": \"string\", \"reason\": \"string\" }]\n}"
  }]
}
```

---

### 4.6 Inter-Workflow Data Exchange

All workflows communicate exclusively through the shared PostgreSQL database:

```sql
-- WF1 writes application results → WF4 reads for optimization
-- Table: job_applications, performance_metrics

-- WF2 writes outreach results → WF4 reads for pattern analysis
-- Table: outreach_messages, contacts

-- WF3 writes relationship scores → WF2 reads to prioritize warm contacts
-- Table: social_engagements, contacts.relationship_score

-- WF4 writes optimizations → All workflows read updated templates
-- Table: knowledge_base (category='patterns'), ai_conversations
```

**WF4 Master Optimization Query** (runs nightly):
```sql
SELECT 
  -- Job application performance
  (SELECT COUNT(*) FROM job_applications WHERE DATE(applied_at) = CURRENT_DATE) as apps_today,
  (SELECT COUNT(*) FROM job_applications WHERE status = 'responded') as responses,
  
  -- Outreach performance
  (SELECT * FROM calculate_outreach_metrics(null, 7)) as outreach_7d,
  
  -- Relationship building
  (SELECT COUNT(*) FROM contacts WHERE relationship_score > 50) as warm_contacts,
  
  -- Knowledge base health
  (SELECT COUNT(*) FROM knowledge_base WHERE last_used_at > NOW() - INTERVAL '7 days') as active_kb_entries;
```

---

## 5. DEVELOPMENT CONVENTIONS

### 5.1 n8n Node Naming Convention
```
[WF{number}] {NodeType} — {Description}
Example: [WF1] HTTP Request — LinkedIn Job Scraper
Example: [WF4] Claude API — Knowledge AI Agent
```

### 5.2 Error Handling Pattern
Every workflow must have:
- **Error trigger node** connected to all nodes
- **Error logger** writing to `workflow_executions` table
- **Alert node** sending Slack/email on critical failures

```sql
-- Error logging query (use in every workflow's error handler)
INSERT INTO workflow_executions 
  (workflow_name, node_name, status, error_message, started_at)
VALUES 
  ('{{ $workflow.name }}', '{{ $node.name }}', 'failed', '{{ $json.error }}', NOW());
```

### 5.3 AI Agent Response Validation
Always validate AI agent JSON before writing to DB:
```javascript
// In n8n Code node after AI agent
const response = JSON.parse($json.content[0].text);

// Validate required fields
if (!response.action || !Array.isArray(response.questions)) {
  throw new Error('Invalid AI agent response structure');
}

return [{ json: response }];
```

### 5.4 Rate Limits to Respect
| Service | Limit | n8n Implementation |
|---|---|---|
| Claude API | 50 req/min | Add Wait node (2s) between batches |
| LinkedIn | 100 req/day | Code node counter in DB |
| Apollo.io | 50 req/day (free) | Cache results in companies table |
| Gmail SMTP | 500 emails/day | Track in performance_metrics |

---

## 6. COPILOT PROMPT PATTERNS

Use these prompt templates when working in VS Code with Copilot:

```
// For n8n node configuration:
"Write an n8n HTTP Request node body that calls Claude API 
 to analyze job descriptions and return a JSON score and custom CV sections"

// For database queries:  
"Write a PostgreSQL query that fetches the top 5 achievement stories
 from knowledge_base ordered by relevance_score, filtered by industry = 'fintech'"

// For error handling:
"Add error handling to this n8n workflow that logs failures 
 to the workflow_executions table and sends a Slack alert"

// For AI prompts:
"Improve this Claude system prompt to extract more specific 
 quantified metrics from product management stories"
```

---

## 7. DEPLOYMENT CHECKLIST

- [ ] PostgreSQL 15+ installed and running on Windows
- [ ] Database `ravinder_job_search` created with all tables
- [ ] Seed data loaded (user_profile, 4 achievement stories)
- [ ] n8n self-hosted running at localhost:5678
- [ ] Claude API key configured in n8n credentials
- [ ] PostgreSQL credential configured in n8n
- [ ] Workflow 4 built and tested (question generation)
- [ ] Workflow 1 built and tested (job scraping + scoring)
- [ ] Workflow 2 built and tested (company discovery)
- [ ] Workflow 3 built and tested (social monitoring)
- [ ] All workflows connected to shared database
- [ ] Error handling nodes in all workflows
- [ ] Performance dashboard query working
- [ ] Daily schedule triggers configured

---

*Last updated: May 2025 | Project: Agentic AI Job Search System | Owner: Ravinder Kumar*