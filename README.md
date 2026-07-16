# my-vercel-site

Static site for **OSF Cancer Clinical Trials**, deployed on Vercel.

## Pages
- `index.html` — choose a cancer type
- `trials.html` — searchable trial list (reads the OSF trials CSV)
- `intake.html` — patient/referral intake
- `departments.html` — clinical trials landing
- **`illinois/`** — Illinois Access-to-Innovation Index (see below)

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
