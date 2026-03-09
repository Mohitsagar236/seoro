# Seoro — Intent Extraction Prototype

> Converts raw meeting audio into structured intent data.  
> Audio → Transcript → Events → Intents → Integrations & Data Fusion.

---

## Architecture Overview

```
┌──────────────┐     ┌─────────────────┐     ┌────────────────────┐
│  Audio Input  │────▶│   Deepgram API   │────▶│  Raw Transcript    │
│  (file/URL)   │     │   (Nova-2 STT)   │     │  + Speaker Labels  │
└──────────────┘     └─────────────────┘     └────────┬───────────┘
                                                       │
                                                       ▼
                                             ┌────────────────────┐
                                             │  OpenAI GPT-4o-mini│
                                             │  Event Extraction  │
                                             └────────┬───────────┘
                                                       │
                                                       ▼
                                             ┌────────────────────┐
                                             │  OpenAI GPT-4o-mini│
                                             │  Intent Classifier │
                                             └────────┬───────────┘
                                                       │
                                             ┌────────┴───────────┐
                                             │  OpenAI GPT-4o-mini│
                                             │ Integrations &     │
                                             │ Data Fusion Analysis│
                                             └────────┬───────────┘
                                                       │
                                                       ▼
                                             ┌────────────────────┐
                                             │     Supabase       │
                                             │  (PostgreSQL DB)   │
                                             │  meetings/events/  │
                                             │  intents/insights  │
                                             └────────┬───────────┘
                                                       │
                                                       ▼
                                             ┌────────────────────┐
                                             │   FastAPI REST     │
                                             │  GET /meeting-     │
                                             │   intent/{id}      │
                                             └────────────────────┘
```

## Tech Stack

| Layer               | Technology           | Why                                        |
|---------------------|----------------------|--------------------------------------------|
| API Framework       | FastAPI              | Async, auto-docs, Pydantic validation       |
| Transcription       | Deepgram Nova-2      | Fast, accurate, speaker diarization, topics |
| Event Extraction    | OpenAI GPT-4o-mini   | Structured JSON extraction from text        |
| Intent Classify     | OpenAI GPT-4o-mini   | Priority + confidence scoring               |
| Integrations        | OpenAI GPT-4o-mini   | System integration analysis from events     |
| Data Fusion         | OpenAI GPT-4o-mini   | Multi-source data fusion analysis           |
| Database            | Supabase (PostgreSQL)| Managed, real-time, auth, REST built-in     |
| Containerization    | Docker               | Reproducible, deployable                    |

## Project Structure

```
seoro/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app factory
│   ├── config.py                # Pydantic settings (env vars)
│   ├── logger.py                # Structured logging (structlog)
│   ├── db/
│   │   ├── client.py            # Supabase client singleton
│   │   ├── repository.py        # CRUD operations
│   │   └── migrations/
│   │       └── 001_init.sql     # Full schema (meetings/events/intents/integration/data-fusion)
│   ├── schemas/
│   │   └── models.py            # Pydantic request/response models
│   ├── services/
│   │   ├── transcription.py     # Deepgram speech-to-text
│   │   ├── event_extraction.py  # GPT-based event extraction
│   │   ├── intent_classification.py  # GPT-based intent classification
│   │   ├── integrations.py      # GPT-based integration analysis
│   │   ├── data_fusion.py       # GPT-based data-fusion analysis
│   │   └── pipeline.py          # Orchestrator (full pipeline)
│   └── routes/
│       ├── meetings.py          # Meeting API endpoints
│       └── health.py            # Health check
├── tests/
│   ├── test_schemas.py          # Schema validation tests
│   └── test_api.py              # API endpoint tests
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quick Start

### 1. Prerequisites

- Python 3.11+
- [Deepgram API key](https://console.deepgram.com/) (free tier available)
- [OpenAI API key](https://platform.openai.com/)
- [Supabase project](https://supabase.com/) (free tier available)

### 2. Setup Database

1. Create a new Supabase project
2. Go to **SQL Editor** in the Supabase dashboard
3. Paste and run the contents of `app/db/migrations/001_init.sql`

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual keys:
#   SUPABASE_URL=https://xxx.supabase.co
#   SUPABASE_KEY=your-key
#   DEEPGRAM_API_KEY=your-key
#   OPENAI_API_KEY=sk-xxx
```

### 4. Install & Run

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --port 8000
```

### 5. Docker (Alternative)

```bash
docker compose up --build
```

## API Endpoints

| Method | Endpoint                                     | Description                           |
|--------|----------------------------------------------|---------------------------------------|
| GET    | `/health`                                    | Health check                          |
| POST   | `/api/v1/meetings/upload`                    | Upload audio file → start pipeline    |
| POST   | `/api/v1/meetings/process-url`               | Submit audio URL → start pipeline     |
| GET    | `/api/v1/meetings`                           | List all meetings                     |
| GET    | `/api/v1/meetings/{meeting_id}`              | Full meeting detail with transcript   |
| GET    | `/api/v1/meetings/{meeting_id}/integrations` | Integration insights for a meeting    |
| GET    | `/api/v1/meetings/{meeting_id}/data-fusion`  | Data-fusion insights for a meeting    |
| GET    | `/meeting-intent/{meeting_id}`               | **Structured intent response (spec)** |
| GET    | `/api/v1/meeting-intent/{meeting_id}`        | Structured intent response (versioned)|

### Interactive API Docs

Once running, visit: **http://localhost:8000/docs** (Swagger UI)

### Example Usage

```bash
# Upload an audio file
curl -X POST http://localhost:8000/api/v1/meetings/upload \
  -F "file=@meeting_recording.mp3" \
  -F "title=Q4 Planning Meeting"

# Response (202 Accepted):
# {
#   "meeting_id": "a1b2c3d4-...",
#   "status": "pending",
#   "message": "Pipeline started. Poll GET /api/v1/meetings/{meeting_id} for progress."
# }

# Check intent results
curl http://localhost:8000/api/v1/meeting-intent/a1b2c3d4-...

# Response:
# {
#   "meeting_id": "a1b2c3d4-...",
#   "title": "Q4 Planning Meeting",
#   "status": "completed",
#   "detected_intents": [
#     {
#       "intent_type": "feature_request",
#       "priority": "high",
#       "confidence": 0.94,
#       "reasoning": "Customer explicitly asked for dark mode."
#     }
#   ],
#   "extracted_events": [
#     {
#       "event_type": "feature_request",
#       "speaker_role": "customer",
#       "topic": "dark mode",
#       "content": "Customer requested dark mode for the mobile app"
#     }
#   ]
# }
```

### Run Tests

```bash
pytest tests/ -v
```

---

## Scaling Analysis (Question 1)

### If 10,000 meetings are processed per day, what becomes bottlenecks?

#### Identified Bottlenecks

| Component            | Bottleneck                                     | Impact             |
|----------------------|------------------------------------------------|--------------------|
| **Deepgram API**     | API rate limits, network I/O per file          | ~3-5 min per file  |
| **OpenAI API**       | Token throughput limits, cost per call          | ~10-30s per call   |
| **Single process**   | Synchronous pipeline blocks on each meeting    | Linear throughput  |
| **File storage**     | Local disk fills up, no redundancy             | Disk I/O ceiling   |
| **Supabase (free)**  | Connection limits, row-level throughput         | DB write contention|

#### Redesigned Pipeline for Scale

```
                    ┌──────────────┐
                    │  API Gateway  │  (Rate limiting, auth)
                    │  (Kong/Nginx) │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Load Balancer│
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼────┐ ┌────▼─────┐ ┌────▼─────┐
        │ API Pod 1│ │ API Pod 2│ │ API Pod N│   (Horizontal scaling)
        └─────┬────┘ └────┬─────┘ └────┬─────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼───────┐
                    │  Message Queue │  (Redis/RabbitMQ/SQS)
                    │  Task Broker   │
                    └──────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
   ┌─────▼──────┐   ┌─────▼──────┐   ┌─────▼──────┐
   │ Worker Pod  │   │ Worker Pod  │   │ Worker Pod  │
   │ (Celery)    │   │ (Celery)    │   │ (Celery)    │
   │             │   │             │   │             │
   │ Transcribe  │   │ Transcribe  │   │ Transcribe  │
   │ Extract     │   │ Extract     │   │ Extract     │
   │ Classify    │   │ Classify    │   │ Classify    │
   └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
         │                 │                 │
         └────────┬────────┴────────┬────────┘
                  │                 │
           ┌──────▼──────┐  ┌──────▼──────┐
           │  Supabase   │  │  Object Store│
           │ (Postgres)  │  │  (S3/GCS)   │
           │  + pgvector │  │  Audio files │
           └─────────────┘  └─────────────┘
```

#### Key Changes for 10K Meetings/Day

1. **Message Queue (Celery + Redis/SQS)**: Decouple API from processing. Upload returns immediately; workers pull jobs asynchronously.

2. **Worker Pool (Horizontal Scaling)**: Run N Celery workers across multiple machines. Each worker processes one meeting independently. Auto-scale based on queue depth.

3. **Batching**: Group small audio files into batches for Deepgram. Batch event/intent extractions into single LLM calls where possible (multiple events per prompt).

4. **Object Storage (S3/GCS)**: Move audio files off local disk to cloud object storage. Workers download on-demand. Lifecycle policies auto-delete after processing.

5. **Connection Pooling (PgBouncer)**: Place a connection pooler in front of Supabase Postgres to handle high write concurrency from workers.

6. **Caching (Redis)**: Cache completed meeting results. The intent endpoint serves from cache on repeat reads.

7. **Async Pipeline Stages**: Split the monolithic pipeline into 3 independent stages (transcribe → extract → classify), each with its own queue. This allows different scaling per stage.

8. **Rate Limit Management**: Implement token bucket / leaky bucket for Deepgram and OpenAI API calls. Use exponential backoff with jitter.

---

## Architecture Diagram (Question 2)

### Seoro Full Data Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SEORO DATA PIPELINE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐                                                   │
│  │  INGESTION   │  Audio upload (file/URL)                         │
│  │  Layer       │  → Validate format, size, duration               │
│  │             │  → Store raw audio in object storage              │
│  │             │  → Emit job to message queue                     │
│  └──────┬──────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                  │
│  │ TRANSCRIPTION │  Deepgram Nova-2 API                            │
│  │  Layer        │  → Speech-to-text with diarization              │
│  │              │  → Word-level timestamps                         │
│  │              │  → Speaker identification                        │
│  │              │  → Store transcript in Supabase                  │
│  └──────┬───────┘                                                  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────┐                                              │
│  │ EVENT EXTRACTION   │  OpenAI GPT-4o                             │
│  │  Layer             │  → Detect feature requests, bugs, feedback │
│  │                   │  → Extract speaker roles, topics            │
│  │                   │  → Map to transcript timestamps             │
│  │                   │  → Store events in Supabase                 │
│  └──────┬────────────┘                                             │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────┐                                              │
│  │ INTENT CLASSIFY    │  OpenAI GPT-4o                             │
│  │  Layer             │  → Categorize: feature/bug/feedback/task   │
│  │                   │  → Assign priority (critical→low)          │
│  │                   │  → Score confidence (0.0–1.0)              │
│  │                   │  → Store intents in Supabase                │
│  └──────┬────────────┘                                             │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────┐                                                   │
│  │  STORAGE     │  Supabase (PostgreSQL)                           │
│  │  Layer       │  → meetings table (metadata, transcript)         │
│  │             │  → events table (structured events)              │
│  │             │  → intents table (classified intents)            │
│  │             │  → Foreign keys, indexes, triggers               │
│  └──────┬──────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────┐                                              │
│  │ VECTORIZATION      │  (Future: pgvector in Supabase)            │
│  │  Layer             │  → Embed events & intents                  │
│  │  (Planned)        │  → Semantic similarity search              │
│  │                   │  → Cross-meeting pattern detection          │
│  └──────┬────────────┘                                             │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────┐                                                   │
│  │  RETRIEVAL   │  FastAPI REST API                                │
│  │  Layer       │  → GET /meeting-intent/{id}                     │
│  │             │  → Full meeting detail with events + intents     │
│  │             │  → Paginated listing                             │
│  │             │  → Swagger/OpenAPI docs at /docs                 │
│  └─────────────┘                                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---


