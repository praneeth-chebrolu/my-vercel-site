// Serverless proxy for the NCI Clinical Trials Search (CTS) API.
// Keeps the API key server-side (set NCI_API_KEY in your Vercel project env vars).
// Get a key: https://clinicaltrialsapi.cancer.gov  →  "Get API Key".
//
// GET /api/nci-trials?biomarkers=EGFR,BRAF&diseases=Lung%20cancer&size=50
// Returns the NCI response verbatim, or { configured:false } when no key is set
// so the front-end can fall back to rule-based matching without breaking.

module.exports = async (req, res) => {
  const key = process.env.NCI_API_KEY;
  res.setHeader("Content-Type", "application/json");

  if (!key) {
    res.status(200).send(JSON.stringify({ configured: false, trials: [], message: "NCI_API_KEY not set" }));
    return;
  }

  const q = req.query || {};
  const biomarkers = (q.biomarkers || "").toString().trim();
  const diseases = (q.diseases || "").toString().trim();
  const size = Math.min(parseInt(q.size, 10) || 50, 50);

  const params = new URLSearchParams();
  if (biomarkers) biomarkers.split(",").map(s => s.trim()).filter(Boolean).forEach(b => params.append("biomarkers", b));
  if (diseases) params.set("diseases", diseases);
  params.set("size", String(size));

  const url = `https://clinicaltrialsapi.cancer.gov/api/v2/trials?${params.toString()}`;

  try {
    const r = await fetch(url, { headers: { "X-API-KEY": key, "Accept": "application/json" } });
    const text = await r.text();
    // cache at the edge for 10 min; NCI data changes slowly
    if (r.ok) res.setHeader("Cache-Control", "s-maxage=600, stale-while-revalidate=1800");
    res.status(r.ok ? 200 : r.status).send(text);
  } catch (e) {
    res.status(502).send(JSON.stringify({ error: String((e && e.message) || e) }));
  }
};
