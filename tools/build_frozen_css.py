#!/usr/bin/env python3
"""Union of every stylesheet + inline <style> across rendered pages, in cascade-preserving order -> one frozen.css.
Usage: build_frozen_css.py <out.css> <html or html.gz files...>   (order of files = priority for first appearance)"""
import re, sys, gzip, hashlib, html, urllib.request
OUT=sys.argv[1]; files=sys.argv[2:]
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140 Safari/537.36"; ORIGIN="https://www.socialeurope.eu/"
cache={}
def fetch(href):
    if href not in cache:
        r=urllib.request.Request(href,headers={'User-Agent':UA}); css=urllib.request.urlopen(r,timeout=60).read().decode('utf-8','replace')
        base=href.rsplit('/',1)[0]+'/'
        css=re.sub(r'url\((["\']?)(?!data:|https?:|//|/)',lambda m:'url('+m.group(1)+base,css); css=re.sub(r'url\((["\']?)/(?!/)',lambda m:'url('+m.group(1)+ORIGIN,css)
        cache[href]=css
    return cache[href]
order=[]; units={}
def merge(seq):
    prev=None
    for k in seq:
        if k not in order: order.insert(order.index(prev)+1 if prev is not None else len(order),k)
        prev=k
for f in files:
    h=gzip.open(f,'rt',encoding='utf-8',errors='replace').read() if f.endswith('.gz') else open(f,encoding='utf-8',errors='replace').read()
    seq=[]
    for m in re.finditer(r'<link[^>]+rel=["\']stylesheet["\'][^>]*>|<style[^>]*>.*?</style>',h,re.S):
        tok=m.group(0)
        if tok.startswith('<link'):
            href=html.unescape(re.search(r'href=["\']([^"\']+)',tok).group(1)); href=ORIGIN+href.lstrip('/') if href.startswith('/') else href
            key='L:'+re.sub(r'[?&](ver|v)=[^&]*','',href)
            if key not in units:
                css=fetch(href); media=re.search(r'media=["\']([^"\']+)',tok)
                if media and media.group(1) not in('all','screen'): css=f'@media {media.group(1)}{{{css}}}'
                units[key]=f'/* === {href} === */\n{css}\n'
            seq.append(key)
        else:
            body=re.search(r'<style[^>]*>(.*?)</style>',tok,re.S).group(1); body=re.sub(r'/\*# sourceURL=[^*]*\*/','',body).strip()
            if not body: continue
            key='S:'+hashlib.sha1(body.encode()).hexdigest()[:12]
            if key not in units: units[key]=f'/* === inline {key} === */\n{body}\n'
            seq.append(key)
    merge(seq)
css='\n'.join(units[k] for k in order); open(OUT,'w').write(css)
print(f'{OUT}: {len(css)//1024} KB, {len(order)} units ({sum(1 for k in order if k.startswith("L:"))} files, {sum(1 for k in order if k.startswith("S:"))} inline) from {len(files)} pages')
