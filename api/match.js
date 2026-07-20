// Serverless proxy for Tier C precision matching: Claude reads a trial's full
// eligibility criteria against the patient profile and returns a structured verdict.
// Keeps the Anthropic API key server-side (set ANTHROPIC_API_KEY in Vercel env vars).
//
// POST /api/match  { profile: {...}, trial: { nctId, title, cancer, eligibilityCriteria } }
// -> { verdict, confidence, matched[], concerns[], summary }  (structured output)
// Returns { configured:false } when no key is set so the UI falls back to rule-based matching.

const MODEL = "claude-opus-4-8";

const SCHEMA = {
  type: "object",
  properties: {
    verdict: { type: "string", enum: ["eligible", "possible", "ineligible"] },
    confidence: { type: "string", enum: ["low", "medium", "high"] },
    matched: { type: "array", items: { type: "string" } },
    concerns: { type: "array", items: { type: "string" } },
    summary: { type: "string" },
  },
  required: ["verdict", "confidence", "matched", "concerns", "summary"],
  additionalProperties: false,
};

const SYSTEM = [
  "You assess whether a cancer patient plausibly meets a clinical trial's eligibility, as DECISION SUPPORT for a clinician or patient — never a medical determination.",
  "Judge ONLY against the trial's written eligibility criteria provided and the patient profile provided. Do not use outside knowledge of the specific trial, and do not invent criteria that aren't stated.",
  "verdict: 'ineligible' only if the profile clearly conflicts with a stated criterion (e.g. an excluded biomarker, wrong sex, out-of-range age, ECOG above the ceiling, wrong line of therapy). 'eligible' only if the stated inclusion criteria are met and nothing conflicts. Otherwise 'possible'.",
  "If the criteria are vague or the profile lacks the needed detail, prefer 'possible' with low/medium confidence — do not guess.",
  "matched: short bullet phrases for criteria the patient appears to satisfy. concerns: criteria that conflict or need confirmation. summary: one or two plain-language sentences. Always end reasoning implicitly with the understanding that the study team makes the final call.",
].join(" ");

function profileText(p) {
  const parts = [];
  if (p.biomarkers && p.biomarkers.length) parts.push("Biomarkers/alterations: " + p.biomarkers.join(", "));
  if (p.stage) parts.push("Stage: " + p.stage);
  if (p.lines !== null && p.lines !== undefined) parts.push("Prior lines of therapy: " + (p.lines >= 2 ? "2+" : p.lines));
  if (p.ecog !== null && p.ecog !== undefined) parts.push("ECOG performance status: " + p.ecog);
  if (p.age !== null && p.age !== undefined) parts.push("Age: " + p.age);
  if (p.sex) parts.push("Sex: " + p.sex.toLowerCase());
  return parts.length ? parts.join("\n") : "(no details provided)";
}

module.exports = async (req, res) => {
  res.setHeader("Content-Type", "application/json");
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) {
    res.status(200).send(JSON.stringify({ configured: false }));
    return;
  }
  if (req.method !== "POST") {
    res.status(405).send(JSON.stringify({ error: "POST only" }));
    return;
  }

  let body = req.body;
  try { if (typeof body === "string") body = JSON.parse(body); } catch (_) { body = null; }
  const profile = (body && body.profile) || {};
  const trial = (body && body.trial) || {};
  const criteria = (trial.eligibilityCriteria || "").toString().slice(0, 12000);
  if (!criteria.trim()) {
    res.status(200).send(JSON.stringify({
      verdict: "possible", confidence: "low", matched: [],
      concerns: ["This trial does not publish structured eligibility criteria."],
      summary: "No eligibility text was available to assess; contact the study team to confirm.",
    }));
    return;
  }

  const userMsg =
    "PATIENT PROFILE\n" + profileText(profile) +
    "\n\nTRIAL: " + (trial.title || trial.nctId || "") +
    " (condition: " + (trial.cancer || "cancer") + ")\n\nELIGIBILITY CRITERIA (verbatim from ClinicalTrials.gov):\n" + criteria;

  try {
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 1024,
        output_config: { format: { type: "json_schema", schema: SCHEMA }, effort: "low" },
        system: SYSTEM,
        messages: [{ role: "user", content: userMsg }],
      }),
    });
    const data = await r.json();
    if (!r.ok) {
      res.status(r.status).send(JSON.stringify({ error: (data && data.error && data.error.message) || ("Anthropic error " + r.status) }));
      return;
    }
    if (data.stop_reason === "refusal") {
      res.status(200).send(JSON.stringify({ verdict: "possible", confidence: "low", matched: [], concerns: ["Automated assessment unavailable for this trial."], summary: "Please review with the study team." }));
      return;
    }
    const textBlock = (data.content || []).find(function (b) { return b.type === "text"; });
    const parsed = textBlock ? JSON.parse(textBlock.text) : null;
    if (!parsed || !parsed.verdict) throw new Error("no structured verdict");
    res.setHeader("Cache-Control", "no-store");
    res.status(200).send(JSON.stringify(parsed));
  } catch (e) {
    res.status(502).send(JSON.stringify({ error: String((e && e.message) || e) }));
  }
};
