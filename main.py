# Render test: GET /?mid=<MID>&ref=<txn ref>  ->  what Paytm's status API answers to THIS server's IP (and the IP itself)
import json, os, urllib.parse, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=15)
        return r.status, r.read(3000).decode("utf8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(80).decode("utf8", "replace")
    except Exception as e:
        return 0, str(e)

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        mid, ref = q.get("mid", [""])[0], q.get("ref", [""])[0]
        out = {"my_ip": get("https://api.ipify.org")[1]}
        if mid and ref:
            j = urllib.parse.quote(json.dumps({"MID": mid, "ORDERID": ref}))
            code, body = get(f"https://secure.paytmpayments.com/order/status?JsonData={j}")
            out.update(paytm_http=code, paytm_status=(json.loads(body).get("STATUS") if code == 200 and body.startswith("{") else body[:60]))
        self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps(out).encode())

HTTPServer(("0.0.0.0", int(os.getenv("PORT", "10000"))), H).serve_forever()
