# my-vercel-site

Static site for **Cancer Clinical Trials**, deployed on Vercel.

## Pages
- `index.html` — choose a cancer type
- `trials.html` — open trials grouped by distance from the user (postal code / city, worldwide), live from **ClinicalTrials.gov** (v2 API, client-side), with an optional **precision-match** patient profile (biomarkers, stage, prior lines, ECOG, age, sex)
- `intake.html` — patient/referral intake
- `departments.html` — clinical trials landing
- **`illinois/`** — Illinois cancer research deserts + Access-to-Innovation Index (see below)

## Precision matching (trial finder)

The trials page ranks trials against a patient profile in two tiers:

- **Tier B (rule-based, always on):** parses each trial's written ClinicalTrials.gov eligibility for biomarker inclusion/exclusion, sex, age, ECOG, stage, and line-of-therapy cues → Strong / Possible / Likely-ineligible with a "why" breakdown.
- **Tier A (NCI structured, optional):** upgrades trials using *structured* biomarker eligibility (gene/variant) from the **NCI Clinical Trials Search API**, shown as a **★ NCI structured** badge.
- **Tier C (Claude reasoning, optional):** a per-trial **🤖 AI eligibility check** button sends the trial's full written eligibility + the patient profile to **Claude** (`claude-opus-4-8`, structured output) for a reasoned *Likely eligible / Possibly eligible / Likely ineligible* verdict with a "why" breakdown — catching nuances (e.g. exclusion criteria) that keyword matching misses.

### Enabling Tier A
1. Get a free key at <https://clinicaltrialsapi.cancer.gov> → **Get API Key**.
2. In the Vercel project: **Settings → Environment Variables → add `NCI_API_KEY`**, then redeploy.
3. `api/nci-trials.js` is a serverless proxy that holds the key server-side; the front-end calls `/api/nci-trials`. With no key set it returns `{configured:false}` and the page falls back to Tier B (no breakage).

### Enabling Tier C
1. Get an Anthropic API key at <https://console.anthropic.com>.
2. In the Vercel project: **Settings → Environment Variables → add `ANTHROPIC_API_KEY`**, then redeploy.
3. `api/match.js` is a serverless proxy that holds the key server-side and calls the Anthropic Messages API. With no key set it returns `{configured:false}` and the button shows a hint instead of failing.

All matching is preliminary decision support — final eligibility is confirmed by the study team.

## Illinois Access-to-Innovation Index (`/illinois/`)

An interactive county-level access-to-care model for Illinois oncology, built from the
"Illinois Cancer Data Analysis" concept. It combines four layers into one map:

1. **Cancer burden** — estimated annual cases per county
2. **Population & density** — real U.S. Census figures + county geometry (FIPS 17)
3. **Trial centers** — real Illinois oncology centers, geocoded
4. **Geographic accessibility** — drive time and trials reachable within 30/60/90 min

These roll up into an **Access-to-Innovation Index** that ranks counties by *unmet need*
(high cancer burden + poor trial access) — surfacing the state's research deserts.

### Files
- `illinois/index.html` — the dashboard (Leaflet choropleth + rankings table)
- `illinois/data/counties.json` — derived per-county dataset (generated)
- `illinois/data/centers.json` — Illinois cancer/trial centers
- `illinois/data/il-counties.geojson` — county boundaries (Census, filtered to Illinois)
- `illinois/build_data.py` — regenerates `counties.json` from source inputs

### Data provenance
| Field | Source |
|---|---|
| Population, land area, density, geometry | **Real** — U.S. Census |
| Cancer center locations | **Real** — geocoded facilities |
| Cancer incidence | **Estimate** — statewide age-adjusted rate × population |
| Drive time / distance | **Estimate** — straight-line × road factor |
| Per-center active-trial counts | **Placeholder** — wire to ClinicalTrials.gov |

To load true county incidence, replace the rate block in `build_data.py` with an
Illinois State Cancer Registry (ISCR) lookup keyed by FIPS, then re-run the script.
This is a planning prototype — not clinical or navigational advice.
