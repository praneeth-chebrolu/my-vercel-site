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
IL_RATE=445.0      # statewide age-adjusted incidence per 100k (SEER/ISCR order of magnitude)

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
    est_cases=round(population*IL_RATE/100000)
    rows.append({
        "fips":fips,"county":name,"population":population,"area_sqmi":area,
        "density":density,"lat":round(lat,4),"lng":round(lng,4),
        "est_annual_cases":est_cases,"incidence_per100k":IL_RATE,
        "nearest_center":nearest_c['name'],"nearest_city":nearest_c['city'],
        "nearest_miles":round(road_mi,1),"drive_min":drive_min,
        "centers_30":c30,"centers_60":c60,"centers_90":c90,
        "trials_60":t60,"trials_90":t90,
    })

# ---- Access-to-Innovation Index ----
# Higher index = greater UNMET need (high burden + poor trial access).
# Normalize burden (est_cases) and access-gap (drive time, few nearby trials) to 0-100.
maxcases=max(r['est_annual_cases'] for r in rows)
maxdrive=max(r['drive_min'] for r in rows)
maxtr90=max(r['trials_90'] for r in rows) or 1
for r in rows:
    burden = r['est_annual_cases']/maxcases                 # 0..1
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

json.dump({"generated_note":"Population/density/area and geography are REAL. Incidence is a statewide-rate estimate; trial counts are illustrative placeholders pending ClinicalTrials.gov + ISCR load.",
           "il_rate_per100k":IL_RATE,"road_factor":ROAD_FACTOR,"avg_mph":AVG_MPH,
           "counties":rows}, open('counties_out.json','w'))
json.dump({"centers":CENTERS}, open('centers_out.json','w'), indent=2)

top=sorted(rows,key=lambda x:-x['index'])[:8]
print("Top unmet-need counties (index):")
for r in top: print(f"  {r['rank']:>2} {r['county']:<12} idx={r['index']:>5} pop={r['population']:>8,} drive={r['drive_min']}min cases={r['est_annual_cases']}")
print("Total est cases:", sum(r['est_annual_cases'] for r in rows))
