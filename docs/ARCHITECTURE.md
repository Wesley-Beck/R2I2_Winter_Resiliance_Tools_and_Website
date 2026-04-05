# WUP Wildfire Risk Explorer — Architecture & Roadmap

## Current Architecture (Static)

```
Browser (index.html)
  |
  |-- JS app (Leaflet map, PapaParse CSV, binary .bin loader)
  |-- Static files served from ./website/
  |-- Data from ./data/output/{year}/{month}/web/{variable}.bin
  |
  v
S3 (NOAA AORC v1.1)  <-- Python CLI fetches, processes, writes .bin
```

**Performance baseline (28,408 grid points):**
- S3 fetch: 4.8s/day (87.5% of pipeline time — I/O bound)
- Fire index compute: 0.63s/day (24h x 28K pts)
- SQLite flush: 2.1s/day
- Web .bin generation: 0.66s/day
- Full month: ~2.5 min with prefetch

## Target Architecture (Server + SQL)

### Phase 1: Local SQLite Server (Near-term)

Replace static file serving with a lightweight Python server that reads
directly from the existing SQLite databases.

```
Browser (SPA)
  |
  |-- fetch('/api/data/{variable}/{year}/{month}?hour=12')
  |-- fetch('/api/fdi-table')
  |-- fetch('/api/article/figures/{id}')
  |
  v
FastAPI / Flask Server
  |
  |-- SQLite per year-month (existing data_YYYY_MM.db files)
  |-- Article content in SQLite (figures, text, metadata)
  |-- Static assets (CSS, JS, article PDFs)
  |
  v
S3 (NOAA AORC) <-- Background worker for new data ingestion
```

**API endpoints:**

```
GET  /api/points                         → points_index.csv as JSON
GET  /api/data/{variable}/{year}/{month} → binary ArrayBuffer (same as .bin)
GET  /api/data/{variable}/{year}/{month}/{day}/{hour} → single-hour slice
GET  /api/availability/{year}            → which months have data
GET  /api/fdi-table                      → dataset capabilities JSON
GET  /api/article                        → article metadata + sections
GET  /api/article/figures/{id}           → figure image (responsive)
GET  /api/references                     → bibliography entries
```

**Database schema additions:**

```sql
-- Article content (new database: article.db)
CREATE TABLE article_sections (
    id INTEGER PRIMARY KEY,
    section_order INTEGER,
    title TEXT,
    content_html TEXT,
    content_markdown TEXT
);

CREATE TABLE figures (
    id INTEGER PRIMARY KEY,
    section_id INTEGER REFERENCES article_sections(id),
    figure_order INTEGER,
    caption TEXT,
    alt_text TEXT,
    image_blob BLOB,        -- full-res image
    thumb_blob BLOB,         -- thumbnail for mobile
    width INTEGER,
    height INTEGER,
    mime_type TEXT DEFAULT 'image/png'
);

CREATE TABLE references (
    id INTEGER PRIMARY KEY,
    cite_key TEXT UNIQUE,    -- e.g. "VanWagner1987"
    authors TEXT,
    year INTEGER,
    title TEXT,
    journal TEXT,
    doi TEXT,
    url TEXT,
    bibtex TEXT
);

CREATE TABLE dataset_capabilities (
    dataset_key TEXT PRIMARY KEY,
    name TEXT,
    category TEXT,
    spatial_resolution TEXT,
    temporal_resolution TEXT,
    period TEXT,
    has_temperature BOOLEAN,
    has_humidity BOOLEAN,
    has_wind BOOLEAN,
    has_precipitation BOOLEAN,
    has_radiation BOOLEAN,
    has_pressure BOOLEAN,
    can_compute_fwi BOOLEAN,
    can_compute_nfdrs BOOLEAN,
    can_compute_fpi BOOLEAN,
    notes TEXT
);
```

### Phase 2: PostgreSQL + Cloud Deploy (Future)

For production deployment with multiple users:

```
Browser (SPA)
  |
  v
CDN (CloudFront / Cloudflare)
  |
  v
FastAPI on EC2/ECS/Lambda
  |
  |-- PostgreSQL (RDS) for article content + metadata
  |-- S3 for binary climate data (.bin files)
  |-- Redis for session caching (optional)
  |
  v
Background Workers
  |-- Climate data ingestion from S3/API sources
  |-- Fire index computation pipeline
  |-- Figure generation / re-rendering
```

### Phase 3: Full Article Website

Website tabs:
1. **Explorer** — Current interactive map + fire index visualization
2. **Reference** — Dataset capability table (implemented)
3. **Article** — Full research article with:
   - Responsive text layout (adapts to window size and platform)
   - Inline interactive figures (click to enlarge, pinch to zoom)
   - Figures stored in SQL, served at appropriate resolution
   - Citation links to reference list
4. **Methods** — Detailed methodology with code examples
5. **Data** — Download links, API documentation, data dictionaries

### Responsive Figure Serving

```python
@app.get("/api/article/figures/{figure_id}")
async def get_figure(figure_id: int, width: int = None, format: str = "png"):
    """Serve figure at appropriate size for the client viewport."""
    fig = db.get_figure(figure_id)
    if width and width < fig.width:
        # Serve thumbnail or dynamically resize
        return Response(content=fig.thumb_blob, media_type=fig.mime_type)
    return Response(content=fig.image_blob, media_type=fig.mime_type)
```

## Migration Path

### Step 1: Add FastAPI server wrapper (minimal changes)
- `server/app.py` — FastAPI app that serves existing .bin files via API
- `server/models.py` — SQLAlchemy models for article content
- No changes to existing extraction pipeline

### Step 2: Migrate article content to SQL
- Import article text as markdown sections
- Store figures as BLOBs with metadata
- Build reference/bibliography table from BibTeX

### Step 3: Update frontend to use API
- Replace static .bin file paths with `/api/data/...` endpoints
- Add article rendering components
- Add responsive figure viewer

### Step 4: Deploy
- Dockerfile for containerized deployment
- docker-compose.yml with app + DB
- GitHub Actions CI/CD pipeline

## Data Flow Summary

```
NOAA S3 ─── aorc-tools extract ───▶ SQLite (.db) ──▶ Web (.bin)
                                          │                │
                                          ▼                ▼
                                   FastAPI server    Static serving
                                          │          (current)
                                          ▼
                                    Browser SPA
                                    (Explorer +
                                     Reference +
                                     Article)
```
