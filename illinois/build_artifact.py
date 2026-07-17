#!/usr/bin/env python3
"""Assemble the self-contained 'Illinois Cancer Research Deserts' page.

Inlines Leaflet + all real data into one HTML file (zero external requests). Emits:
  - research-deserts.html            (full standalone doc, deployable on the site)
  - scratchpad/artifact_body.html    (head/body-less content for the Artifact host)
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
def read(p): return open(os.path.join(HERE, p), encoding="utf-8").read()

leaflet_css = read("vendor/leaflet.css")
leaflet_js  = read("vendor/leaflet.js")
counties    = json.load(open(os.path.join(HERE, "data/counties.json")))
centers     = json.load(open(os.path.join(HERE, "data/centers.json")))
geo         = json.load(open(os.path.join(HERE, "data/il-counties.geojson")))

DATA_JS = "const META=%s;\nconst DATA=META.counties;\nconst CENTERS=%s;\nconst GEO=%s;" % (
    json.dumps(counties, separators=(",", ":")),
    json.dumps(centers["centers"], separators=(",", ":")),
    json.dumps(geo, separators=(",", ":")),
)

STYLE = r"""
<style>
__LEAFLET_CSS__
:root{
  --ground:#FBF8F3; --panel:#FFFFFF; --ink:#1C1814; --muted:#6E6459;
  --line:#EAE2D6; --line-strong:#D8CCBB;
  --accent:#0E6B6B; --accent-ink:#0A5252;
  --sev-severe:#8C2D12; --sev-high:#D0561F; --sev-mod:#E7A15A; --sev-low:#7FA9A0;
  --shadow:0 1px 2px rgba(28,20,12,.04),0 8px 24px rgba(28,20,12,.06);
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
}
@media (prefers-color-scheme:dark){
  :root{
    --ground:#15120E; --panel:#1F1B15; --ink:#F1EADE; --muted:#A89C8C;
    --line:#2E281F; --line-strong:#3C3428;
    --accent:#3FBFB4; --accent-ink:#6FD6CC; --sev-low:#5F8A81;
    --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
  }
}
:root[data-theme="light"]{
  --ground:#FBF8F3; --panel:#FFFFFF; --ink:#1C1814; --muted:#6E6459; --line:#EAE2D6; --line-strong:#D8CCBB;
  --accent:#0E6B6B; --accent-ink:#0A5252; --sev-low:#7FA9A0;
  --shadow:0 1px 2px rgba(28,20,12,.04),0 8px 24px rgba(28,20,12,.06);
}
:root[data-theme="dark"]{
  --ground:#15120E; --panel:#1F1B15; --ink:#F1EADE; --muted:#A89C8C; --line:#2E281F; --line-strong:#3C3428;
  --accent:#3FBFB4; --accent-ink:#6FD6CC; --sev-low:#5F8A81;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
.wrap{font-family:var(--sans);color:var(--ink);background:var(--ground);
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;padding:0 clamp(16px,4vw,48px) 64px;}
.inner{max-width:1160px;margin:0 auto;}
a{color:var(--accent-ink)}
.hero{padding:56px 0 28px;border-bottom:1px solid var(--line);}
.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:700;margin:0 0 14px;}
.hero h1{font-family:var(--serif);font-weight:600;font-size:clamp(40px,7vw,76px);line-height:.98;
  letter-spacing:-.01em;margin:0;text-wrap:balance;}
.hero h1 em{font-style:italic;color:var(--sev-high);}
.hero .thesis{font-size:clamp(17px,2.1vw,20px);line-height:1.5;color:var(--muted);max-width:60ch;margin:18px 0 0;}
.hero .thesis b{color:var(--ink);font-weight:600;}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:34px 0 0;}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;box-shadow:var(--shadow);}
.stat .n{font-family:var(--serif);font-size:34px;line-height:1;font-variant-numeric:tabular-nums;letter-spacing:-.01em;}
.stat.sev .n{color:var(--sev-severe);} .stat.warn .n{color:var(--sev-high);}
.stat .k{font-size:12.5px;color:var(--muted);margin-top:8px;line-height:1.35;}
.grid{display:grid;grid-template-columns:1.55fr 1fr;gap:22px;margin-top:30px;align-items:start;}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);overflow:hidden;}
.card-h{display:flex;align-items:baseline;justify-content:space-between;gap:12px;padding:16px 18px 0;}
.card-h h2{font-size:15px;margin:0;letter-spacing:.01em;}
.card-h .hint{font-size:12px;color:var(--muted);}
.controls{display:flex;flex-wrap:wrap;gap:7px;padding:14px 18px;}
.chip{font-family:var(--sans);font-size:12.5px;border:1px solid var(--line-strong);background:transparent;color:var(--ink);
  border-radius:999px;padding:6px 12px;cursor:pointer;transition:all .12s;}
.chip:hover{border-color:var(--accent);color:var(--accent-ink);}
.chip.active{background:var(--accent);border-color:var(--accent);color:#fff;}
#map{height:520px;width:100%;background:var(--ground);}
.leaflet-container{background:var(--ground);font-family:var(--sans);}
.legend{display:flex;flex-wrap:wrap;gap:14px;padding:12px 18px 18px;font-size:11.5px;color:var(--muted);}
.legend .row{display:flex;align-items:center;gap:6px;}
.legend .sw{width:26px;height:10px;border-radius:2px;}
.list{padding:6px 8px 10px;max-height:600px;overflow:auto;}
.di{display:grid;grid-template-columns:26px 1fr auto;gap:12px;align-items:center;padding:11px 12px;border-radius:12px;cursor:pointer;}
.di+.di{border-top:1px solid var(--line);}
.di:hover{background:var(--ground);}
.di.sel{background:color-mix(in srgb,var(--accent) 10%,transparent);}
.di .rk{font-family:var(--serif);font-size:17px;color:var(--muted);font-variant-numeric:tabular-nums;text-align:center;}
.di .co{font-weight:600;font-size:14.5px;}
.di .sub{font-size:12px;color:var(--muted);margin-top:2px;}
.di .sc{font-variant-numeric:tabular-nums;font-weight:700;font-size:15px;text-align:right;}
.pill{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;
  padding:2px 7px;border-radius:6px;color:#fff;}
.pill.severe{background:var(--sev-severe);} .pill.high{background:var(--sev-high);}
.pill.mod{background:var(--sev-mod);color:#4a2a08;} .pill.low{background:var(--sev-low);}
.detail{padding:16px 18px;border-top:1px solid var(--line);display:none;}
.detail.on{display:block;}
.detail .dn{font-family:var(--serif);font-size:22px;margin:0;}
.detail .dsub{font-size:12px;color:var(--muted);margin:3px 0 12px;}
.drow{display:flex;justify-content:space-between;gap:16px;font-size:13px;padding:6px 0;border-bottom:1px dashed var(--line);}
.drow:last-child{border-bottom:none;} .drow b{font-variant-numeric:tabular-nums;}
.method{margin-top:34px;padding-top:26px;border-top:1px solid var(--line);}
.method h2{font-family:var(--serif);font-size:22px;margin:0 0 6px;}
.mgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:22px;margin-top:14px;}
.method h3{font-size:13px;margin:0 0 4px;color:var(--accent-ink);}
.method p{font-size:13px;line-height:1.6;color:var(--muted);margin:0;}
.prov{margin-top:22px;font-size:11.5px;color:var(--muted);line-height:1.6;}
.tag{display:inline-block;font-size:10.5px;border:1px solid var(--line-strong);border-radius:6px;padding:1px 6px;margin-right:5px;color:var(--muted);}
@media (max-width:900px){
  .grid{grid-template-columns:1fr;} .stats{grid-template-columns:repeat(2,1fr);} .mgrid{grid-template-columns:1fr;}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important;}}
</style>
"""

BODY = r"""
<div class="wrap"><div class="inner">
  <header class="hero">
    <p class="eyebrow">Illinois &middot; Cancer clinical-trial access</p>
    <h1>Research <em>Deserts</em></h1>
    <p class="thesis">Where Illinois has both the <b>highest cancer burden</b> and the
      <b>least access to clinical trials</b>. In <b id="tDeserts">&mdash;</b> counties, cancer strikes
      at or above the state rate yet the nearest trial center is a long drive with
      <b>no active trials within 90&nbsp;minutes</b>.</p>
    <div class="stats">
      <div class="stat sev"><div class="n" id="sSevere">&mdash;</div><div class="k">severe research deserts (highest unmet need)</div></div>
      <div class="stat warn"><div class="n" id="sPeople">&mdash;</div><div class="k">people in high-burden, zero-trial counties</div></div>
      <div class="stat"><div class="n" id="sCases">&mdash;</div><div class="k">cancer cases / year in those counties</div></div>
      <div class="stat"><div class="n" id="sFar">&mdash;</div><div class="k">counties &gt; 60&nbsp;min from any IL trial center</div></div>
    </div>
  </header>
  <div class="grid">
    <section class="card">
      <div class="card-h"><h2 id="mapTitle">Research-desert severity</h2><span class="hint">hover a county</span></div>
      <div class="controls" id="controls">
        <button class="chip active" data-m="desert_score">Desert severity</button>
        <button class="chip" data-m="incidence_per100k">Incidence rate</button>
        <button class="chip" data-m="annual_cases">Cancer cases</button>
        <button class="chip" data-m="drive_min">Drive to center</button>
        <button class="chip" data-m="trials_90">Trials &le;90 min</button>
      </div>
      <div id="map"></div>
      <div class="legend" id="legend"></div>
      <div class="detail" id="detail"></div>
    </section>
    <section class="card">
      <div class="card-h"><h2>The deserts, ranked</h2><span class="hint">most unmet need first</span></div>
      <div class="list" id="list"></div>
    </section>
  </div>
  <section class="method">
    <h2>How a &ldquo;desert&rdquo; is measured</h2>
    <div class="mgrid">
      <div><h3>Burden</h3><p>Real per-county cancer incidence &mdash; age-adjusted rate and average annual case count &mdash; from NCI &amp; CDC State Cancer Profiles (All Cancer Sites, 2018&ndash;2022).</p></div>
      <div><h3>Access</h3><p>For each county we find the nearest of 12 real Illinois trial centers, estimate the drive, and count active trials reachable within 30 / 60 / 90 minutes.</p></div>
      <div><h3>Severity score</h3><p>Severity = &radic;(burden &times; access gap), where the access gap blends drive time (55%) and scarcity of nearby trials (45%). Higher = greater unmet need.</p></div>
    </div>
    <p class="prov">
      <span class="tag">Real</span> Population, density, geometry (U.S. Census).
      <span class="tag">Real</span> Cancer incidence (NCI &amp; CDC State Cancer Profiles &mdash; U.S. Cancer Statistics / NPCR + SEER, 2018&ndash;2022).
      <span class="tag">Real</span> Cancer-center locations.
      <span class="tag">Estimate</span> Per-center trial counts &amp; drive times are modeled for planning &mdash; not clinical or navigational advice.
    </p>
  </section>
</div></div>

<script>
__DATA_JS__
const RAMPS={
  warm:['#F6EAD6','#F4CD9A','#EDA05E','#DF6E36','#B8431F','#7C2A12'],
  teal:['#E7F1EF','#BFDDD8','#8FC4BB','#4E9E92','#2C7A6E','#14524A'],
};
const METRICS={
  desert_score:     {t:'Research-desert severity', ramp:'warm', fmt:v=>v.toFixed(0)},
  incidence_per100k:{t:'Age-adjusted incidence (per 100k)', ramp:'warm', fmt:v=>Math.round(v).toLocaleString()},
  annual_cases:     {t:'Annual cancer cases', ramp:'warm', fmt:v=>v.toLocaleString()},
  drive_min:        {t:'Drive to nearest center (min)', ramp:'warm', fmt:v=>v+' min'},
  trials_90:        {t:'Active trials within 90 min', ramp:'teal', fmt:v=>v.toLocaleString()},
};
const STATE_RATE=META.il_rate_per100k||464.2;
const byFips={}; DATA.forEach(c=>byFips[c.fips]=c);
let current='desert_score', STOPS={};
function stops(m){const v=DATA.map(c=>c[m]);return{min:Math.min(...v),max:Math.max(...v)};}
Object.keys(METRICS).forEach(k=>STOPS[k]=stops(k));
function color(m,val){const r=RAMPS[METRICS[m].ramp],s=STOPS[m];
  let t=(val-s.min)/((s.max-s.min)||1);return r[Math.min(r.length-1,Math.max(0,Math.floor(t*r.length)))];}
function tier(s){return s>=55?['severe','Severe']:s>=38?['high','High']:s>=22?['mod','Moderate']:['low','Served'];}
const deserts=DATA.filter(c=>c.incidence_per100k>=STATE_RATE && c.trials_90===0);
document.getElementById('tDeserts').textContent=deserts.length;
document.getElementById('sSevere').textContent=DATA.filter(c=>c.desert_score>=55).length;
const ppl=deserts.reduce((a,c)=>a+c.population,0), cas=deserts.reduce((a,c)=>a+c.annual_cases,0);
document.getElementById('sPeople').textContent=(ppl/1e6).toFixed(1)+'M';
document.getElementById('sCases').textContent=cas.toLocaleString();
document.getElementById('sFar').textContent=DATA.filter(c=>c.drive_min>60).length;
const map=L.map('map',{scrollWheelZoom:false,zoomControl:true,attributionControl:false}).setView([40,-89.3],6);
let gLayer;
function style(f){const c=byFips[f.properties.GEO_ID.slice(-5)];
  return{fillColor:c?color(current,c[current]):'#eee',weight:1,color:'#FBF8F3',fillOpacity:.85};}
gLayer=L.geoJSON(GEO,{style,onEachFeature:(f,l)=>{
  const c=byFips[f.properties.GEO_ID.slice(-5)]; if(c)c._l=l;
  l.on({mouseover:()=>{l.setStyle({weight:2.5,color:'#1C1814'});l.bringToFront();if(c)detail(c);},
        mouseout:()=>gLayer.resetStyle(l), click:()=>{if(c){detail(c);map.fitBounds(l.getBounds(),{maxZoom:9,padding:[30,30]});}}});
}}).addTo(map);
map.fitBounds(gLayer.getBounds(),{padding:[10,10]});
L.layerGroup(CENTERS.map(c=>{const nci=c.nci!=='None';
  return L.circleMarker([c.lat,c.lng],{radius:nci?7:5,color:'#1C1814',weight:1.4,
    fillColor:nci?'#8C2D12':'#1C1814',fillOpacity:.92})
    .bindTooltip(`${c.name} — ${c.city}${nci?' (NCI '+c.nci+')':''}`);
})).addTo(map);
function legend(){const m=METRICS[current],r=RAMPS[m.ramp],s=STOPS[current];let h='';
  for(let i=0;i<r.length;i++){const lo=s.min+(s.max-s.min)*i/r.length;
    h+=`<div class="row"><span class="sw" style="background:${r[i]}"></span>${m.fmt(Math.round(lo))}</div>`;}
  h+=`<div class="row"><span class="sw" style="background:#1C1814;border-radius:50%;width:10px"></span>Trial center</div>`;
  document.getElementById('legend').innerHTML=h;
  document.getElementById('mapTitle').textContent=m.t;
}
function detail(c){const t=tier(c.desert_score);
  const d=document.getElementById('detail'); d.classList.add('on');
  d.innerHTML=`
    <p class="dn">${c.county} County <span class="pill ${t[0]}">${t[1]}</span></p>
    <p class="dsub">FIPS ${c.fips} &middot; ${c.rural_urban||''} &middot; desert rank #${c.desert_rank} of ${DATA.length} &middot; severity ${c.desert_score}</p>
    <div class="drow"><span>Incidence (per 100k)</span><b>${c.incidence_per100k.toLocaleString()} <span style="color:var(--muted);font-weight:400">(${c.trend||'n/a'}, state ${STATE_RATE})</span></b></div>
    <div class="drow"><span>Cancer cases / year</span><b>${c.annual_cases.toLocaleString()}</b></div>
    <div class="drow"><span>Population</span><b>${c.population.toLocaleString()}</b></div>
    <div class="drow"><span>Nearest trial center</span><b>${c.nearest_city} &middot; ${c.drive_min} min</b></div>
    <div class="drow"><span>Trials within 60 / 90 min</span><b>${c.trials_60} / ${c.trials_90}</b></div>
    <div class="drow"><span style="color:var(--muted)">${c.nearest_center}</span><b></b></div>`;
  document.querySelectorAll('.di').forEach(x=>x.classList.toggle('sel',x.dataset.f===c.fips));
}
function renderList(){
  const rows=[...DATA].sort((a,b)=>b.desert_score-a.desert_score);
  document.getElementById('list').innerHTML=rows.map(c=>{const t=tier(c.desert_score);
    return `<div class="di" data-f="${c.fips}">
      <div class="rk">${c.desert_rank}</div>
      <div><div class="co">${c.county}</div>
        <div class="sub">${c.incidence_per100k} /100k &middot; ${c.drive_min} min &middot; ${c.trials_90} trials &le;90m</div></div>
      <div style="text-align:right"><span class="pill ${t[0]}">${t[1]}</span><div class="sc">${c.desert_score.toFixed(0)}</div></div>
    </div>`;}).join('');
  document.querySelectorAll('.di').forEach(d=>d.onclick=()=>{const c=byFips[d.dataset.f];
    detail(c); if(c._l)map.fitBounds(c._l.getBounds(),{maxZoom:9,padding:[30,30]});});
}
function setMetric(m){current=m;document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x.dataset.m===m));
  gLayer.setStyle(style);legend();}
document.querySelectorAll('.chip').forEach(x=>x.onclick=()=>setMetric(x.dataset.m));
legend();renderList();
detail([...DATA].sort((a,b)=>b.desert_score-a.desert_score)[0]);
</script>
"""

inner = STYLE.replace("__LEAFLET_CSS__", leaflet_css)
lf_tag = "<script>\n" + leaflet_js + "\n</script>\n"
inner += lf_tag + BODY.replace("__DATA_JS__", DATA_JS)

art_path = "/tmp/claude-0/-home-user-my-vercel-site/a69d2f8f-2f2c-5491-97fb-ccbc6d76770e/scratchpad/artifact_body.html"
open(art_path, "w", encoding="utf-8").write(inner)

doc = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
       '<title>Illinois Cancer Research Deserts</title>\n</head>\n<body>\n'
       + inner + '\n</body>\n</html>\n')
open(os.path.join(HERE, "research-deserts.html"), "w", encoding="utf-8").write(doc)

print("artifact body bytes:", os.path.getsize(art_path))
print("standalone doc bytes:", os.path.getsize(os.path.join(HERE, "research-deserts.html")))
print("high-burden zero-trial counties:", len(deserts) if 'deserts' in dir() else 'n/a')
