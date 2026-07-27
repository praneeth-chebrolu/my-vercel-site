// Serverless proxy: cancer-specific biomarkers / tumor markers for precision matching.
//
// OPEN BY DEFAULT. Primary source = CIViC (civicdb.org) — the Clinical Interpretation
// of Variants in Cancer knowledgebase, released into the PUBLIC DOMAIN (CC0), so it's
// free for any use including commercial. Assay coverage (MSK-IMPACT / MSK-ACCESS) is
// layered on from cBioPortal's public gene-panel API (also free, no key).
//
// Optional upgrade: if an ONCOKB_TOKEN is set in the environment, the proxy uses MSK
// OncoKB instead (richer curation, but OncoKB requires a paid license for commercial/
// clinical use). No token → CIViC. Either way the response shape is identical.
//
// GET /api/biomarkers?cancer=Lung%20cancer
//   -> { configured:true, cancer, count, source, genes:[{gene, level, rank, onImpact,
//        onAccess, aliases[], alterations[], therapies[], tumorAgnostic}], ... }

const ONCOKB = "https://www.oncokb.org/api/v1";
const CBIO = "https://www.cbioportal.org/api";
const CIVIC_TSV = "https://civicdb.org/downloads/nightly/nightly-ClinicalEvidenceSummaries.tsv";
const IMPACT_PANEL = "IMPACT505";
const ACCESS_PANEL_CANDIDATES = ["MSK-ACCESS", "MSK-ACCESS-v1", "ACCESS129", "MSK_ACCESS"];

// Map our UI cancer labels to substrings that appear in disease names (CIViC + OncoKB).
const CANCER_KEYWORDS = {
  "Bladder cancer": ["bladder", "urothelial"],
  "Brain cancer": ["glioma", "glioblastoma", "astrocytoma", "oligodendroglioma", "brain"],
  "Breast cancer": ["breast"],
  "Colon & rectal cancer": ["colorectal", "colon", "rectal"],
  "Gastrointestinal cancer": ["colorectal", "gastric", "stomach", "esophag", "pancrea", "hepatocellular", "liver", "biliary", "cholangio", "gastrointestinal stromal", "small bowel"],
  "Gynecologic cancer": ["ovarian", "cervical", "endometrial", "uterine", "vaginal", "vulvar", "fallopian"],
  "Head & neck cancer": ["head and neck", "nasophar", "orophar", "laryn"],
  "Kidney cancer": ["renal", "kidney"],
  "Lung cancer": ["lung", "nsclc", "sclc"],
  "Prostate cancer": ["prostate"],
  "Skin cancer": ["melanoma", "skin", "merkel", "basal cell", "squamous cell carcinoma of the skin"],
  "Testicular cancer": ["germ cell", "testicular"],
};
// Tumor-agnostic disease buckets — always relevant (NTRK fusions, MSI-H, TMB-H, etc.).
const AGNOSTIC_ONCOKB = ["all solid tumors", "all tumors", "all liquid tumors"];
const AGNOSTIC_CIVIC = ["cancer", "solid tumor", "advanced solid tumor", "solid tumors", "neoplasm", "any cancer", "carcinoma"];

// Small alias aid so gene symbols still match how trials phrase them (CIViC uses HUGO symbols).
const ALIASES = {
  ERBB2: ["HER2", "neu"], EGFR: ["ERBB1"], CD274: ["PD-L1", "PDL1"], PDCD1: ["PD-1", "PD1"],
  MET: ["c-MET"], KIT: ["c-KIT", "CD117"], ALK: [], MLH1: ["MMR", "MSI"], MSH2: ["MMR", "MSI"],
  MSH6: ["MMR", "MSI"], PMS2: ["MMR", "MSI"], MKI67: ["Ki-67"],
};

function levelRankLetter(lv) { const o = { A: 1, B: 2, C: 3, D: 4, E: 5 }; return o[(lv || "").toUpperCase()] || 9; }
function levelRankOncokb(lv) { const o = { LEVEL_1: 1, LEVEL_2: 2, LEVEL_3A: 3, LEVEL_3B: 4, LEVEL_4: 5, LEVEL_R1: 6, LEVEL_R2: 7 }; return o[lv] || 9; }

async function fetchPanels() {
  const cbioPanel = async (id) => {
    try {
      const r = await fetch(`${CBIO}/gene-panels/${encodeURIComponent(id)}`, { headers: { Accept: "application/json" } });
      if (!r.ok) return null;
      const d = await r.json();
      const g = (d.genes || []).map((x) => (x.hugoGeneSymbol || "").toUpperCase()).filter(Boolean);
      return g.length ? new Set(g) : null;
    } catch (_) { return null; }
  };
  const impactSet = await cbioPanel(IMPACT_PANEL);
  let accessSet = null;
  for (const id of ACCESS_PANEL_CANDIDATES) { const s = await cbioPanel(id); if (s) { accessSet = s; break; } }
  return { impactSet, accessSet };
}

function decorate(genesArr, cur, panels) {
  return genesArr.map((g) => {
    const curated = cur ? cur.get(g.gene) : null;
    const aliases = (curated && Array.isArray(curated.geneAliases) && curated.geneAliases.length)
      ? curated.geneAliases.slice(0, 6) : (ALIASES[g.gene] || []);
    return {
      gene: g.gene, level: g.level, rank: g.rank,
      onImpact: !!(curated && curated.mSKImpact) || (panels.impactSet ? panels.impactSet.has(g.gene) : false),
      onAccess: panels.accessSet ? panels.accessSet.has(g.gene) : false,
      aliases,
      alterations: [...(g.alterations || [])].slice(0, 8),
      therapies: [...(g.therapies || [])].slice(0, 6),
      tumorAgnostic: !!g.tumorAgnostic,
    };
  }).sort((a, b) => (a.rank - b.rank) || a.gene.localeCompare(b.gene));
}

// ---------------- CIViC (open, default) ----------------
function normHeader(s) { return (s || "").trim().toLowerCase().replace(/\s+/g, "_"); }
async function getFromCivic(cancer, keyList, panels) {
  const r = await fetch(CIVIC_TSV, { headers: { Accept: "text/tab-separated-values" } });
  if (!r.ok) throw new Error("CIViC " + r.status);
  const text = await r.text();
  const lines = text.split(/\r?\n/);
  if (!lines.length) return [];
  const header = lines[0].split("\t").map(normHeader);
  const col = (...names) => { for (const n of names) { const i = header.indexOf(n); if (i !== -1) return i; } return -1; };
  const iGene = col("gene"), iVariant = col("variant"), iDisease = col("disease"),
    iLevel = col("evidence_level"), iSig = col("significance", "clinical_significance"),
    iTher = col("therapies", "drugs"), iStatus = col("evidence_status");
  if (iGene < 0 || iLevel < 0 || iDisease < 0) throw new Error("CIViC columns not found");

  const matches = (disease) => {
    const c = (disease || "").toLowerCase().trim();
    if (AGNOSTIC_CIVIC.includes(c)) return { hit: true, agnostic: true };
    if (keyList.some((k) => c.includes(k))) return { hit: true, agnostic: false };
    return { hit: false, agnostic: false };
  };

  const genes = new Map();
  for (let n = 1; n < lines.length; n++) {
    const f = lines[n].split("\t");
    if (f.length <= iLevel) continue;
    const lvl = (f[iLevel] || "").trim().toUpperCase();
    if (!/^[A-E]$/.test(lvl)) continue;               // validates a real data row (guards free-text wraps)
    if (iStatus >= 0 && (f[iStatus] || "").trim().toLowerCase() === "rejected") continue;
    const sym = (f[iGene] || "").trim().toUpperCase();
    if (!sym || /\s/.test(sym)) continue;
    const m = matches(f[iDisease]);
    if (!m.hit) continue;
    const g = genes.get(sym) || { gene: sym, level: null, rank: 99, alterations: new Set(), therapies: new Set(), tumorAgnostic: false };
    const rk = levelRankLetter(lvl);
    if (rk < g.rank) { g.rank = rk; g.level = lvl; }
    const v = iVariant >= 0 ? (f[iVariant] || "").trim() : "";
    if (v) g.alterations.add(v);
    if (iTher >= 0) (f[iTher] || "").split(",").map((s) => s.trim()).filter(Boolean).forEach((t) => g.therapies.add(t));
    if (m.agnostic) g.tumorAgnostic = true;
    genes.set(sym, g);
  }
  return decorate([...genes.values()], null, panels);
}

// ---------------- OncoKB (optional, licensed) ----------------
async function getFromOncokb(cancer, keyList, token, panels) {
  const oncokbGet = async (path) => {
    const r = await fetch(ONCOKB + path, { headers: { Authorization: "Bearer " + token, Accept: "application/json" } });
    if (!r.ok) throw new Error("OncoKB " + r.status);
    return r.json();
  };
  const [actionable, curated] = await Promise.all([
    oncokbGet("/utils/allActionableVariants"),
    oncokbGet("/utils/allCuratedGenes?includeEvidence=false").catch(() => []),
  ]);
  const cur = new Map();
  (curated || []).forEach((g) => { const s = (g.hugoSymbol || "").toUpperCase(); if (s) cur.set(s, g); });
  const matches = (ct) => {
    const c = (ct || "").toLowerCase();
    if (AGNOSTIC_ONCOKB.some((a) => c.includes(a))) return { hit: true, agnostic: true };
    return { hit: keyList.some((k) => c.includes(k)), agnostic: false };
  };
  const genes = new Map();
  (actionable || []).forEach((a) => {
    const sym = (a.hugoSymbol || (a.gene && a.gene.hugoSymbol) || "").toUpperCase();
    if (!sym) return;
    const ct = a.cancerType || a.tumorType || "";
    const m = matches(ct);
    if (!m.hit) return;
    const g = genes.get(sym) || { gene: sym, level: null, rank: 99, alterations: new Set(), therapies: new Set(), tumorAgnostic: false };
    if (a.alteration) g.alterations.add(a.alteration);
    (a.drugs || []).forEach((d) => { const dn = typeof d === "string" ? d : (d && d.drugName); if (dn) g.therapies.add(dn); });
    const r = levelRankOncokb(a.level);
    if (r < g.rank) { g.rank = r; g.level = (a.level || "").replace("LEVEL_", "") || null; }
    if (m.agnostic) g.tumorAgnostic = true;
    genes.set(sym, g);
  });
  return decorate([...genes.values()], cur, panels);
}

module.exports = async (req, res) => {
  res.setHeader("Content-Type", "application/json");
  const cancer = ((req.query && req.query.cancer) || "").toString();
  const keys = CANCER_KEYWORDS[cancer];
  if (!keys) {
    res.status(200).send(JSON.stringify({ configured: true, cancer, count: 0, genes: [], note: "no cancer-specific mapping" }));
    return;
  }
  const keyList = keys.map((s) => s.toLowerCase());
  const token = process.env.ONCOKB_TOKEN;

  try {
    const panels = await fetchPanels();
    let genes, source;
    if (token) {
      genes = await getFromOncokb(cancer, keyList, token, panels);
      source = "MSK OncoKB (licensed) + MSK-IMPACT/ACCESS coverage (cBioPortal)";
    } else {
      genes = await getFromCivic(cancer, keyList, panels);
      source = "CIViC (civicdb.org, CC0 public domain) + MSK-IMPACT/ACCESS coverage (cBioPortal)";
    }
    res.setHeader("Cache-Control", "s-maxage=86400, stale-while-revalidate=604800");
    res.status(200).send(JSON.stringify({
      configured: true, cancer, count: genes.length,
      impactAvailable: !!panels.impactSet, accessAvailable: !!panels.accessSet,
      source, genes,
    }));
  } catch (e) {
    res.status(502).send(JSON.stringify({ error: String((e && e.message) || e), genes: [] }));
  }
};
