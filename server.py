import time
import re
import http.server, socketserver, urllib.request, urllib.parse, json, os, sys, mimetypes

DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 8787
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36'
API = 'https://api.zhihu.com/podcasts/morning/morning_call/-1'
REF = 'https://www.zhihu.com/podcast/morning-call/'

COOKIE_FILE = os.path.join(DIR, 'cookie.txt')

def read_cookie():
    try:
        return open(COOKIE_FILE, encoding='utf-8', errors='ignore').read().strip()
    except Exception:
        return ''

def fetch(url, extra=None):
    h = {'User-Agent': UA, 'Referer': REF, 'Accept': '*/*'}
    ck = read_cookie()
    if ck:
        h['Cookie'] = ck
    if extra:
        h.update(extra)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.headers.get('Content-Type', 'application/octet-stream'), r.read()

def rewrite_m3u8(text, base):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith('#'):
            if 'URI="' in s:
                pre, rest = s.split('URI="', 1)
                uri, post = rest.split('"', 1)
                absu = urllib.parse.urljoin(base, uri)
                s = pre + 'URI="/seg?u=' + urllib.parse.quote(absu, safe='') + '"' + post
            out.append(s)
        else:
            absu = urllib.parse.urljoin(base, s)
            out.append('/seg?u=' + urllib.parse.quote(absu, safe=''))
    return ('\n'.join(out) + '\n').encode('utf-8')


FALLBACK_IDS = ['2798442']
MEDIA_CACHE = os.path.join(DIR, 'media_cache.json')

def find_media():
    out = {'tried': []}
    try:
        st, ct, body = fetch(API)
        j = json.loads(body.decode('utf-8'))
        pu = (j.get('data', {}).get('play_url') or {}).get('primary')
    except Exception as e:
        pu = None
        out['api_error'] = str(e)
    cands = []
    if pu:
        cands.append(pu)
    for i in FALLBACK_IDS:
        cands.append('https://api.zhihu.com/podcasts/morning/player/%s.m3u8' % i)
    for u in cands:
        try:
            st, ct, b = fetch(u)
            if b.startswith(b'#EXTM3U'):
                dur = 0
                try:
                    txt = b.decode('utf-8', 'replace')
                    for x in re.findall(r'#EXTINF:([0-9.]+)', txt):
                        dur += float(x)
                except Exception:
                    pass
                out['url'] = u
                out['status'] = st
                out['duration'] = int(dur)
                out['segments'] = b.count(b'#EXTINF')
                try:
                    open(MEDIA_CACHE, 'w', encoding='utf-8').write(json.dumps({'url': u, 'at': int(time.time())}))
                except Exception:
                    pass
                return out
            out['tried'].append([u, st, len(b)])
        except Exception as e:
            out['tried'].append([u, getattr(e, 'code', 0), str(e)[:60]])
    return out

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DIR, **k)

    def log_message(self, fmt, *args):
        sys.stdout.write('  %s\n' % (fmt % args))

    def out(self, code, data, ctype):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:
            pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == '/api/ep':
            try:
                st, ct, body = fetch(API)
                self.out(200, body, 'application/json; charset=utf-8')
            except Exception as e:
                self.out(502, json.dumps({'error': str(e)}).encode(), 'application/json')
            return
        if u.path == '/api/media':
            self.out(200, json.dumps(find_media(), ensure_ascii=False).encode(), 'application/json')
            return
        if u.path == '/api/cookie':
            v = (q.get('v') or [''])[0]
            try:
                open(COOKIE_FILE, 'w', encoding='utf-8').write(v)
                self.out(200, json.dumps({'ok': True, 'len': len(v)}).encode(), 'application/json')
            except Exception as e:
                self.out(500, json.dumps({'error': str(e)}).encode(), 'application/json')
            return
        if u.path == '/api/diag':
            out = {'cookie': len(read_cookie())}
            try:
                st, ct, body = fetch(API)
                j = json.loads(body.decode('utf-8'))
                out['api'] = st
                out['title'] = j.get('data', {}).get('title')
                pu = (j.get('data', {}).get('play_url') or {}).get('primary')
                out['play'] = pu
                try:
                    st2, ct2, b2 = fetch(pu)
                    out['media_status'] = st2
                    out['media_bytes'] = len(b2)
                    out['media_head'] = b2[:60].decode('utf-8', 'replace')
                except Exception as e2:
                    out['media_status'] = getattr(e2, 'code', 0)
                    try:
                        out['media_body'] = e2.read()[:120].decode('utf-8', 'replace')
                    except Exception:
                        out['media_body'] = str(e2)[:120]
            except Exception as e:
                out['error'] = str(e)
            self.out(200, json.dumps(out, ensure_ascii=False).encode(), 'application/json')
            return
        if u.path == '/api/probe':
            target = (q.get('u') or [''])[0]
            if not target:
                self.out(400, b'{"error":"missing u"}', 'application/json')
                return
            try:
                st, ct, body = fetch(target)
                head = body[:200].decode('utf-8', 'replace')
                self.out(200, json.dumps({'status': st, 'ctype': ct, 'bytes': len(body), 'head': head}).encode(), 'application/json')
            except Exception as e:
                msg = str(e)
                code = getattr(e, 'code', 0)
                self.out(200, json.dumps({'status': code, 'error': msg}).encode(), 'application/json')
            return
        if u.path == '/hls':
            target = (q.get('u') or [''])[0]
            if not target:
                self.out(400, b'{"error":"missing u"}', 'application/json')
                return
            try:
                st, ct, body = fetch(target)
            except Exception as e:
                self.out(502, json.dumps({'error': str(e)}).encode(), 'application/json')
                return
            if b'#EXTM3U' in body[:200]:
                self.out(200, rewrite_m3u8(body.decode('utf-8', 'replace'), target), 'application/vnd.apple.mpegurl')
            else:
                self.out(200, body, ct)
            return
        if u.path == '/seg':
            target = (q.get('u') or [''])[0]
            if not target:
                self.out(400, b'{"error":"missing u"}', 'application/json')
                return
            try:
                st, ct, body = fetch(target)
                self.out(200, body, ct)
            except Exception as e:
                self.out(502, json.dumps({'error': str(e)}).encode(), 'application/json')
            return
        if u.path in ('/', '/index.html'):
            fp = os.path.join(DIR, 'index.html')
            try:
                data = open(fp, 'rb').read()
                self.out(200, data, 'text/html; charset=utf-8')
            except Exception as e:
                self.out(500, str(e).encode(), 'text/plain; charset=utf-8')
            return
        return super().do_GET()
class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == '__main__':
    os.chdir(DIR)
    try:
        srv = S(('127.0.0.1', PORT), H)
    except OSError as e:
        print('port %d is busy: %s' % (PORT, e))
        print('maybe another copy is already running: http://127.0.0.1:%d/' % PORT)
        raise SystemExit(1)
    print('MORNING CALL  http://127.0.0.1:%d/' % PORT)
    print('close this window or press Ctrl+C to stop')
    if os.environ.get('MORNING_NO_BROWSER', '') != '1':
        try:
            import threading, webbrowser
            threading.Timer(1.2, lambda: webbrowser.open('http://127.0.0.1:%d/' % PORT)).start()
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass