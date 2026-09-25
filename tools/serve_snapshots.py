#!/usr/bin/env python3
"""Serve crawled live pages (archive/live/<id>.html.gz) as control pages for pixel diffs: /control/<id>.html
Root-relative URLs are made absolute so images/scripts load from the live site. Usage: serve_snapshots.py <archive_dir> <port>"""
import sys, gzip, re, os
from http.server import BaseHTTPRequestHandler, HTTPServer
A=sys.argv[1]; PORT=int(sys.argv[2])
class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_GET(self):
        m=re.match(r'^/control/(\d+)\.html$',self.path)
        if not m: self.send_response(404); self.end_headers(); return
        p=f'{A}/live/{m.group(1)}.html.gz'
        if not os.path.exists(p): self.send_response(404); self.end_headers(); return
        h=gzip.open(p,'rt',encoding='utf-8',errors='replace').read(); h=re.sub(r'(src|href|srcset)=(["\'])/(?!/)',r'\1=\2https://www.socialeurope.eu/',h).encode()
        self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(h))); self.end_headers(); self.wfile.write(h)
HTTPServer(('127.0.0.1',PORT),H).serve_forever()
