#!/usr/bin/env python3
import http.server, json, os, sys, ssl, base64, traceback, urllib.request, urllib.error

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

def gh_request(method, url, token, data=None):
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    headers = {'Authorization': f'token {token}', 'User-Agent': 'Hermes', 'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers=headers, method=method)
    return urllib.request.urlopen(req, timeout=15, context=ctx)

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()
    def do_GET(self):
        if self.path in ('/', '/index.html'):
            try:
                with open(INDEX, 'rb') as f: data = f.read()
                self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self._cors(); self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode())
        elif self.path == '/health':
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self._cors(); self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        elif self.path.startswith('/api/conversations'):
            try:
                gh_token = os.environ.get('GITHUB_TOKEN', '')
                gh_repo = os.environ.get('GITHUB_REPO', 'khosrozadeganjavad-ai/hermes')
                if not gh_token:
                    self.send_response(200); self.send_header('Content-Type', 'application/json'); self._cors(); self.end_headers()
                    self.wfile.write(b'{}'); return
                resp = gh_request('GET', f'https://api.github.com/repos/{gh_repo}/contents/conversations', gh_token)
                items = json.loads(resp.read())
                result = {}
                for item in items:
                    if item['name'].endswith('.json'):
                        raw = urllib.request.urlopen(item['download_url'], timeout=10, context=ssl.create_default_context())
                        result[item['name'][:-5]] = json.loads(raw.read())
                self.send_response(200); self.send_header('Content-Type', 'application/json'); self._cors(); self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            except Exception as e:
                self.send_response(200); self.send_header('Content-Type', 'application/json'); self._cors(); self.end_headers()
                self.wfile.write(b'{}')
        else:
            self.send_error(404)
    def do_POST(self):
        if self.path == '/api/conversations':
            try:
                gh_token = os.environ.get('GITHUB_TOKEN', '')
                gh_repo = os.environ.get('GITHUB_REPO', 'khosrozadeganjavad-ai/hermes')
                length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(length))
                conv_id = body.get('id', 'default')
                conv_data = json.dumps(body.get('data', {}), ensure_ascii=False)
                # Check if file exists
                try:
                    existing = json.loads(gh_request('GET', f'https://api.github.com/repos/{gh_repo}/contents/conversations/{conv_id}.json', gh_token).read())
                    sha = existing.get('sha', '')
                except: sha = ''
                payload = {'message': f'Update {conv_id}', 'content': base64.b64encode(conv_data.encode()).decode(), 'branch': 'main'}
                if sha: payload['sha'] = sha
                gh_request('PUT', f'https://api.github.com/repos/{gh_repo}/contents/conversations/{conv_id}.json', gh_token, payload)
                self.send_response(200); self.send_header('Content-Type', 'application/json'); self._cors(); self.end_headers()
                self.wfile.write(b'{"ok":true}')
            except Exception as e:
                self.send_response(500); self.send_header('Content-Type', 'application/json'); self._cors(); self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return
        if self.path != '/v1/chat/completions':
            self.send_error(404); return
        try:
            c = load_api_config()
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            model_map = {
                'hermes': 'nousresearch/hermes-3-llama-3.1-405b',
                'nemotron ultra': 'nvidia/nemotron-3-ultra-550b-a55b:free',
                'nemotron super': 'nvidia/nemotron-3-super-120b-a12b:free',
                'gemma': 'google/gemma-4-31b-it:free',
                'gemma mini': 'google/gemma-4-26b-a4b-it:free',
                'gpt-oss': 'openai/gpt-oss-20b:free',
                'ling': 'inclusionai/ling-3.0-flash:free',
                'cohere': 'cohere/north-mini-code:free',
                'laguna': 'poolside/laguna-s-2.1:free',
                'auto': 'openrouter/free'
            }
            m = data.get('model', 'hermes').lower()
            data['model'] = model_map.get(m, m)
            msgs = data.get('messages', [])
            if not msgs or msgs[0].get('role') != 'system':
                name_map = {
                    'nousresearch/hermes-3-llama-3.1-405b': 'Hermes',
                    'nvidia/nemotron-3-ultra-550b-a55b:free': 'Nemotron Ultra',
                    'nvidia/nemotron-3-super-120b-a12b:free': 'Nemotron Super',
                    'google/gemma-4-31b-it:free': 'Gemma',
                    'google/gemma-4-26b-a4b-it:free': 'Gemma Mini',
                    'openai/gpt-oss-20b:free': 'GPT-OSS',
                    'inclusionai/ling-3.0-flash:free': 'Ling',
                    'cohere/north-mini-code:free': 'Cohere',
                    'poolside/laguna-s-2.1:free': 'Laguna',
                    'openrouter/free': 'AI'
                }
                ai_name = name_map.get(data.get('model', 'hermes'), 'AI')
                msgs.insert(0, {"role": "system", "content": f"You are {ai_name}, a helpful AI assistant. Speak in the same language as the user. Be concise."})
            data['messages'] = msgs
            req = urllib.request.Request(
                f"{c['base_url']}/chat/completions",
                data=json.dumps(data).encode(),
                headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {c['api_key']}"},
                method='POST'
            )
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            resp = urllib.request.urlopen(req, timeout=120, context=ctx)
            self.send_response(200); self.send_header('Access-Control-Allow-Origin', '*'); self.send_header('Content-Type', 'text/event-stream'); self.end_headers()
            self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code); self.send_header('Access-Control-Allow-Origin', '*'); self.send_header('Content-Type', 'application/json'); self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            traceback.print_exc()
            self.send_response(500); self.send_header('Access-Control-Allow-Origin', '*'); self.send_header('Content-Type', 'application/json'); self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

sys.stderr.write(f"[BOOT] Starting on 0.0.0.0:{PORT}\n"); sys.stderr.flush()
http.server.HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
