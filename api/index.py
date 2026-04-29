"""
SV-31869 reproducer — Vercel serverless function version.

Routes (giống bản local test_app.py):
  GET  /         search form, posts to /results
  POST /results  tracking results page (200)
  GET  /results  502 Bad Gateway — POST-only
  GET  /detail   detail page with in-page Back button
"""

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse


FORM_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Track Consignment</title>
<style>
  body { font-family: sans-serif; margin: 40px; }
  h1 { color: #d35400; }
  .panel { border: 1px solid #ccc; padding: 16px; max-width: 480px; }
  input[type=text] { width: 240px; padding: 6px; }
  button { padding: 6px 18px; }
</style>
</head>
<body>
  <h1>Track Consignment</h1>
  <div class="panel">
    <form method="POST" action="/results">
      <label>Consignment number:
        <input type="text" name="con" value="FJP001034947" required>
      </label>
      <input type="hidden" name="conID" value="1389330640">
      <input type="hidden" name="CITCon" value="True">
      <p><button type="submit">Track</button></p>
    </form>
    <p style="color:#888; font-size: 12px;">
      Reproducer for SV-31869. Submitting POSTs to /results.
    </p>
  </div>
</body>
</html>
"""


def results_page(con: str, conid: str) -> str:
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Track Results</title>
<style>
  body {{ font-family: sans-serif; margin: 40px; }}
  h1 {{ color: #d35400; }}
  table {{ border-collapse: collapse; max-width: 720px; }}
  th {{ background: #d35400; color: white; padding: 6px 12px; text-align: left; }}
  td {{ border: 1px solid #ccc; padding: 6px 12px; }}
  .actions {{ margin-top: 16px; }}
  a.btn, button.btn {{
    display: inline-block; padding: 6px 18px; border: 1px solid #888;
    background: #eee; text-decoration: none; color: black; cursor: pointer;
    font: inherit;
  }}
</style>
</head>
<body>
  <h1>Consignment Status History</h1>
  <p><b>Consignment No:</b> {con} &nbsp; <b>conID:</b> {conid}</p>
  <table>
    <tr><th>Status</th><th>Date</th><th>Time</th><th>Depot</th></tr>
    <tr><td>Your shipment data is lodged</td><td>19/03/2025</td><td>15:35</td><td>Sydney - Enfield</td></tr>
    <tr><td>We're processing your shipment</td><td>20/03/2025</td><td>06:42</td><td>Gold Coast</td></tr>
    <tr><td>Your shipment's with a driver</td><td>20/03/2025</td><td>09:51</td><td>Gold Coast</td></tr>
    <tr><td>We've delivered your shipment</td><td>20/03/2025</td><td>12:01</td><td>Gold Coast</td></tr>
  </table>
  <div class="actions">
    <a class="btn" href="/detail?con={con}&conID={conid}">View POD Image</a>
  </div>
  <p style="color:#888; font-size: 12px; margin-top: 32px;">
    This page was rendered from a POST. Reload or back-navigate from /detail
    will trigger a re-fetch; if the re-fetch loses POST it hits 502.
  </p>
</body>
</html>
"""


def detail_page(con: str, conid: str) -> str:
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Track Results</title>
<style>
  body {{ font-family: sans-serif; margin: 40px; }}
  h1 {{ color: #d35400; }}
  .card {{ border: 1px solid #ccc; max-width: 640px; padding: 16px; }}
  .footer {{ background: #ccc; padding: 8px; margin-top: 16px; text-align: right; }}
  button.btn {{
    display: inline-block; padding: 6px 18px; border: 1px solid #888;
    background: #eee; cursor: pointer; font: inherit;
  }}
</style>
</head>
<body>
  <h1>Proof of Delivery Details</h1>
  <div class="card">
    <p><b>Consignment No:</b> {con} &nbsp; <b>conID:</b> {conid}</p>
    <p><b>Items Received:</b> 1</p>
    <p><b>Date and Time:</b> 20/03/2025 12:01</p>
    <p><b>Signed By:</b> Ludovic</p>
    <p><i>Received in good order and condition.</i></p>
    <div class="footer">
      <button class="btn" onclick="history.back()">Back</button>
    </div>
  </div>
  <p style="color:#888; font-size: 12px; margin-top: 32px;">
    Click "Back" (or use the browser back button). In safeview this should
    end on chrome-error://chromewebdata/ if the bug is reproduced.
  </p>
</body>
</html>
"""


ERROR_BODY = """\
<!DOCTYPE html>
<html><head><title>Bad Gateway</title></head>
<body>
<h1>Bad Gateway (502)</h1>
<p>This URL is POST-only. SV-31869 reproducer marker.</p>
</body></html>
"""


class handler(BaseHTTPRequestHandler):
    server_version = "SV31869Repro/1.0"

    def _send(self, status: int, body: str,
              ctype: str = "text/html; charset=utf-8") -> None:
        body_bytes = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(body_bytes)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/" or path == "":
            self._send(200, FORM_PAGE)
            return


        if path == "/detail":
            con = (query.get("con") or ["?"])[0]
            conid = (query.get("conID") or ["?"])[0]
            self._send(200, detail_page(con, conid))
            return

        self._send(404, "<h1>404</h1>")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length > 0 else b""
        form = parse_qs(raw.decode("utf-8", errors="replace"))

        if path == "/results":
            con = (form.get("con") or ["?"])[0]
            conid = (form.get("conID") or ["?"])[0]
            if not con or con == "?":
                self._send(502, ERROR_BODY)
                return
            self._send(200, results_page(con, conid))
            return

        self._send(404, "<h1>404</h1>")
