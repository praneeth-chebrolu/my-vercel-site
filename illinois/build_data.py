"""
Build the Illinois Access-to-Innovation Index dataset (data/counties.json).

Inputs (download once, place alongside this script):
  il_counties.geojson  -> filter U.S. county GeoJSON to STATE == "17":
     https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json
  us_pop.json          -> county population/area/density:
     https://raw.githubusercontent.com/balsama/us_counties_data/master/data/counties.json

Real vs. estimated:
  REAL      county population, land area, density, boundary geometry, center locations
  ESTIMATE  cancer incidence (statewide age-adjusted rate x population)
  ESTIMATE  drive time / distance (straight-line x road factor)
  PLACEHOLDER  per-center active-trial and Phase I counts (wire to ClinicalTrials.gov)

To use true county incidence, replace the IL_RATE block with a lookup keyed by FIPS
loaded from an Illinois State Cancer Registry (ISCR) export, then re-run:
  python3 build_data.py   ->  writes counties_out.json / centers_out.json
"""
import json, math

geo = json.load(open('il_counties.geojson'))
pop = json.load(open('us_pop.json'))
pop_il = {v['fips']: v for k,v in pop.items() if k.endswith(', Illinois')}

# ---- Real Illinois cancer centers running oncology clinical trials ----
# lat/lng are real facility locations; nci = NCI-designated status.
# trials_active / phase1 are ILLUSTRATIVE placeholders (populate from ClinicalTrials.gov).
CENTERS = [
 {"name":"Robert H. Lurie Comprehensive Cancer Center (Northwestern)","city":"Chicago","lat":41.8969,"lng":-87.6212,"nci":"Comprehensive","trials_active":420,"phase1":95},
 {"name":"University of Chicago Medicine Comprehensive Cancer Center","city":"Chicago","lat":41.7886,"lng":-87.6044,"nci":"Comprehensive","trials_active":380,"phase1":88},
 {"name":"University of Illinois Cancer Center","city":"Chicago","lat":41.8670,"lng":-87.6706,"nci":"None","trials_active":140,"phase1":22},
 {"name":"RUSH MD Anderson Cancer Center","city":"Chicago","lat":41.8743,"lng":-87.6693,"nci":"None","trials_active":160,"phase1":28},
 {"name":"City of Hope Chicago","city":"Zion","lat":42.4592,"lng":-87.8290,"nci":"None","trials_active":110,"phase1":20},
 {"name":"OSF HealthCare Cancer Institute","city":"Peoria","lat":40.6936,"lng":-89.5923,"nci":"None","trials_active":60,"phase1":8},
 {"name":"Carle Cancer Institute","city":"Urbana","lat":40.1106,"lng":-88.2073,"nci":"None","trials_active":75,"phase1":10},
 {"name":"Simmons Cancer Institute at SIU Medicine","city":"Springfield","lat":39.7817,"lng":-89.6501,"nci":"None","trials_active":55,"phase1":7},
 {"name":"Memorial Care / Springfield Clinic Oncology","city":"Springfield","lat":39.7990,"lng":-89.6540,"nci":"None","trials_active":40,"phase1":4},
 {"name":"UW Health Cancer Center (Rockford)","city":"Rockford","lat":42.2711,"lng":-89.0940,"nci":"None","trials_active":45,"phase1":5},
 {"name":"Southern Illinois Healthcare Cancer Institute","city":"Carbondale","lat":37.7273,"lng":-89.2168,"nci":"None","trials_active":30,"phase1":3},
 {"name":"Edward-Elmhurst / Northwestern Medicine (Naperville)","city":"Naperville","lat":41.7508,"lng":-88.1535,"nci":"None","trials_active":50,"phase1":6},
]

def haversine(lat1,lon1,lat2,lon2):
    R=3958.8
    p1,p2=math.radians(lat1),math.radians(lat2)
    dphi=math.radians(lat2-lat1); dl=math.radians(lon2-lon1)
    a=math.sin(dphi/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

def centroid(geom):
    # area-weighted centroid of largest ring set; simple average of polygon vertices
    coords=[]
    def collect(c):
        if isinstance(c[0],(float,int)):
            coords.append(c)
        else:
            for x in c: collect(x)
    collect(geom['coordinates'])
    xs=[c[0] for c in coords]; ys=[c[1] for c in coords]
    return sum(ys)/len(ys), sum(xs)/len(xs)  # lat, lng

ROAD_FACTOR=1.27   # straight-line -> road distance multiplier
AVG_MPH=52         # blended highway/rural speed for drive-time estimate

# ---- REAL county incidence: State Cancer Profiles / ISCR export (2018-2022) ----
# All Cancer Sites, all races, both sexes, all ages. Age-adjusted rate per 100k
# and average annual case count, keyed by county FIPS.
import csv, os
INCIDENCE_CSV = 'incidence_scp_2018_2022.csv'
if not os.path.exists(INCIDENCE_CSV):
    INCIDENCE_CSV = os.path.join('data', 'incidence_scp_2018_2022.csv')

def load_incidence(path):
    out = {}
    state_rate = 445.0
    with open(path, newline='') as fh:
        for parts in csv.reader(fh):
            if len(parts) < 10:
                continue
            fips = parts[1].strip()
            if fips == '17000':                      # statewide row
                try: state_rate = float(parts[3])
                except ValueError: pass
                continue
            if not (fips.startswith('17') and len(fips) == 5 and fips != '17000'):
                continue
            try:
                rate = float(parts[3])
                count = int(float(str(parts[9]).replace(',', '').strip()))
            except (ValueError, IndexError):
                continue
            out[fips] = {'rate': rate, 'count': count,
                         'rural_urban': parts[2].strip(), 'trend': parts[10].strip() if len(parts) > 10 else ''}
    return out, state_rate

INCIDENCE, IL_RATE = load_incidence(INCIDENCE_CSV)

rows=[]
for f in geo['features']:
    p=f['properties']
    fips=p['GEO_ID'][-5:]
    name=p['NAME']
    src=pop_il.get(fips,{})
    population=src.get('population',0)
    area=src.get('area', round(p.get('CENSUSAREA',0)))
    density=src.get('density', round(population/area,1) if area else 0)
    lat,lng=centroid(f['geometry'])
    # distances to every center
    dists=sorted(((haversine(lat,lng,c['lat'],c['lng']), c) for c in CENTERS), key=lambda t:t[0])
    nearest_d, nearest_c = dists[0]
    road_mi = nearest_d*ROAD_FACTOR
    drive_min = round(road_mi/AVG_MPH*60)
    def within(minutes):
        cnt=0; tr=0
        for d,c in dists:
            dm=d*ROAD_FACTOR/AVG_MPH*60
            if dm<=minutes:
                cnt+=1; tr+=c['trials_active']
        return cnt,tr
    c30,t30=within(30); c60,t60=within(60); c90,t90=within(90)
    inc=INCIDENCE.get(fips)
    if inc:
        annual_cases=inc['count']; rate=inc['rate']; rural_urban=inc['rural_urban']; trend=inc['trend']
        is_real=True
    else:                                           # fallback if a county is missing from the CSV
        rate=IL_RATE; annual_cases=round(population*IL_RATE/100000)
        rural_urban=""; trend=""; is_real=False
    rows.append({
        "fips":fips,"county":name,"population":population,"area_sqmi":area,
        "density":density,"lat":round(lat,4),"lng":round(lng,4),
        "annual_cases":annual_cases,"incidence_per100k":rate,"incidence_real":is_real,
        "rural_urban":rural_urban,"trend":trend,
        "nearest_center":nearest_c['name'],"nearest_city":nearest_c['city'],
        "nearest_miles":round(road_mi,1),"drive_min":drive_min,
        "centers_30":c30,"centers_60":c60,"centers_90":c90,
        "trials_60":t60,"trials_90":t90,
    })

# ---- Access-to-Innovation Index ----
# Higher index = greater UNMET need (high burden + poor trial access).
# Normalize burden (real annual cases) and access-gap (drive time, few nearby trials) to 0-100.
maxcases=max(r['annual_cases'] for r in rows)
maxdrive=max(r['drive_min'] for r in rows)
maxtr90=max(r['trials_90'] for r in rows) or 1
for r in rows:
    burden = r['annual_cases']/maxcases                     # 0..1
    gap_drive = r['drive_min']/maxdrive                      # 0..1 (farther = worse)
    gap_trials = 1 - (r['trials_90']/maxtr90)                # 0..1 (fewer trials = worse)
    access_gap = 0.55*gap_drive + 0.45*gap_trials
    # weight so both burden and gap matter; sqrt keeps mid values visible
    idx = 100*math.sqrt(max(burden,0.02)*max(access_gap,0.02))
    r['access_gap']=round(access_gap*100,1)
    r['index']=round(idx,1)

# rank
for i,r in enumerate(sorted(rows,key=lambda x:-x['index']),1):
    r['rank']=i

real_n=sum(1 for r in rows if r['incidence_real'])
json.dump({"generated_note":f"Population, density, geography, and cancer incidence are REAL: county age-adjusted incidence and annual case counts are from the Illinois State Cancer Registry / State Cancer Profiles (All Cancer Sites, 2018-2022). Trial counts remain illustrative placeholders pending a ClinicalTrials.gov load.",
           "incidence_source":"Illinois State Cancer Registry / State Cancer Profiles (US Cancer Statistics), All Cancer Sites, 2018-2022, age-adjusted to 2000 US std population.",
           "incidence_real_counties":real_n,
           "il_rate_per100k":IL_RATE,"road_factor":ROAD_FACTOR,"avg_mph":AVG_MPH,
           "counties":rows}, open('counties_out.json','w'))
json.dump({"centers":CENTERS}, open('centers_out.json','w'), indent=2)

top=sorted(rows,key=lambda x:-x['index'])[:8]
print(f"Real incidence loaded for {real_n}/{len(rows)} counties. Statewide rate {IL_RATE}/100k.")
print("Top unmet-need counties (index):")
for r in top: print(f"  {r['rank']:>2} {r['county']:<12} idx={r['index']:>5} rate={r['incidence_per100k']:>5}/100k drive={r['drive_min']:>3}min cases={r['annual_cases']}")
print("Total annual cases:", sum(r['annual_cases'] for r in rows))
