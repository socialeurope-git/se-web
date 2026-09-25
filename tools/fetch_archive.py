#!/usr/bin/env python3
"""Pull the complete Social Europe archive from the public WordPress REST API plus the rendered pages.
Writes to <out>/: posts.json, pages.json, users.json, media.json, terms.json, coauthors.json, live/<id>.html.gz
Rerunnable: skips what exists. Public endpoints only, no auth."""
import json, os, sys, time, gzip, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
OUT=sys.argv[1]; os.makedirs(OUT+'/live',exist_ok=True); os.chdir(OUT)
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140 Safari/537.36"
BASE="https://www.socialeurope.eu/wp-json/wp/v2/"
def get(u,retries=4):
    for i in range(retries):
        try:
            r=urllib.request.Request(u,headers={'User-Agent':UA,'Accept-Encoding':'identity'}); resp=urllib.request.urlopen(r,timeout=90); return resp.read(), resp.headers
        except urllib.error.HTTPError as e:
            if e.code in (400,404): return None, {}
            time.sleep(2*(i+1))
        except Exception: time.sleep(2*(i+1))
    return None, {}
def collection(name,fields,per=100,extra=''):
    path=f'{name}.json'
    if os.path.exists(path): return json.load(open(path))
    items=[]; page=1
    while True:
        body,h=get(f'{BASE}{name}?per_page={per}&page={page}&_fields={fields}{extra}')
        if body is None: break
        batch=json.loads(body); items+=batch; total=int(h.get('X-WP-TotalPages','1'))
        print(f'{name}: page {page}/{total} ({len(items)})',flush=True)
        if page>=total: break
        page+=1; time.sleep(0.25)
    json.dump(items,open(path,'w')); return items
posts=collection('posts','id,slug,link,date,date_gmt,modified,modified_gmt,status,title,content,excerpt,categories,tags,featured_media,author,coauthors,sticky,format')
pages=collection('pages','id,slug,link,date,modified,title,content,excerpt,parent,menu_order,template,featured_media')
users=collection('users','id,slug,name,description,url,avatar_urls,simple_local_avatar,link')
media=collection('media','id,slug,date,source_url,alt_text,caption,title,mime_type,media_details,post')
cats=collection('categories','id,name,slug,parent,description,count'); tags=collection('tags','id,name,slug,description,count')
json.dump({'categories':cats,'tags':tags},open('terms.json','w'))
# co-authors per post (CAP REST) -> user objects; parallel
if not os.path.exists('coauthors.json'):
    def ca(p):
        body,_=get(f'https://www.socialeurope.eu/wp-json/coauthors/v1/coauthors?post_id={p["id"]}')
        try: return p['id'], [{'id':a.get('id'),'slug':a.get('slug') or a.get('user_nicename'),'name':a.get('display_name') or a.get('name')} for a in json.loads(body)] if body else None
        except Exception: return p['id'], None
    res={}
    with ThreadPoolExecutor(4) as ex:
        for i,(pid,val) in enumerate(ex.map(ca,posts)):
            res[pid]=val
            if i%200==0: print(f'coauthors: {i}/{len(posts)}',flush=True)
    json.dump(res,open('coauthors.json','w')); print('coauthors done, missing:',sum(1 for v in res.values() if v is None))
# rendered pages (SEO head, injected furniture, freeze oracle)
def crawl(p):
    path=f'live/{p["id"]}.html.gz'
    if os.path.exists(path): return 0
    body,_=get(p['link'])
    if body: gzip.open(path,'wb').write(body); return 1
    return -1
done=0; fail=0
with ThreadPoolExecutor(3) as ex:
    for i,r in enumerate(ex.map(crawl,posts+pages)):
        done+= r==1; fail+= r==-1
        if i%200==0: print(f'crawl: {i}/{len(posts)+len(pages)} fetched={done} failed={fail}',flush=True)
print(f'ARCHIVE COMPLETE: posts={len(posts)} pages={len(pages)} users={len(users)} media={len(media)} cats={len(cats)} tags={len(tags)} crawled_now={done} failed={fail}')
