# -*- coding: utf-8 -*-
"""测试用静态服务器：和 `python -m http.server` 一样，但强制不缓存。

为什么需要：浏览器会把 content/kendudian.js、popup/popup.js 缓存住（304），
测试页拿到的还是旧代码 → 明明改好了却"没生效"，浪费大量排查时间。
用法：  python test/nocache_server.py 8123 .
"""
import sys, functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # 静音，测试输出更干净


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
    root = sys.argv[2] if len(sys.argv) > 2 else "."
    handler = functools.partial(NoCacheHandler, directory=root)
    print("serving %s on http://127.0.0.1:%d (no-store)" % (root, port), file=sys.stderr)
    ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
