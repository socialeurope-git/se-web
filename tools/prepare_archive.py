#!/usr/bin/env python3
"""Build import + fixture files from the fetched archive.
Inputs : archive/{posts,pages,users,media,terms,coauthors}.json and rendered pages (archive/live/<id>.html.gz, or a dir of <id>.html)
Outputs: archive/wxr-<name>.xml (WXR with block-comment wrapping so the converter keeps figures/accordions verbatim),
         archive/authors.json (slug -> name, bio, url, avatarHtml; import data for sync_bylines.py), archive/fixtures/<id>.json (per-post live widgets)
Usage  : prepare_archive.py <archive_dir> <live_dir> <name> [ids.json]"""
import json, os, re, sys, gzip, html
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
BERLIN=ZoneInfo('Europe/Berlin')
def to_gmt(local):
    """WordPress local time (site timezone Europe/Berlin) -> UTC string. Old posts carry a wrong date_gmt, the local date is the truth."""
    d=datetime.fromisoformat(local).replace(tzinfo=BERLIN); return d.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
from xml.sax.saxutils import escape
A=sys.argv[1]; LIVE=sys.argv[2]; NAME=sys.argv[3]; only=set(json.load(open(sys.argv[4]))) if len(sys.argv)>4 else None
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
posts=json.load(open(f'{A}/posts.json')); pages=json.load(open(f'{A}/pages.json')); users={u['slug']:u for u in json.load(open(f'{A}/users.json'))}
media={m['id']:m for m in json.load(open(f'{A}/media.json'))} if os.path.exists(f'{A}/media.json') else {}
terms=json.load(open(f'{A}/terms.json')); cats={c['id']:c for c in terms['categories']}; tags={t['id']:t for t in terms['tags']}
coauthors=json.load(open(f'{A}/coauthors.json')) if os.path.exists(f'{A}/coauthors.json') else {}
os.makedirs(f'{A}/fixtures',exist_ok=True); os.makedirs(f'{ROOT}/src/se/data',exist_ok=True)
def live_html(pid):
    for p in (f'{LIVE}/{pid}.html.gz', f'{LIVE}/{pid}.html'):
        if os.path.exists(p): return (gzip.open(p,'rt',encoding='utf-8',errors='replace').read() if p.endswith('.gz') else open(p,encoding='utf-8',errors='replace').read())
    return None
def balanced(s,start_re,tags=('div','aside','section','form','figure','table','blockquote','ul','ol','nav','main','article','header','footer','picture')):
    m=re.search(start_re,s)
    if not m: return None,-1,-1
    i=m.start(); depth=0
    for t in re.finditer(r'<(/?)(%s)\b[^>]*?(/?)>'%'|'.join(tags),s[i:]):
        if t.group(3)=='/': continue
        depth+= -1 if t.group(1) else 1
        if depth==0: return s[i:i+t.end()],i,i+t.end()
    return None,-1,-1
def clean_body(entry):
    b=entry
    for marker in ('<div class="ns-content-marker"','<div class="se-author-profile-box'):
        k=b.find(marker)
        if k>=0: b=b[:k]
    b=re.sub(r'<style[^>]*>.*?</style>','',b,flags=re.S)
    # posts without the Novashare marker are cut at the author box, which sits after WordPress's own </div> of .entry-content
    while len(re.findall(r'</div>',b))>len(re.findall(r'<div\b',b)) and b.rstrip().endswith('</div>'):
        b=b.rstrip()[:-6]
    for rx in (r'<aside class="se-rel-inline', r'<div id="mlb2-\d+'):
        while True:
            seg,i,j=balanced(b,rx)
            if seg is None: break
            b=b[:i]+b[j:]
    return b.strip()
VOID={'br','img','hr','source','input','meta','link','wbr','track','embed'}
def top_level(fragment):
    out=[];depth=0;buf=''
    for m in re.finditer(r'<!--.*?-->|<(/?)([a-zA-Z0-9]+)[^>]*?(/?)>|[^<]+',fragment,re.S):
        tok=m.group(0)
        if tok.startswith('<!--'): continue
        if tok.startswith('<'):
            closing,tag,selfc=m.group(1)=='/',m.group(2).lower(),m.group(3)=='/'
            buf+=tok
            if closing: depth-=1
            elif not(tag in VOID or selfc): depth+=1
            if depth<=0:
                depth=0
                if buf.strip(): out.append(buf.strip())
                buf=''
        else:
            buf+=tok
            if depth<=0 and buf.strip(): out.append(buf.strip()); buf=''
    if buf.strip(): out.append(buf.strip())
    return out
def wrap_blocks(body):
    """Wrap top-level elements in Gutenberg comments: plain p/h/ul/ol/blockquote become editable blocks (with the
    attributes the converter needs), everything else stays raw HTML so the rendered markup is preserved verbatim."""
    out=[]
    for el in top_level(body):
        m=re.match(r'<([a-zA-Z0-9]+)([^>]*)>',el); tag=m.group(1).lower() if m else ''; attrs=m.group(2) if m else ''
        cls=re.search(r'class="([^"]*)"',attrs); cls=set(cls.group(1).split()) if cls else set()
        plain_cls=cls<= {'wp-block-paragraph','wp-block-heading','wp-block-list','wp-block-quote'} | {f'p{i}' for i in range(1,10)}
        text=re.sub(r'<[^>]+>','',el).replace('&nbsp;','').strip()
        if tag=='p' and plain_cls and 'style=' not in el and not re.search(r'<(img|figure|iframe|table|video|audio|picture|br|font)',el) and text:   # <br>, inline styles and <font> are dropped by the converter -> keep verbatim
            out.append(f'<!-- wp:paragraph -->\n{el}\n<!-- /wp:paragraph -->')
        elif tag in('h1','h2','h3','h4','h5','h6') and plain_cls and 'style=' not in attrs and ' id=' not in attrs:   # heading anchors (id) are dropped by the converter -> keep raw
            lvl=int(tag[1]); attr='' if lvl==2 else ' {"level":%d}'%lvl
            out.append(f'<!-- wp:heading{attr} -->\n{el}\n<!-- /wp:heading -->')
        elif tag in('ul','ol') and plain_cls and '<ul' not in el[3:] and '<ol' not in el[3:] and '<img' not in el and '<br' not in el and 'style=' not in el:   # <br>/styles inside items would be dropped
            attr=' {"ordered":true}' if tag=='ol' else ''
            out.append(f'<!-- wp:list{attr} -->\n{el}\n<!-- /wp:list -->')
        elif tag=='blockquote' and plain_cls and '<img' not in el and not re.search(r'<(ul|ol|h[1-6])',el):
            out.append(f'<!-- wp:quote -->\n{el}\n<!-- /wp:quote -->')
        else:
            out.append(f'<!-- wp:html -->\n{el}\n<!-- /wp:html -->')
    return '\n\n'.join(out)
def cdata(s): return '<![CDATA['+s.replace(']]>',']]]]><![CDATA[>')+']]>'
authors={}
def author_from_hero(h):
    """capture exact avatar markup + name per author slug from the hero byline (inline for one author, stacked for several)"""
    res=[]
    stack=re.search(r'<div class="se-hero__byline se-hero__byline--stacked">(.*?)<p class="se-hero__names">(.*?)</p></div>',h,re.S)
    if stack:
        avs={m.group(1):m.group(2) for m in re.finditer(r'<a class="se-avatar se-avatar--stack" href="https://www\.socialeurope\.eu/author/([^"/]+)/?"[^>]*>(.*?)</a>',stack.group(1),re.S)}
        for m in re.finditer(r'<a class="se-hero__name" href="https://www\.socialeurope\.eu/author/([^"/]+)/?" rel="author">([^<]*)</a>',stack.group(2)):
            slug,name=m.group(1),html.unescape(m.group(2)).strip(); inner=avs.get(slug,'')
            av=f'<span class="se-avatar">{inner}</span>' if '<picture' in inner else (f'<span class="se-avatar se-avatar--initials">{inner.strip()}</span>' if inner.strip() and '<' not in inner else '')
            res.append((slug,name,av))
            a=authors.setdefault(slug,{'slug':slug,'name':name,'avatarHtml':'','bio':'','url':f'https://www.socialeurope.eu/author/{slug}'})
            if av and (not a['avatarHtml'] or ('<picture' in av and '<picture' not in a['avatarHtml'])): a['avatarHtml']=av
            u=users.get(slug)
            if u and not a['bio']: a['bio']=u.get('description',''); a['name']=u.get('name') or name
        return res
    for m in re.finditer(r'<a class="se-hero__author" href="https://www\.socialeurope\.eu/author/([^"/]+)/?" rel="author">(<span class="se-avatar[^"]*">.*?</span>)?<span class="se-hero__name">([^<]*)</span></a>',h,re.S):
        slug,av,name=m.group(1),m.group(2) or '',html.unescape(m.group(3)).strip()
        # avatar span may be '<span class="se-avatar"><picture>...</picture></span>' or initials span
        if av and 'picture' in av:
            seg,_,_=balanced(av,r'<span class="se-avatar"',tags=('span','picture'))
            av=seg or av
        res.append((slug,name,av))
        a=authors.setdefault(slug,{'slug':slug,'name':name,'avatarHtml':'','bio':'','url':f'https://www.socialeurope.eu/author/{slug}'})
        if av and (not a['avatarHtml'] or ('<picture' in av and '<picture' not in a['avatarHtml'])): a['avatarHtml']=av
        u=users.get(slug)
        if u and not a['bio']: a['bio']=u.get('description','') ; a['name']=u.get('name') or name
    return res
items=[]; fixtures_written=0; missing_live=0; att_seen=set()
# Every media item of the site becomes a WXR attachment: EmDash's importer downloads the originals into its
# storage, registers them in the Media Library and returns an old->new URL map (fresh_import.sh). Featured
# images link via _thumbnail_id; portraits (Simple Local Avatars uploads) are attachments too.
def att_item(m):
    url=m['source_url']; title=html.unescape(re.sub('<[^>]+>','',(m.get('title') or {}).get('rendered','')))
    cap=html.unescape(re.sub('<[^>]+>','',(m.get('caption') or {}).get('rendered','')))
    d=m.get('date') or '2014-01-01T00:00:00'
    return (f'<item><title>{cdata(title or os.path.basename(url))}</title><link>{escape(url)}</link><dc:creator>{cdata("social-europe")}</dc:creator><guid isPermaLink="false">{escape(url)}</guid>'
            f'<content:encoded>{cdata("")}</content:encoded><excerpt:encoded>{cdata(cap)}</excerpt:encoded><wp:post_id>{m["id"]}</wp:post_id><wp:post_date>{to_gmt(d)}</wp:post_date><wp:post_date_gmt>{to_gmt(d)}</wp:post_date_gmt>'
            f'<wp:post_name>{escape(m.get("slug") or os.path.splitext(os.path.basename(url))[0])}</wp:post_name><wp:status>inherit</wp:status><wp:post_parent>{m.get("post") or 0}</wp:post_parent><wp:post_type>attachment</wp:post_type>'
            f'<wp:attachment_url>{escape(url)}</wp:attachment_url><wp:postmeta><wp:meta_key>_wp_attachment_image_alt</wp:meta_key><wp:meta_value>{cdata(m.get("alt_text") or "")}</wp:meta_value></wp:postmeta></item>')
if only is None:
    for m in media.values():
        if m.get('source_url'): items.append(att_item(m)); att_seen.add(m['id'])
sel=[p for p in posts if (only is None or p['id'] in only)]
for p in sel:
    pid=p['id']; h=live_html(pid)
    if not h: missing_live+=1; continue
    ec_seg=h.split('<div class="entry-content"',1)
    if len(ec_seg)<2: missing_live+=1; continue
    entry='<div class="entry-content"'+ec_seg[1].split('</article>')[0]
    inner=entry[entry.find('>')+1:]                      # drop the .entry-content wrapper itself
    body=clean_body(inner); content=wrap_blocks(body)
    bylines=author_from_hero(h)
    for m in re.finditer(r'<div class="se-author-profile-box se-author-profile"><h4 class="se-box-header">AUTHOR PROFILE</h4><div class="se-box-inner"><div class="se-author-avatar">(.*?)</div><div class="se-author-text"><h3 class="se-author-name-title"><a href="https://www\.socialeurope\.eu/author/([^"/]+)/?">',h,re.S):
        a=authors.get(m.group(2))
        if a is not None and not a.get('avatarBoxHtml'): a['avatarBoxHtml']=m.group(1)
    # bio from the live author box (co-authors who never were post_author are not in the REST users list)
    for m in re.finditer(r'<h3 class="se-author-name-title"><a href="https://www\.socialeurope\.eu/author/([^"/]+)/?">[^<]*</a></h3><div class="se-author-bio-text">(.*?)</div></div></div></div>',h,re.S):
        a=authors.get(m.group(1)); bio=re.sub(r'^\s*<p>|</p>\s*$','',m.group(2).strip())
        if a is not None and not a.get('bio') and bio: a['bio']=bio
    if not bylines and coauthors.get(str(pid)):
        bylines=[(a['slug'],a['name'],'') for a in coauthors[str(pid)]]
    creator=bylines[0][0] if bylines else 'social-europe'
    title=html.unescape(re.sub('<[^>]+>','',p['title']['rendered']))
    # standfirst: only what the live hero shows (posts without a manual excerpt have no dek element at all)
    hero_seg=h.split('class="entry-content"')[0]
    dm=re.search(r'<p class="[^"]*se-hero__dek[^"]*">(.*?)</p>',hero_seg,re.S); dek=html.unescape(re.sub('<[^>]+>','',dm.group(1))).strip() if dm else ''
    t=''.join(f'<category domain="category" nicename="{cats[c]["slug"]}">{cdata(cats[c]["name"])}</category>' for c in p['categories'] if c in cats)
    t+=''.join(f'<category domain="post_tag" nicename="{tags[x]["slug"]}">{cdata(tags[x]["name"])}</category>' for x in p['tags'] if x in tags)
    meta=''
    fm=p.get('featured_media'); fmedia=media.get(fm)
    if fmedia: meta=f'<wp:postmeta><wp:meta_key>_thumbnail_id</wp:meta_key><wp:meta_value>{fm}</wp:meta_value></wp:postmeta>'
    items.append(f'''<item><title>{cdata(title)}</title><link>{escape(p['link'])}</link><dc:creator>{cdata(creator)}</dc:creator><guid isPermaLink="false">https://www.socialeurope.eu/?p={pid}</guid>
<content:encoded>{cdata(content)}</content:encoded><excerpt:encoded>{cdata(dek)}</excerpt:encoded><wp:post_id>{pid}</wp:post_id><wp:post_date>{to_gmt(p['date'])}</wp:post_date><wp:post_date_gmt>{to_gmt(p['date'])}</wp:post_date_gmt><wp:post_modified>{to_gmt(p['modified'])}</wp:post_modified><wp:post_modified_gmt>{to_gmt(p['modified'])}</wp:post_modified_gmt><wp:comment_status>closed</wp:comment_status><wp:post_name>{escape(p['slug'])}</wp:post_name><wp:status>publish</wp:status><wp:post_parent>0</wp:post_parent><wp:post_type>post</wp:post_type>{t}{meta}</item>''')
    # per-post fixtures from the live page (widgets whose data will later come from services)
    rel_inline,_,_=balanced(entry,r'<aside class="se-rel-inline'); rel_band,_,_=balanced(h,r'<section class="se-rel-band"')
    hero_bg=re.search(r'--inline-bg-image: url\(\'([^\']+)\'\)',h)
    head_title=re.search(r'<title>(.*?)</title>',h,re.S)
    # SEO facts from the live head: author Person @id (TSF hashes the user e-mail, not reproducible), image size, modified date
    lds=[m.group(1) for m in re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>',h,re.S)]
    personId=None; personDesc=None; imgw=imgh=None; modified=None; wordcount=None; lddesc=None; ldpub=None; ldhead=None; ldkw=None; seo_author=None; ldauthors=None
    for ld in lds:
        try: d=json.loads(ld)
        except Exception: continue
        if '@graph' in d:
            for node in d['@graph']:
                if node.get('@type')=='WebPage' and isinstance(node.get('author'),dict): personId=node['author'].get('@id'); personDesc=node['author'].get('description'); seo_author=node['author']
        elif d.get('@type')=='NewsArticle':
            img=d.get('image') or {}; imgw,imgh=img.get('width'),img.get('height'); modified=d.get('dateModified'); wordcount=d.get('wordCount'); lddesc=d.get('description'); ldpub=d.get('datePublished'); ldhead=d.get('headline'); ldkw=d.get('keywords'); ldauthors=d.get('author')
    pass
    ogm=re.search(r'<meta property="article:modified_time" content="([^"]*)"',h)
    mdesc=re.search(r'<meta name="description" content="([^"]*)"',h); ogdesc=re.search(r'<meta property="og:description" content="([^"]*)"',h); ogt=re.search(r'<meta property="og:title" content="([^"]*)"',h)
    fx={'id':pid,'slug':p['slug'],'bylines':[{'slug':s,'name':n} for s,n,_ in bylines],'heroBg':hero_bg.group(1) if hero_bg else None,'relInline':rel_inline,'relBand':rel_band,'title':html.unescape(head_title.group(1).strip()) if head_title else title,'dek':dek,'imageW':imgw,'imageH':imgh,'modified':modified,'modifiedDay':ogm.group(1) if ogm else None,'wordCount':wordcount,'ldDescription':lddesc,'ldPublished':ldpub,'ldHeadline':ldhead,'ldKeywords':ldkw,'seoAuthor':seo_author,'ldAuthors':ldauthors,'ogTitle':html.unescape(ogt.group(1)) if ogt else None,'description':html.unescape(mdesc.group(1)) if mdesc else None,'ogDescription':html.unescape(ogdesc.group(1)) if ogdesc else None,'bodyClass':re.search(r'<body class="([^"]*)"',h).group(1),'articleClass':(re.search(r'<article id="post-\d+" class="([^"]*)"',h) or [None,''])[1]}
    json.dump(fx,open(f'{A}/fixtures/{pid}.json','w')); fixtures_written+=1
# pages: body from the rendered live page (archive/live-pages/<slug>.html), fixture with the template wrappers
PAGES_DIR=os.path.join(os.path.dirname(A),'archive','live-pages') if os.path.basename(A)=='archive' else os.path.join(A,'live-pages')
for pg in pages:
    if only is not None and pg['id'] not in only and 'pages' not in (sys.argv[5:] or []): continue
    lp=os.path.join(PAGES_DIR,f"{pg['slug']}.html"); h=open(lp,encoding='utf-8',errors='replace').read() if os.path.exists(lp) else None
    title=html.unescape(re.sub('<[^>]+>','',pg['title']['rendered']))
    if h:
        ec=h.split('<div class="entry-content"',1)[1]; ec=ec[ec.find('>')+1:].split('</article>')[0]
        # drop the closing </div> of .entry-content and anything after it
        depth=1; end=len(ec)
        for t in re.finditer(r'<(/?)div\b[^>]*>',ec):
            depth+= -1 if t.group(1) else 1
            if depth==0: end=t.start(); break
        body=ec[:end].strip()
        intro=re.search(r'<section class="se-ed-intro">(.*?)</section>',h,re.S)
        after_article=h[h.find('</article>'):]                       # a CTA inside the content is part of the content, not a page-level block
        cta=re.search(r'<section class="se-ed-cta">.*?</section>',after_article,re.S)
        fi=re.search(r'<div class="featured-image page-header-image[^"]*">.*?</div>',h,re.S)
        ogi=re.search(r'<meta property="og:image" content="([^"]*)"',h); ogw=re.search(r'<meta property="og:image:width" content="(\d+)"',h); ogh=re.search(r'<meta property="og:image:height" content="(\d+)"',h); oga=re.search(r'<meta property="og:image:alt" content="([^"]*)"',h); desc=re.search(r'<meta name="description" content="([^"]*)"',h); ogd=re.search(r'<meta property="og:description" content="([^"]*)"',h)
        fx={'id':pg['id'],'ogDescription':html.unescape(ogd.group(1)) if ogd else None,'slug':pg['slug'],'title':title,'template':pg.get('template') or 'default','ogImage':html.unescape(ogi.group(1)) if ogi else None,'ogImageW':int(ogw.group(1)) if ogw else None,'ogImageH':int(ogh.group(1)) if ogh else None,'ogImageAlt':html.unescape(oga.group(1)) if oga else None,'description':html.unescape(desc.group(1)) if desc else None,'bodyClass':re.search(r'<body class="([^"]*)"',h).group(1),
            'introHtml':intro.group(0) if intro else None,'ctaHtml':cta.group(0) if cta else None,'featuredHtml':fi.group(0) if fi else None,
            'headTitle':html.unescape(re.search(r'<title>(.*?)</title>',h,re.S).group(1).strip()),'articleClass':(re.search(r'<article id="post-\d+" class="([^"]*)"',h) or [None,''])[1],'hasSidebar':'id="right-sidebar"' in h}
        json.dump(fx,open(f'{A}/fixtures/page-{pg["slug"]}.json','w'))
    else:
        body=pg['content']['rendered']
    items.append(f'''<item><title>{cdata(title)}</title><link>{escape(pg['link'])}</link><dc:creator>social-europe</dc:creator><guid isPermaLink="false">https://www.socialeurope.eu/?page_id={pg['id']}</guid><content:encoded>{cdata(wrap_blocks(body))}</content:encoded><wp:post_id>{pg['id']}</wp:post_id><wp:post_date>{pg['date'].replace('T',' ')}</wp:post_date><wp:post_date_gmt>{pg['date'].replace('T',' ')}</wp:post_date_gmt><wp:post_modified>{pg['modified'].replace('T',' ')}</wp:post_modified><wp:post_name>{escape(pg['slug'])}</wp:post_name><wp:status>publish</wp:status><wp:post_parent>{pg.get('parent',0)}</wp:post_parent><wp:post_type>page</wp:post_type></item>''')
authors_xml=''.join(f'<wp:author><wp:author_id>{i+1}</wp:author_id><wp:author_login>{cdata(a["slug"])}</wp:author_login><wp:author_email>{cdata(a["slug"]+"@example.invalid")}</wp:author_email><wp:author_display_name>{cdata(a["name"])}</wp:author_display_name></wp:author>' for i,a in enumerate(authors.values()))
authors_xml+='<wp:author><wp:author_id>9999</wp:author_id><wp:author_login>social-europe</wp:author_login><wp:author_email>editor@example.invalid</wp:author_email><wp:author_display_name>Social Europe</wp:author_display_name></wp:author>'
cx=''.join(f'<wp:category><wp:term_id>{c["id"]}</wp:term_id><wp:category_nicename>{c["slug"]}</wp:category_nicename><wp:category_parent></wp:category_parent><wp:cat_name>{cdata(c["name"])}</wp:cat_name></wp:category>' for c in cats.values())
tx=''.join(f'<wp:tag><wp:term_id>{t["id"]}</wp:term_id><wp:tag_slug>{t["slug"]}</wp:tag_slug><wp:tag_name>{cdata(t["name"])}</wp:tag_name></wp:tag>' for t in tags.values())
xml=f'''<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:wfw="http://wellformedweb.org/CommentAPI/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:wp="http://wordpress.org/export/1.2/">
<channel><title>Social Europe</title><link>https://www.socialeurope.eu</link><description>Politics, economy and employment &amp; labour</description><language>en-GB</language><wp:wxr_version>1.2</wp:wxr_version><wp:base_site_url>https://www.socialeurope.eu</wp:base_site_url><wp:base_blog_url>https://www.socialeurope.eu</wp:base_blog_url>
{authors_xml}{cx}{tx}<generator>https://wordpress.org/?v=7.1</generator>
{''.join(items)}
</channel></rss>'''
xml=re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',xml)   # control characters are not allowed in XML, not even inside CDATA
out=f'{A}/wxr-{NAME}.xml'; open(out,'w').write(xml)
import xml.dom.minidom as md; md.parseString(xml.encode())
# merge authors into the theme data file (keep existing avatar markup if already captured)
ap=f'{A}/authors.json'; existing=json.load(open(ap)) if os.path.exists(ap) else {}
for s,a in authors.items():
    e=existing.setdefault(s,a)
    for k,v in a.items():
        if v and (not e.get(k) or (k in('avatarHtml','avatarBoxHtml') and '<picture' in str(v) and '<picture' not in str(e.get(k)))): e[k]=v
json.dump(existing,open(ap,'w'),indent=0,ensure_ascii=False)
print(f'{out}: {len(sel)-missing_live} posts, {len(att_seen)} attachments, {sum(1 for pg in pages if only is None or pg["id"] in only)} pages, {len(authors)} authors (total in data file {len(existing)}), fixtures {fixtures_written}, missing live pages {missing_live}, {len(xml)//1024} KB')
