# FOODWAYS — Shared Heritage by Taste

> An open digital research and mapping system for culinary heritage, foodways, provenance, and AI-assisted historical exploration.
>
> Built by **Angga Conni Saputra**

Foodways is a browser-based heritage intelligence application for documenting, mapping, exploring, and researching culinary traditions and the relationships that connect them across places and time.

The project combines a lightweight static web frontend with **Supabase** for live data and authentication, while repository-hosted JSON layers provide reproducible research and synchronization outputs.

## ✨ What Foodways Does

### 🗺️ Culinary Heritage Mapping
Foodways uses **Leaflet** to visualize culinary heritage records geographically. Records can include:

- current food location
- probable/original food source
- geographic coordinates
- optional distribution polygons
- connection types such as Trade, Migration, or Colonialism

The map is intended to support exploration of foodways as spatial cultural relationships.

### 📊 Culinary Intelligence Dashboard
The dashboard provides a live snapshot of the current inventory, including:

- total food records
- country coverage
- mapped-data coverage
- research/evidence coverage
- UNESCO-related status
- data-readiness indicators
- analytical charts and tables

### 🧭 Timeline & Trade Routes
Foodways includes an **AI-assisted historical research layer** driven by:

`foodways_timeline_research.json`

This layer can surface:

- earliest supported references
- probable origins
- date evidence
- route hypotheses
- confidence scores
- research warnings/errors
- geographic research corridors
- human cross-check status

**Important:** route overlays and AI-generated historical interpretations are explicitly treated as research hypotheses. They are not automatically presented as verified historical reconstruction.

### 🛰️ AI Culinary Radar
Foodways can load a culinary subset synchronized from the wider **ICH-Radar** workflow through:

`ai_culinary.json`

The AI-assisted map helps researchers discover culinary heritage signals, inspect source material, and—when authorized—review and curate promising records before saving them into the main Foodways inventory.

### 🔐 Authentication & Contributor Access
The current web application uses **Supabase Auth** with **Google OAuth**.

After login, the application checks the `is_foodways_admin` database function to determine whether the current user has Foodways Admin permission.

That means:

- **Guest:** explore public data
- **Signed-in Viewer:** authenticated, but without editing privileges
- **Admin:** CRUD, curation, and contributor tools enabled

The frontend uses a Supabase **publishable client key**. Server-side secrets/service-role keys should never be embedded in the browser.

## 🛠️ Data Management

The main live dataset is stored in the Supabase table:

`Heritage Foodways`

The current data model includes fields such as:

`id`, `food_name`, `country`, `lat`, `lng`, `description`, `geometry_json`, `unesco_status`, `research_links`, `image_url`, `youtube_url`, `origin_food_name`, `origin_country`, `origin_lat`, `origin_lng`, `connection_type`

Admins can create, edit, and delete records from the web interface.

### Geographic editing

The application includes geographic picking and polygon editing so contributors can capture more than a single point.

### Research provenance

Research links are stored directly with records, while the timeline research layer keeps its own evidence and uncertainty fields. This separation helps distinguish the live inventory from exploratory research.

## 📤 Export & Reporting

Foodways provides several output paths:

### CSV
Download the current dataset as CSV for spreadsheet analysis and archival snapshots.

### DCMI-style metadata
Generate Dublin Core-oriented metadata for digital-library and documentation workflows.

### GeoJSON
Produce GIS-compatible spatial data for tools such as:

- ArcGIS
- QGIS
- other GeoJSON-capable GIS applications

### PDF
Generate a printable food profile containing narrative, images, lineage information, and map snapshots.

The PDF workflow uses browser-side rendering with **html2pdf.js** and **html2canvas**, avoiding a dedicated reporting server.

## 📱 Desktop & Mobile

The repository contains two client interfaces:

- `index.html` — full desktop/research interface
- `mobile.html` — simplified mobile interface

The desktop page detects mobile-sized devices and redirects them to the dedicated mobile application.

The mobile version provides a compact:

- dashboard
- search interface
- Leaflet map
- food detail view
- admin entry workflow
- profile/auth view
- PDF reporting path

## 🧩 Repository Structure

| File | Purpose |
| --- | --- |
| `index.html` | Main desktop Foodways application |
| `mobile.html` | Mobile-optimized application |
| `guides.json` | In-app help/manual content |
| `ai_culinary.json` | Culinary signals synchronized from ICH-Radar |
| `foodways_timeline_research.json` | AI-assisted historical/timeline research output |
| `foodways_timeline_cache.json` | Research/cache support data |
| `radar_culinary_sync.py` | Culinary data synchronization logic |
| `timeline_research.py` | Historical timeline research pipeline |
| `keepalive.py` | Supabase keepalive utility |
| `requirements.txt` | Python dependencies |
| `.github/workflows/sync-ich-radar-culinary.yml` | Automated culinary synchronization |
| `.github/workflows/research-foodways-timeline.yml` | Automated timeline research workflow |
| `.github/workflows/supabase-keepalive.yml` | Scheduled Supabase keepalive workflow |
| `assets/` | Screenshots and project assets |

## 🔬 Research Architecture

Foodways now operates as a layered research system rather than a simple CRUD map:

**Live heritage inventory**
→ Supabase `Heritage Foodways`

**AI discovery layer**
→ `ai_culinary.json`

**Historical research layer**
→ `foodways_timeline_research.json`

**Human curation**
→ Admin review and Supabase save

This creates a useful separation between:

1. **discovery**
2. **research**
3. **curation**
4. **published inventory**

That separation is especially important for heritage data where evidence quality and uncertainty matter.

## 🤖 AI-Assisted Research Disclaimer

The timeline/research layer may contain:

- machine-discovered sources
- probable origins
- inferred route relationships
- confidence scores
- incomplete records
- unresolved contradictions

These outputs are intended to **accelerate human research**, not replace it.

A research hypothesis should be independently checked before being treated as a historical fact, publication claim, policy statement, or heritage determination.

## 🚀 Running the Project

Foodways is intentionally lightweight.

You do not need a Node.js build process for the main web client.

For local development, you can:

1. Clone the repository.
2. Serve it using a static web server such as VS Code Live Server.
3. Open the site in a modern browser.

GitHub Pages is also suitable for the static frontend.

### Why use a static architecture?

The project intentionally avoids a heavy application build stack.

Benefits include:

- low deployment complexity
- easy source inspection
- simple hosting
- easy portability
- low maintenance overhead
- browser-native extensibility

## 🔧 Supabase Configuration

The production client is configured in the HTML application using the Supabase project URL and publishable browser key.

For your own deployment:

1. Create a Supabase project.
2. Create the `Heritage Foodways` table using the required fields.
3. Configure Supabase Auth and Google OAuth.
4. Implement the `is_foodways_admin` authorization function.
5. Configure the appropriate Row Level Security (RLS) policies.
6. Update the client configuration in the HTML application.
7. Configure the OAuth redirect URL for your deployment domain.

**Security note:** a publishable client key is expected to be visible in browser code. A Supabase service-role key is not.

## 🔄 Automation

The repository includes GitHub Actions for:

- keeping the Supabase project active
- synchronizing culinary research from ICH-Radar
- generating/updating Foodways timeline research

This allows the application to remain largely static while the research datasets can evolve through scheduled automation.

## 📚 In-App Guide

The complete in-app manual is maintained in:

`guides.json`

It is designed to explain both everyday usage and the research philosophy of Foodways, including the distinction between curated data and AI-assisted hypotheses.

## 🤝 Contribution

Contributions are welcome through:

- GitHub Issues
- Pull Requests
- research feedback
- source-quality corrections
- UI/UX improvements
- data model improvements
- documentation improvements

For heritage research, please preserve source provenance and clearly distinguish evidence from interpretation.

## 🛡️ Security & Integrity

Foodways is open source so that users can inspect how the application works.

The browser application can be audited directly because the main client logic is published in the repository.

However, open source does **not** automatically mean every deployment is secure. Security ultimately depends on:

- Supabase RLS policies
- authentication configuration
- authorization logic
- OAuth redirect settings
- database permissions
- careful handling of private credentials

Never expose service-role credentials or other privileged secrets in client-side code.

## 📄 License & Usage

See [LICENSE](LICENSE) for the current license terms.

The project is intended for social impact, education, heritage research, and responsible digital experimentation. Commercial or derivative use should follow the actual license terms rather than relying on informal statements in earlier documentation.

## 📬 Contact

**Angga Conni Saputra**  
Governance Reform & Digital System Consultant

LinkedIn: https://www.linkedin.com/in/anggaconni/
