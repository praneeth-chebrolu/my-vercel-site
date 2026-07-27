// Serverless proxy: cancer-specific biomarkers / tumor markers for precision matching.
// Source of truth = MSK OncoKB (actionable variants + curated genes); assay coverage
// (MSK-IMPACT / MSK-ACCESS) is layered on from cBioPortal public gene panels.
//
// GET /api/biomarkers?cancer=Lung%20cancer
//   -> { configured, cancer, count, genes:[{gene, level, rank, onImpact, onAccess, aliases[], alterations[], tumorAgnostic}], ... }
//
// OncoKB requires a token — set ONCOKB_TOKEN in the Vercel env (register at
// https://www.oncokb.org/account/register; note OncoKB is free for research/academic
// use but COMMERCIAL/clinical use requires a license agreement with MSK).
// With no token the proxy returns { configured:false } and the UI falls back to a
// short list of common pan-cancer markers.

const ONCOKB = "https://www.oncokb.org/api/v1";
const CBIO = "https://www.cbioportal.org/api";
const IMPACT_PANEL = "IMPACT505";
// cBioPortal panel id for MSK-ACCESS varies across releases; try a few, use the first that resolves.
const ACCESS_PANEL_CANDIDATES = ["MSK-ACCESS", "MSK-ACCESS-v1", "ACCESS129", "MSK_ACCESS"];

// Map our UI cancer labels to substrings that appear in OncoKB cancerType names.
// A missing entry => no cancer-specific mapping => UI keeps its common-marker fallback.
const CANCER_KEYWORDS = {
  "Bladder cancer": ["bladder", "urothelial"],
  "Brain cancer": ["glioma", "glioblastoma", "astrocytoma", "oligodendroglioma", "brain"],
  "Breast cancer": ["breast"],
  "Colon & rectal cancer": ["colorectal", "colon", "rectal"],
  "Gastrointestinal cancer": ["colorectal", "gastric", "esophag", "pancrea", "hepatocellular", "biliary", "cholangio", "gastrointestinal stromal", "small bowel"],
  "Gynecologic cancer": ["ovarian", "cervical", "endometrial", "uterine", "vaginal", "vulvar"],
  "Head & neck cancer": ["head and neck"],
  "Kidney cancer": ["renal"],
  "Lung cancer": ["lung"],
  "Prostate cancer": ["prostate"],
  "Skin cancer": ["melanoma", "skin", "merkel"],
  "Testicular cancer": ["germ cell", "testicular"],
};
// Tumor-agnostic buckets in OncoKB — always relevant (e.g. NTRK fusions, MSI-H, TMB-H).
const AGNOSTIC = ["all solid tumors", "all tumors", "all liquid tumors"];

function levelRank(lv) {
  const o = { LEVEL_1: 1, LEVEL_2: 2, LEVEL_3A: 3, LEVEL_3B: 4, LEVEL_4: 5, LEVEL_R1: 6, LEVEL_R2: 7 };
  return o[lv] || 9;
}
const shortLevel = (lv) => (lv || "").replace("LEVEL_", "") || null;

async function oncokbGet(path, token) {
  const r = await fetch(ONCOKB + path, { headers: { Authorization: "Bearer " + token, Accept: "application/json" } });
  if (!r.ok) throw new Error("OncoKB " + r.status);
  return r.json();
}
async function cbioPanel(id) {
  try {
    const r = await fetch(`${CBIO}/gene-panels/${encodeURIComponent(id)}`, { headers: { Accept: "application/json" } });
    if (!r.ok) return null;
    const d = await r.json();
    const genes = (d.genes || []).map((g) => (g.hugoGeneSymbol || "").toUpperCase()).filter(Boolean);
    return genes.length ? new Set(genes) : null;
  } catch (_) { return null; }
}

module.exports = async (req, res) => {
  res.setHeader("Content-Type", "application/json");
  const token = process.env.ONCOKB_TOKEN;
  if (!token) { res.status(200).send(JSON.stringify({ configured: false, genes: [] })); return; }

  const cancer = ((req.query && req.query.cancer) || "").toString();
  const keys = CANCER_KEYWORDS[cancer];
  if (!keys) {
    // Known-but-unmapped (e.g. "Childhood cancer") or empty — let the UI fall back gracefully.
    res.status(200).send(JSON.stringify({ configured: true, cancer, count: 0, genes: [], note: "no cancer-specific mapping" }));
    return;
  }
  const keyList = keys.map((s) => s.toLowerCase());

  try {
    const [actionable, curated, impactSet, accessSet] = await Promise.all([
      oncokbGet("/utils/allActionableVariants", token),
      oncokbGet("/utils/allCuratedGenes?includeEvidence=false", token).catch(() => []),
      cbioPanel(IMPACT_PANEL),
      (async () => { for (const id of ACCESS_PANEL_CANDIDATES) { const s = await cbioPanel(id); if (s) return s; } return null; })(),
    ]);

    const cur = new Map();
    (curated || []).forEach((g) => { const s = (g.hugoSymbol || "").toUpperCase(); if (s) cur.set(s, g); });

    const matches = (ct) => {
      const c = (ct || "").toLowerCase();
      if (AGNOSTIC.some((a) => c.includes(a))) return true;
      return keyList.some((k) => c.includes(k));
    };

    const genes = new Map();
    (actionable || []).forEach((a) => {
      const sym = (a.hugoSymbol || (a.gene && a.gene.hugoSymbol) || "").toUpperCase();
      if (!sym) return;
      const ct = a.cancerType || a.tumorType || "";
      if (!matches(ct)) return;
      const g = genes.get(sym) || { gene: sym, level: null, rank: 99, alterations: new Set(), tumorAgnostic: false };
      if (a.alteration) g.alterations.add(a.alteration);
      const r = levelRank(a.level);
      if (r < g.rank) { g.rank = r; g.level = shortLevel(a.level); }
      if (AGNOSTIC.some((x) => ct.toLowerCase().includes(x))) g.tumorAgnostic = true;
      genes.set(sym, g);
    });

    const out = [...genes.values()].map((g) => {
      const c = cur.get(g.gene);
      return {
        gene: g.gene,
        level: g.level,
        rank: g.rank,
        onImpact: !!(c && c.mSKImpact) || (impactSet ? impactSet.has(g.gene) : false),
        onAccess: accessSet ? accessSet.has(g.gene) : false,
        aliases: c && Array.isArray(c.geneAliases) ? c.geneAliases.slice(0, 6) : [],
        alterations: [...g.alterations].slice(0, 8),
        tumorAgnostic: g.tumorAgnostic,
      };
    }).sort((a, b) => (a.rank - b.rank) || a.gene.localeCompare(b.gene));

    res.setHeader("Cache-Control", "s-maxage=86400, stale-while-revalidate=604800");
    res.status(200).send(JSON.stringify({
      configured: true, cancer, count: out.length,
      impactAvailable: !!impactSet, accessAvailable: !!accessSet,
      source: "MSK OncoKB actionable variants + curated genes; MSK-IMPACT/MSK-ACCESS coverage from cBioPortal gene panels",
      genes: out,
    }));
  } catch (e) {
    res.status(502).send(JSON.stringify({ error: String((e && e.message) || e) }));
  }
};
