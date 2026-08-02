# Hermes Mini App — Deployment Guide

## Overview
Telegram Mini App for Hermes AI assistant. Connects to an OpenAI-compatible API.

## Quick Deploy (Railway)

### Prerequisites
- GitHub account
- Railway account (https://railway.com)
- API endpoint (OpenAI-compatible)

### Steps
1. **Create GitHub repo** (public or connect Railway GitHub App):
   ```
   Repo: hermes-miniapp
   Branch: main
   ```

2. **Files needed** (all in repo root):
   - `server.py` — Python HTTP server + API proxy
   - `index.html` — Frontend (Telegram Mini App UI)
   - `Dockerfile` — Docker build config
   - `Procfile` — Process definition for Railway

3. **Deploy to Railway**:
   - New Project → Deploy from GitHub Repo
   - Select the repo
   - Railway auto-detects Dockerfile

4. **Set Environment Variables**:
   ```
   OPENAI_API_KEY=your-api-key
   OPENAI_BASE_URL=https://your-api-endpoint/v1
   ```
   (Do NOT set PORT — Railway handles this automatically)

5. **Done!** App will be at `https://your-service.up.railway.app`

## File Contents

### server.py
```python
#!/usr/bin/env python3
"""Hermes Mini App Server"""
import http.server, json, os, ssl, sys, traceback, urllib.request, urllib.error

PORT = int(os.environ.get('PORT', '8080'))
DIR = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(DIR, 'index.html')

def load_api_config():
    return {
        'api_key': os.environ.get('OPENAI_API_KEY', ''),
        'base_url': os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    }

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass
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
            if data.get('model','').lower()=='hermes': data['model']='Hermes'
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

http.server.HTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
```

### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY server.py .
COPY index.html .
EXPOSE 8080
CMD ["python3", "server.py"]
```

### Procfile
```
web: python3 server.py
```

## Railway CLI Deploy (Alternative)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy from current directory
railway up --service miniapp
```

## Current Config
- **Railway URL**: https://miniapp-production-8761.up.railway.app
- **API Backend**: https://9router-production-f48a.up.railway.app/v1
- **Railway Project**: vigilant-spontaneity (production)
- **Service**: miniapp

## Notes
- Do NOT set PORT env var — Railway provides it automatically
- Server reads PORT from environment
- Health check endpoint: /health
- Frontend: index.html (served at root /)
- API proxy: POST /v1/chat/completions
