import csv,glob,re,sys
RAW='/Users/loistanglao/Documents/honors_thesis/data/raw/'
SRC=[('2003','nns_03','provcode'),('2008','nns_08','provcode'),('2011','nns_11','provcode'),
     ('2013','nns_13','provcode'),('2015','nns_15','provcode'),('2018','nns_18_19_21','provhuc'),('2023','nns_23','provhuc')]
def norm(s): return re.sub(r'\s+',' ',s.strip().lower().replace('?','n'))
# harmonized scheme = 2008-2015 province codes
base={}
for r in csv.DictReader(open(glob.glob(RAW+'nns_08/*dictionary*anthrop*')[0],encoding='utf-8-sig')):
    if r['variable_name']=='provcode': base[norm(r['value_label'])]=(r['var_value'].strip(),r['value_label'].strip())
base['batanes']=('9','Batanes')
base['davao del norte']=base['davao (davao del norte)']
# alias: new-scheme name -> (harmonized base name, note)
A={'cagayan province':'cagayan','isabela province':'isabela','quezon province':'quezon',
 'iloilo province':'iloilo','baguio':'benguet','baguio city':'benguet','angeles city':'pampanga',
 'olongapo city':'zambales','lucena city':'quezon','puerto princesa city':'palawan','bacolod city':'negros occidental',
 'iloilo city':'iloilo','cebu city':'cebu','mandaue city':'cebu','lapu-lapu city (opon)':'cebu','tacloban city':'leyte',
 'zamboanga city':'zamboanga del sur','city of isabela':'isabela city','butuan city':'agusan del norte',
 'cagayan de oro':'misamis oriental','iligan city':'lanao del norte','davao city':'davao del sur',
 'davao occidental':'davao del sur','general santos city':'south cotabato','dinagat islands':'surigao del norte',
 'maguindanao':'maguindanao'}
NCR={'ncr - manila first district':'1st','city of manila':'1st',
 'mandaluyong city':'2nd','city of marikina':'2nd','city of pasig':'2nd','quezon city':'2nd','san juan city':'2nd',
 'caloocan city':'3rd','city of malabon':'3rd','city of navotas':'3rd','city of valenzuela':'3rd',
 'las pinas city':'4th','makati city':'4th','city of muntinlupa':'4th','city of paranaque':'4th','pasay city':'4th','pateros':'4th','taguig city':'4th'}
NCRB={'1st':'ncr - manila first district','2nd':'ncr second district','3rd':'ncr third district','4th':'ncr fourth district'}
rows=[];unm=[]
for y,f,v in SRC:
    p=glob.glob(RAW+f+'/*dictionary*anthrop*')[0]
    for r in csv.DictReader(open(p,encoding='utf-8-sig')):
        if r['variable_name']!=v or not r['var_value'].strip(): continue
        c,l=r['var_value'].strip(),r['value_label'].strip(); n=norm(l); n2=n.replace('ñ','n')
        note=''
        if n2 in NCR: key=NCRB[NCR[n2]]; note='NCR city folded into district' if y in('2018','2023') and n2!='ncr - manila first district' else ''
        elif n2 in A: key=A[n2]; note='city/new province folded into parent' if n2 not in('cagayan province','isabela province','quezon province','iloilo province','maguindanao') else ''
        elif n2 in base: key=n2
        elif n2.startswith('ncr'): key=n2
        else: key=None
        if key is None or key not in base: unm.append((y,c,l)); continue
        if n2 in ('davao city','davao occidental'): note='REVIEW: assigned to Davao del Sur'
        if n2=='iloilo city': note='city folded into Iloilo province'
        if y=='2003' and c=='16': note='REVIEW: labelled Cagayan in 2003 dict; code 16 is Camarines Norte in later years'
        if y=='2003' and c=='16': key='camarines norte'
        hc,hn=base[key]
        rows.append(dict(year=y,source_code=c,source_label=l,harmonized_code=hc,harmonized_name=hn,note=note))
# 2003 dictionary lists only 66 of the provinces present in the data; codes are identical to 2008-2015,
# so fill the gaps from the 2008 dictionary for codes that actually occur in the 2003 data.
import pandas as pd
d03=pd.read_csv(glob.glob(RAW+'nns_03/*data-set_anthrop.csv')[0],usecols=['provcode'])
have03={r['source_code'] for r in rows if r['year']=='2003'}
for r in [r for r in rows if r['year']=='2008']:
    if r['source_code'] not in have03 and (d03.provcode==int(r['source_code'])).any():
        rows.append({**r,'year':'2003','note':'INFERRED from 2008 dictionary (code missing from 2003 dictionary)'})
print('UNMATCHED',unm,file=sys.stderr)
rows.sort(key=lambda r:(int(r['harmonized_code']),r['year'],int(r['source_code'])))
import os
os.makedirs(RAW+'../processed',exist_ok=True)
w=csv.DictWriter(open(RAW+'../processed/province_crosswalk_long.csv','w',newline=''),fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
# wide
yrs=[s[0] for s in SRC]; wide={}
for r in rows:
    k=(int(r['harmonized_code']),r['harmonized_name']); d=wide.setdefault(k,{y:[] for y in yrs}); d[r['year']].append(r['source_code'])
out=[]
for (hc,hn),d in sorted(wide.items()):
    out.append({'harmonized_code':hc,'harmonized_name':hn,**{f'code_{y}':'|'.join(d[y]) for y in yrs}})
w=csv.DictWriter(open(RAW+'../processed/province_crosswalk_wide.csv','w',newline=''),fieldnames=list(out[0]));w.writeheader();w.writerows(out)
print(len(rows),len(out))
