# NexusFlow AI — WhatsApp Sales & Lead Qualification MVP

An AI-powered WhatsApp-style sales concierge for real-estate developers. Built as a
low-cost, free-tier-friendly MVP for client demos — not enterprise scale (yet).

It simulates a WhatsApp conversation with an AI sales concierge that:
- Understands English, Hindi, and Hinglish (including spelling mistakes)
- Extracts structured lead data (budget, configuration, timeline, phone, etc.)
- Scores buyer intent deterministically as 🔥 HOT / 🟡 WARM / 🔵 COLD
- Answers only from real project knowledge (RAG over a demo project + optional PDF upload) — never invents prices or inventory
- Handles common objections (price, "decide later", "send on WhatsApp", site visit requests)
- Surfaces everything on an Executive Lead Dashboard with KPIs, a funnel, and a simulated sales-alert panel

## Architecture

```
Streamlit UI (landing / chat simulator / dashboard)
        |
Python backend (SalesAgent: conversation + extraction + scoring + RAG)
        |
   Groq LLM   |   FAISS (local RAG)   |   Supabase / SQLite (leads + chat history)
```

- **LLM:** Groq (`llama-3.3-70b-versatile`, with `llama-3.1-8b-instant` as an automatic
  fallback), abstracted behind `LLMProvider` so OpenAI/Gemini/Anthropic can be added later
  without touching the agent code.
- **Database:** Supabase Postgres if configured, otherwise a local SQLite file — the
  app never crashes because a database is unavailable.
- **RAG:** local `sentence-transformers` embeddings + `faiss-cpu`, no server, no paid
  vector DB. Auto-bootstraps from the demo project JSON on first run; you can also
  upload a real PDF brochure from the sidebar.
- **Messaging:** `channels/` abstracts message delivery — only a Streamlit-based
  `DemoChannel` is implemented today; `MetaWhatsAppChannel` / `TwilioChannel` /
  `GupshupChannel` are stubs for after a client signs a pilot.

## Project layout

```
app.py                  Streamlit entrypoint
config/settings.py      Env/secrets loader
channels/                MessageChannel abstraction (demo + future stubs)
agents/                  Sales agent orchestration, prompts, lead extraction
llm/                     LLMProvider abstraction + Groq implementation
rag/                     FAISS vector store, PDF ingestion, retriever
database/                Supabase + SQLite backends, shared queries.py, schema.sql
scoring/                 Deterministic HOT/WARM/COLD scoring engine
ui/                      Landing page, chat simulator, dashboard, shared components
data/demo_project.json   Sample "Nexus Heights" project data (clearly marked as demo data)
tests/                   pytest unit tests
```

## Local setup

1. **Install dependencies** (Python 3.10+ recommended):
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and set `GROQ_API_KEY` (free key at https://console.groq.com).
   Leave `SUPABASE_URL`/`SUPABASE_KEY` blank to run entirely on local SQLite —
   this is the default (`DEMO_MODE=true`).
3. **Run the app:**
   ```bash
   streamlit run app.py
   ```
4. Click **Start Demo** and chat in English, Hindi, or Hinglish.

## Supabase setup (optional, for persistent multi-session demos)

1. Create a free project at https://supabase.com.
2. Open **SQL Editor → New query**, paste the contents of `database/schema.sql`, and run it.
3. Copy your Project URL and publishable/`anon` API key into `.env` as `SUPABASE_URL` / `SUPABASE_KEY`.
4. Set `DEMO_MODE=false` so the app prefers Supabase over local SQLite.
5. **Row Level Security:** new Supabase projects enable RLS by default on tables, which
   blocks writes from the publishable key. For the demo phase (no end-user auth yet),
   disable RLS on the four tables:
   ```sql
   alter table business_clients disable row level security;
   alter table client_projects disable row level security;
   alter table leads disable row level security;
   alter table chat_messages disable row level security;
   ```
   Before a real client-facing launch with the WhatsApp API, replace this with proper
   RLS policies (or route writes through a service-role key server-side) instead of
   leaving the tables open.

If Supabase is unreachable at runtime, the app automatically falls back to local
storage for that session and shows a non-blocking warning banner — it will not crash.

## Free deployment — Streamlit Community Cloud

Hugging Face Spaces deprecated free Streamlit/Docker hosting in 2026 (now requires a
paid PRO plan), so Streamlit Community Cloud is the recommended free option — it
natively hosts Streamlit apps with no Docker step, deploying straight from GitHub.

1. Push this repository to a GitHub repo (public repos are unlimited on the free tier;
   private is limited to one app).
2. Go to https://share.streamlit.io, sign in with GitHub, and click **New app**.
3. Point it at your repo/branch, with `app.py` as the entrypoint file.
4. Before (or right after) deploying, open **Advanced settings → Secrets** and paste:
   ```toml
   GROQ_API_KEY = "..."
   GROQ_MODEL = "llama-3.3-70b-versatile"
   SUPABASE_URL = "..."
   SUPABASE_KEY = "..."
   DEMO_MODE = "false"
   ```
5. `config/settings.py` reads these via `st.secrets`/environment automatically — no code
   changes needed versus local `.env` usage.
6. The free tier has ~1GB memory and apps sleep after 12h without traffic (a visit wakes
   them back up in a few seconds) — fine for demo purposes. The FAISS RAG index
   auto-rebuilds from `data/demo_project.json` on every cold start, so no manual
   re-upload is needed after a sleep/wake cycle.
7. No Docker/Kubernetes/custom infra required — Community Cloud hosts it for free.

## Approximate monthly cost

| Component | Cost while on free tiers |
|---|---|
| Groq API | Free tier (rate-limited, generous for demos) |
| Supabase | Free tier (500MB DB, more than enough for 10-15 demo clients) |
| Streamlit / Hugging Face Spaces hosting | Free |
| Embeddings (sentence-transformers) | Free, runs locally |
| **Total** | **$0/month** for the demo phase |

Costs only appear once you add: paid Groq tier (for higher volume), a real WhatsApp
Business API (Meta/Twilio/Gupshup — usually pay-per-conversation), or Supabase paid
tier (beyond free-tier storage/traffic limits).

## What's demo data vs. real

`data/demo_project.json` is clearly marked `_DEMO_DATA_NOTICE` and contains the sample
"Nexus Heights" project. Replace this file (or upload a PDF brochure from the sidebar)
with a real client's project details before any live client-facing deployment.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Chat replies with "having trouble connecting…" | `GROQ_API_KEY` missing/invalid, or Groq API down | Check `.env` / Space secrets; verify the key at console.groq.com |
| Sidebar shows "🧪 DEMO MODE — Local Storage" unexpectedly | Supabase not configured, or `DEMO_MODE=true` | Set `SUPABASE_URL`/`SUPABASE_KEY` and `DEMO_MODE=false` |
| Dashboard shows "No leads yet" | No conversations have happened yet this session/database | Go to Chat Simulator and have a conversation |
| AI says it can't answer a question | RAG found no matching knowledge (by design — prevents hallucination) | Upload the real brochure PDF or extend `data/demo_project.json` |
| PDF upload fails | Corrupt/unsupported PDF | Try a different PDF or re-export it |
| App shows a generic "Something went wrong" | Uncaught error (see server logs) | Check the terminal/Space logs for the underlying exception |

## Testing

Run the automated test suite:
```bash
pytest
```

See the plan/troubleshooting table above for the manual pre-demo smoke test covering
English/Hindi/Hinglish conversations, objections, site visits, and failure scenarios
(missing API key, invalid JSON, DB failure, etc.).

## What to build only after the first paying client

- Real WhatsApp Business API integration (`MetaWhatsAppChannel`/`TwilioChannel`/`GupshupChannel`)
- Multi-tenant support (`business_clients` already modeled in the schema, just unused by the demo UI)
- Authentication/RBAC on the dashboard
- Automated follow-ups and CRM integrations
- A paid vector DB or managed embeddings service, if knowledge-base scale demands it
- Swapping/adding LLM providers (OpenAI/Gemini/Anthropic) via the existing `LLMProvider` interface

## Upgrade roadmap

```
MVP (this repo)
 -> Real WhatsApp Business API channel
 -> Multi-tenant SaaS (business_clients / client_projects already modeled)
 -> CRM integration + automated follow-ups
 -> Sales team alerts via real channels (Slack/Email/WhatsApp)
 -> Executive analytics (Power BI / richer dashboards)
 -> Enterprise AI sales platform
```
