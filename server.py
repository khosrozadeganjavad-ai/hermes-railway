#!/usr/bin/env python3
import http.server, json, os, sys, ssl, traceback, urllib.request, urllib.error

PORT = int(os.environ.get('PORT', '8080'))
DIR = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(DIR, 'index.html')

sys.stderr.write(f"[BOOT] Python {sys.version}\n")
sys.stderr.write(f"[BOOT] PORT={PORT} DIR={DIR}\n")
sys.stderr.write(f"[BOOT] index.html exists: {os.path.exists(INDEX)}\n")
sys.stderr.flush()

def load_api_config():
    return {
        'api_key': os.environ.get('OPENAI_API_KEY', ''),
        'base_url': os.environ.get('OPENAI_BASE_URL', 'https://openrouter.ai/api/v1').rstrip('/')
    }

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200); self.send_header('Content-Type','application/json'); self._cors(); self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        elif self.path in ('/','/index.html'):
            try:
                with open(INDEX,'rb') as f: data=f.read()
                self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self._cors(); self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode())
        else: self.send_error(404)
    def do_POST(self):
        if self.path != '/v1/chat/completions': self.send_error(404); return
        try:
            c=load_api_config(); length=int(self.headers.get('Content-Length',0)); body=self.rfile.read(length); data=json.loads(body)
            model_map = {
                'hermes': 'nousresearch/hermes-3-llama-3.1-405b',
                'gemma': 'google/gemma-4-31b-it:free',
                'nemotron': 'nvidia/nemotron-3-ultra-550b-a55b:free',
                'gpt-oss': 'openai/gpt-oss-20b:free',
                'openrouter': 'openrouter/free'
            }
            m = data.get('model','hermes').lower()
            data['model'] = model_map.get(m, m)
            msgs=data.get('messages',[])
            if not msgs or msgs[0].get('role')!='system': msgs.insert(0,{"role":"system","content":"Tu Hermes hasti, dastiyar-e AI Nous Research. Be farsi sohbat kon. Mukhtasar bash."})
            data['messages']=msgs
            req=urllib.request.Request(f"{c['base_url']}/chat/completions",data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Authorization':f"Bearer {c['api_key']}"},method='POST')
            ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
            resp=urllib.request.urlopen(req,timeout=120,context=ctx)
            self.send_response(200); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Content-Type','text/event-stream'); self.end_headers()
            self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Content-Type','application/json'); self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            traceback.print_exc()
            self.send_response(500); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Content-Type','application/json'); self.end_headers()
            self.wfile.write(json.dumps({'error':str(e)}).encode())

sys.stderr.write(f"[BOOT] Starting on 0.0.0.0:{PORT}\n"); sys.stderr.flush()
http.server.HTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
