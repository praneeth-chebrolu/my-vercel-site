// Serverless endpoint: tumor-specific biomarkers / tumor markers for precision matching.
//
// Deterministic and self-contained — reads a bundled, curated per-tumor dataset
// (biomarker-data.json), so it returns cancer-specific markers instantly with NO
// external API calls, keys, or egress. The dataset is seeded from FDA-recognized and
// NCCN/CAP-guideline biomarkers per tumor type; refresh it from CIViC/OncoKB as needed.
//
// GET /api/biomarkers?cancer=Lung%20cancer
//   -> { configured:true, cancer, count, source, genes:[{gene, level, rank, onImpact,
//        onAccess, aliases[], alterations[], therapies[], tumorAgnostic}], ... }

const DATA = require("./biomarker-data.json");
const SOURCE = (DATA._meta && DATA._meta.source) || "Curated tumor-specific biomarkers";

// Tumor-agnostic, FDA-approved markers — appended to every mapped tumor.
const AGNOSTIC = [
  { gene: "NTRK1/2/3", aliases: ["NTRK", "TRK", "NTRK1", "NTRK2", "NTRK3"], tier: "A", alterations: ["Gene fusion"], onImpact: true, onAccess: true },
  { gene: "MSI-H/dMMR", aliases: ["MSI", "MSI-H", "microsatellite instability", "dMMR", "mismatch repair"], tier: "A", alterations: ["MSI-high / mismatch-repair deficient"], onImpact: true, onAccess: false },
  { gene: "TMB-High", aliases: ["TMB", "tumor mutational burden"], tier: "A", alterations: ["≥ 10 mutations/Mb"], onImpact: true, onAccess: false },
];

const tierRank = (t) => (t === "A" ? 1 : t === "B" ? 2 : 3);

function toOut(b, agnostic) {
  return {
    gene: b.gene,
    level: b.tier || null,
    rank: tierRank(b.tier),
    onImpact: !!b.onImpact,
    onAccess: !!b.onAccess,
    aliases: Array.isArray(b.aliases) ? b.aliases.slice(0, 6) : [],
    alterations: Array.isArray(b.alterations) ? b.alterations.slice(0, 8) : [],
    therapies: [],
    tumorAgnostic: !!agnostic,
  };
}

module.exports = async (req, res) => {
  res.setHeader("Content-Type", "application/json");
  const cancer = ((req.query && req.query.cancer) || "").toString();
  const list = DATA[cancer];

  if (!Array.isArray(list)) {
    res.status(200).send(JSON.stringify({ configured: true, cancer, count: 0, genes: [], note: "no tumor-specific list for this type" }));
    return;
  }

  const seen = new Set();
  const genes = [];
  list.forEach((b) => { if (!seen.has(b.gene)) { seen.add(b.gene); genes.push(toOut(b, false)); } });
  AGNOSTIC.forEach((b) => { if (!seen.has(b.gene)) { seen.add(b.gene); genes.push(toOut(b, true)); } });
  genes.sort((a, b) => (a.rank - b.rank) || 0); // stable: keeps tumor-specific before agnostic within a tier

  res.setHeader("Cache-Control", "s-maxage=86400, stale-while-revalidate=604800");
  res.status(200).send(JSON.stringify({
    configured: true, cancer, count: genes.length,
    impactAvailable: true, accessAvailable: true,
    source: SOURCE, genes,
  }));
};
