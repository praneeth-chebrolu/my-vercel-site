# Precision Trial-Matching Module

A drop-in module that finds open cancer clinical trials near a patient and ranks them
against a patient profile — with a tumor-specific biomarker dropdown and three optional
matching tiers. Built for **zero-config Vercel**: a static page at the project root plus
serverless functions under `api/`.

## Files

| File | Role | Key? |
|---|---|---|
| `trials.html` | The entire UI — live ClinicalTrials.gov search, distance grouping, precision-match panel, nearest-site "I'm interested" modal. | — |
| `api/biomarker-data.json` | Curated per-tumor biomarker dataset (drives the dropdown). | — |
| `api/biomarkers.js` | `GET /api/biomarkers?cancer=…` → that tumor's markers. Deterministic, no external calls. | — |
| `api/match.js` | **Tier C** — Claude reads full eligibility vs. the profile (assess + adversarial verify). | `ANTHROPIC_API_KEY` |
| `api/nci-trials.js` | **Tier A** — optional structured biomarker eligibility from NCI. | `NCI_API_KEY` |
| `vercel.json` | Gives `api/match.js` a 30s max duration for the Claude call. | — |

## How it works

### Data flow
1. The browser queries **ClinicalTrials.gov v2** directly (client-side) by disease group and
   groups results by distance from the patient's postal code / city.
2. Picking a cancer type calls **`/api/biomarkers`**, which returns that tumor's markers from
   the bundled dataset. The precision panel renders them as a **dropdown → removable chips**.
3. Matching runs in tiers:
   - **Tier B (always on):** rule-based scoring in `trials.html` — parses each trial's written
     eligibility for biomarker in/exclusion, sex, age, ECOG, stage, and line-of-therapy.
   - **Tier A (optional):** `api/nci-trials.js` adds *structured* gene/variant eligibility
     from the NCI Clinical Trials Search API (`★ NCI structured` badge).
   - **Tier C (optional):** `api/match.js` sends the trial's full eligibility + the profile to
     **Claude** for a reasoned verdict; an `eligible` verdict triggers a second **adversarial
     verify** pass that can only hold (`✓ double-checked`) or downgrade it.
4. **"I'm interested"** opens the nearest recruiting site with its address, contact, and a
   directions link.

### Biomarker dataset
`api/biomarker-data.json` is keyed by cancer label; each entry is a marker:

```json
{ "gene": "EGFR", "aliases": ["ERBB1"], "tier": "A",
  "alterations": ["Exon 19 deletion", "L858R", "T790M"],
  "onImpact": true, "onAccess": true }
```

- **tier** — `A` = FDA / standard-of-care, `B` = guideline / emerging.
- Tumor-agnostic FDA approvals (**NTRK** fusions, **MSI-H/dMMR**, **TMB-High**) are appended
  to every tumor automatically by `api/biomarkers.js` (no need to repeat them per cancer).
- To add a cancer or marker, just edit the JSON — the API and UI pick it up with no code change.

> The dataset is seeded from FDA-recognized and NCCN/CAP-guideline biomarkers; tiers and
> MSK-IMPACT/MSK-ACCESS flags are **indicative for a prototype**, not a certified report.
> Refresh it from an open source (CIViC, CC0) or a licensed OncoKB feed if you need
> authoritative, continuously-updated curation.

## Install (drop into a Vercel project)

1. Copy `trials.html`, the `api/` folder, and `vercel.json` to your project root.
2. Deploy to Vercel (zero config — `api/*.js` become functions automatically).
3. Open `/trials.html`. It works immediately; the two keys below are optional.

### Optional keys (Vercel → Settings → Environment Variables → redeploy)
- `ANTHROPIC_API_KEY` — enables **Tier C** (Claude eligibility reasoning). Without it,
  `api/match.js` returns `{configured:false}` and the UI shows a hint instead of erroring.
- `NCI_API_KEY` — enables **Tier A** (NCI structured biomarkers). Get one at
  <https://clinicaltrialsapi.cancer.gov>. Without it the page uses Tier B only.

Every tier degrades gracefully: with no keys you still get live trials, distance grouping,
the tumor-specific dropdown, and Tier B rule-based matching.

## Key functions in `trials.html`
- `loadBiomarkers()` / `renderMarkers()` — fetch + render the tumor-specific dropdown & chips.
- `computeMatch(t, p)` — Tier B rule-based eligibility scoring.
- `aiCheck()` / `aiCheckTop()` — Tier C single + shortlist calls (with the verify pass).
- `classify()` / `nearestSite()` / `openInterest()` — distance grouping + nearest-site modal.

_All matching is preliminary decision support — final eligibility is confirmed by the study team._
