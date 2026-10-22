# 开发测试用静态服务器：允许跨域（真实网页注入 content script 时加载词典/模型/wasm）
# python cors_server.py [port]  默认 8765
import http.server, socketserver, os, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 项目根（脚本在 tools/ 下）
MIME = {
    '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8', '.png': 'image/png',
    '.wasm': 'application/wasm', '.mjs': 'text/javascript', '.onnx': 'application/octet-stream',
    '.txt': 'text/plain; charset=utf-8', '.css': 'text/css; charset=utf-8',
    '.md': 'text/plain; charset=utf-8', '.zip': 'application/zip',
}

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()
    def do_OPTIONS(self):
        self.send_response(204); self.end_headers()
    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return MIME.get(ext, 'application/octet-stream')

with socketserver.ThreadingTCPServer(('127.0.0.1', PORT), Handler) as httpd:
    print(f'CORS server on http://127.0.0.1:{PORT} root={ROOT}')
    httpd.serve_forever()
