# Relay for Render (its IPs are not refused where Cloudflare's and Oracle's are):
#   GET /tb?code=<share code> -> TeraBox's /api/shorturlinfo answer;  GET /status?mid=<MID>&ref=<txn ref> -> Paytm's JSON.
# Paytm status relay: GET /status?mid=<MID>&ref=<txn ref> -> Paytm's JSON, fetched from this server's IP.
# (Paytm refuses data-center IPs of Cloudflare and Oracle; Render's works.)
import base64, json, os, random, re, urllib.error, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

HOSTS = ["www.1024terabox.com", "terafileshare.com"]
TOKENS = ["A942EF515E02A72F9A53362C318515FB810BE376D1C39F93B84F5784D2DF89C5B130EB9C59EA59E162FB0545D2470D6A8C065623E368A3A71B78611DEAE90600",
          "7AFA4BC6C89B13EA9E3E1965FF71A9F45E5AF0803A7EC411EA3B1718C0E3B4F05916B3F0BC2BFD9AB09473D479FC27F6E5EBD4807273F2027161C7F5120DF64404EEDCA9F692B58F862B5504A5B5B8532EA13B29DC2B07A40DE67B5831E10B14"]
DEAD = {105, -3, -9, 2, 115, -70, 9019, 400210}  # dead link: asking again will not help
b64 = lambda n: base64.urlsafe_b64encode(os.urandom(n)).decode().rstrip("=")

def tb_resolve(code):
    last = {"errno": -1}
    for i in range(5):
        ck = "; ".join(["PANWEB=1", "csrfToken=" + b64(24), "browserid=" + b64(24) + "=" + os.urandom(4).hex(), "TSID=TS" + str(random.randint(10**12, 9 * 10**12)) + os.urandom(6).hex(), "ndut_fmt=" + os.urandom(32).hex()])
        u = f"https://{random.choice(HOSTS)}/api/shorturlinfo?app_id=250528&web=1&channel=dubox&clienttype=0&jsToken={TOKENS[i % 2]}&dp-logid=87207{random.randint(10**12, 9 * 10**12)}&shorturl={urllib.parse.quote(code)}&root=1"
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "application/json, text/plain, */*", "Cookie": ck}), timeout=6))
        except Exception as e:
            d = {"errno": type(e).__name__}
        if d.get("errno") == 0 and d.get("list"):
            return {**d, "jt": TOKENS[i % 2], "tries": i + 1}
        last = d
        if d.get("errno") in DEAD and d.get("errno") != 400210:
            break
    return last

class H(BaseHTTPRequestHandler):
    def reply(self, code, body):
        self.send_response(code); self.send_header("content-type", "application/json"); self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else json.dumps(body).encode())

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        if u.path == "/tb":
            code = q.get("code", "")
            if not re.fullmatch(r"[\w-]{6,40}", code):
                return self.reply(400, {"error": "bad code"})
            return self.reply(200, tb_resolve(code))
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
