# Paytm status relay for Render: GET /status?mid=<MID>&ref=<txn ref> -> Paytm's JSON, fetched from this server's IP.
# (Paytm refuses data-center IPs of Cloudflare and Oracle; Render's works.)
import json, os, re, urllib.error, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class H(BaseHTTPRequestHandler):
    def reply(self, code, body):
        self.send_response(code); self.send_header("content-type", "application/json"); self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else json.dumps(body).encode())

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        if u.path != "/status":
            return self.reply(200, {"ok": True})  # health check / keep-alive ping
        mid, ref = q.get("mid", ""), q.get("ref", "")
        if not re.fullmatch(r"[A-Za-z0-9]{10,30}", mid) or not re.fullmatch(r"\d{6,30}", ref):
            return self.reply(400, {"error": "bad mid/ref"})
        j = urllib.parse.quote(json.dumps({"MID": mid, "ORDERID": ref}))
        try:
            r = urllib.request.urlopen(urllib.request.Request(f"https://secure.paytmpayments.com/order/status?JsonData={j}", headers={"User-Agent": UA}), timeout=15)
            self.reply(200, r.read())
        except urllib.error.HTTPError as e:
            self.reply(502, {"error": "paytm", "http": e.code})
        except Exception as e:
            self.reply(502, {"error": str(e)[:100]})

    def log_message(self, *a):
        pass

ThreadingHTTPServer(("0.0.0.0", int(os.getenv("PORT", "10000"))), H).serve_forever()
