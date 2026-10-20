"""Add a `super_province` column (named as in the Natural Earth admin-1 shapefile) to the NNS data files.

Run province_crosswalk.py first. This script
  1. adds `super_province` to the crosswalk CSVs (cities/small units folded into the big province, NCR as one unit),
  2. writes shapefile_super_province_lookup.csv (every Philippine polygon -> super_province, for dissolving the map),
  3. writes copies of the NNS data files with `super_province` into data/processed/yearly_nns_only_data/,
  4. documents which provinces have no data in each year (DROPPED_PROVINCES.md / .csv).
Raw files are never modified. socio_dem files are not used.
"""
import glob, os
import pandas as pd
import geopandas as gpd

ROOT = '/Users/loistanglao/Documents/honors_thesis/data/'
RAW, PROC = ROOT + 'raw/', ROOT + 'processed/'
OUT = PROC + 'yearly_nns_only_data/'
SHP = RAW + 'ne_10m_admin_1_states_provinces/ne_10m_admin_1_states_provinces.shp'
os.makedirs(OUT, exist_ok=True)

# ---- shapefile polygons -> super_province ----------------------------------
shp = gpd.read_file(SHP)
shp = shp[shp.admin == 'Philippines'].copy()
CITY_TO_PROV = {  # (polygon name, gn_name) is needed for the duplicated names
    'Angeles': 'Pampanga', 'Bacolod': 'Negros Occidental', 'Baguio': 'Benguet', 'Butuan': 'Agusan del Norte',
    'Cagayan de Oro': 'Misamis Oriental', 'Dagupan': 'Pangasinan', 'Davao': 'Davao del Sur',
    'General Santos': 'South Cotabato', 'Iligan': 'Lanao del Norte', 'Lapu-Lapu': 'Cebu', 'Lucena': 'Quezon',
    'Mandaue': 'Cebu', 'Naga': 'Camarines Sur', 'Olongapo': 'Zambales', 'Ormoc': 'Leyte',
    'Puerto Princesa': 'Palawan', 'Santiago': 'Isabela', 'Tacloban': 'Leyte', 'Zamboanga': 'Zamboanga del Sur',
}
NCR_CITIES = {'Caloocan', 'Las Pinas', 'Makati', 'Malabon', 'Mandaluyong City', 'Manila', 'Marikina', 'Muntinlupa',
              'Navotas', 'Paranaque', 'Pasay', 'Pasig', 'Pateros', 'Quezon City', 'San Juan', 'Taguig', 'Valenzuela'}
def poly_super(r):
    n, t = r['name'], r['type_en']
    if n in NCR_CITIES: return 'NCR'
    if n in CITY_TO_PROV: return CITY_TO_PROV[n]
    if n in ('Cebu', 'Iloilo'): return n            # city and province polygons both belong to the province
    if n == 'Cotabato': return 'Maguindanao' if 'City' in str(t) else 'Cotabato'
    return n
shp['super_province'] = shp.apply(poly_super, axis=1)
lookup = shp[['adm1_code', 'name', 'type_en', 'gn_name', 'super_province']].sort_values(['super_province', 'name'])
lookup.to_csv(PROC + 'shapefile_super_province_lookup.csv', index=False)
shp_supers = set(shp.super_province)

# ---- crosswalk -> super_province -------------------------------------------
OVERRIDE = {'davao (davao del norte)': 'Davao del Norte', 'western samar': 'Samar',
            'occidental mindoro': 'Mindoro Occidental', 'oriental mindoro': 'Mindoro Oriental',
            'north cotabato': 'Cotabato', 'isabela city': 'Basilan', 'cotabato city': 'Maguindanao'}
shp_lower = {s.lower(): s for s in shp_supers}
def to_super(hname):
    h = hname.strip().lower()
    if h.startswith('ncr'): return 'NCR'
    if h in OVERRIDE: return OVERRIDE[h]
    return shp_lower.get(h)
xl = pd.read_csv(PROC + 'province_crosswalk_long.csv', dtype=str).drop(columns=['super_province'], errors='ignore')
xl.insert(5, 'super_province', xl.harmonized_name.map(to_super))
bad = xl[xl.super_province.isna()]
assert bad.empty, bad
assert set(xl.super_province) <= shp_supers
xl.to_csv(PROC + 'province_crosswalk_long.csv', index=False)
xw = pd.read_csv(PROC + 'province_crosswalk_wide.csv', dtype=str).drop(columns=['super_province'], errors='ignore')
xw.insert(2, 'super_province', xw.harmonized_name.map(to_super))
xw.to_csv(PROC + 'province_crosswalk_wide.csv', index=False)

# ---- data files --------------------------------------------------------------
def rd(pat): return pd.read_csv(glob.glob(pat)[0], low_memory=False, dtype={'ms_psucode': str})
FILES = [  # output name, source, crosswalk year, province column
    ('anthrop_2003', RAW + 'nns_03/*data-set_anthrop.csv', '2003', 'provcode'),
    ('anthrop_2008', RAW + 'nns_08/*data-set_anthrop.csv', '2008', 'provcode'),
    ('anthrop_2011', RAW + 'nns_11/*data-set_anthrop.csv', '2011', 'provcode'),
    ('anthrop_2013', RAW + 'nns_13/*data-set_anthrop.csv', '2013', 'provcode'),
    ('anthrop_2015', RAW + 'nns_15/*data-set_anthrop.csv', '2015', 'provcode'),
    ('anthrop_18_19_21', RAW + 'nns_18_19_21/*data-set_anthrop.csv', '2018', 'provhuc'),
    ('socio_18_19_21', RAW + 'nns_18_19_21/*data-set_socio.csv', '2018', 'provhuc'),
    ('anthrop_23', RAW + 'nns_23/*data-set_anthrop.csv', '2023', 'provhuc'),
    ('socio_23', RAW + 'nns_23/*data-set_socio.csv', '2023', 'provhuc'),
    ('merged_anthro_socio_18_19_21', PROC + 'merged_anthro_socio_18_19_21.csv', '2018', 'provhuc'),
    ('merged_anthro_socio_23', PROC + 'merged_anthro_socio_23.csv', '2023', 'provhuc'),
]
def code_str(s): return pd.to_numeric(s, errors='coerce').astype('Int64').astype(str)
present = {}   # (file, year) -> set of super_provinces with data
report = []
for name, pat, xy, pc in FILES:
    d = rd(pat)
    m = xl[xl.year == xy].drop_duplicates('source_code').set_index('source_code').super_province
    d['super_province'] = code_str(d[pc]).map(m)
    d.to_csv(OUT + name + '.csv', index=False)
    n_un = d.super_province.isna().sum()
    unm = sorted(d.loc[d.super_province.isna(), pc].dropna().unique().tolist())
    print(f'{name}: {len(d):,} rows, {n_un} unmatched {unm}')
    yrcol = d['enns_year'] if 'enns_year' in d else pd.Series(xy, index=d.index)
    if name.startswith('merged'): continue
    for y, g in d.groupby(yrcol):
        have = set(g.super_province.dropna())
        missing = sorted(shp_supers - have)
        dict_codes = set(xl[xl.year == xy].source_code)
        report.append(dict(file=name, survey_year=int(y), n_super_provinces_with_data=len(have),
                           n_missing=len(missing), missing_super_provinces='; '.join(missing),
                           rows_unmatched=int(n_un), unmatched_codes='; '.join(map(str, unm))))
rep = pd.DataFrame(report)
rep.to_csv(OUT + 'DROPPED_PROVINCES.csv', index=False)
with open(OUT + 'DROPPED_PROVINCES.md', 'w') as f:
    f.write('# Provinces with no data, by survey year\n\n'
            f'Reference list: the {len(shp_supers)} super-provinces in the Natural Earth shapefile after folding cities into '
            'their province and NCR into one unit (see `../shapefile_super_province_lookup.csv`).\n'
            '"Missing" = no respondent in that year\'s file falls in the super-province. '
            'Provinces are never dropped by the script itself; missing ones were absent from the source data/dictionary.\n\n')
    for _, r in rep.iterrows():
        f.write(f"## {r.file} - {r.survey_year}\n- Super-provinces with data: {r.n_super_provinces_with_data} of {len(shp_supers)}\n"
                f"- Missing ({r.n_missing}): {r.missing_super_provinces or 'none'}\n"
                f"- Rows whose code is not in the crosswalk: {r.rows_unmatched}"
                f"{' (codes: ' + r.unmatched_codes + ')' if r.unmatched_codes else ''}\n\n")
