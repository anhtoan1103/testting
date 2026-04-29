#!/usr/bin/env python3
"""
SV-31869 Reproducer for back-navigation to a POST result page.

What this reproduces
--------------------
Chromium history-back to a POST entry uses LOAD_ONLY_FROM_CACHE
(see content/browser/renderer_host/navigation_request.cc, the
HISTORY_DIFFERENT_DOCUMENT branch of UpdateLoadFlagsWithCacheFlags).
If the POST response was uncacheable (Cache-Control: no-store / no-cache),
that fetch returns ERR_CACHE_MISS and Chromium commits the failed
navigation as chrome-error://chromewebdata/ (render_frame_impl.cc).

In native Chrome this is masked by bfcache: the rendered POST page is
restored from bfcache and the cache-only flag is never exercised.

In the safeview surrogate Chromium bfcache is effectively disabled:
  - safeview/renderer/safeview_render_frame_observer.cc:1205 marks any
    script injection as BackForwardCacheAware::kPossiblyDisallow,
  - the WebSocket connection used by every TC page disqualifies bfcache.
With no bfcache, history-back hits LOAD_ONLY_FROM_CACHE -> ERR_CACHE_MISS
-> chrome-error://chromewebdata/, exactly as the customer's WebSocket
trace shows ([history_jump,-1] then a set_doctype to chrome-error://...).

To repro the bug locally the only thing the test page must do is:
  (1) accept a POST and return content,
  (2) make that response uncacheable (Cache-Control: no-store).
That's it. The forward GET page is just a hop so the back-button has
something to navigate from.

Ji Feng's earlier test apps did not reproduce because their POST response
was cacheable, so the cache-only fetch succeeded.

Routes
------
  GET  /             search form, posts to /results
  POST /results      tracking results page (Cache-Control: no-store).
                     Has a link to /detail and an in-page "Back" button.
  GET  /results      502 Bad Gateway, useful only as a secondary signal:
                     if you ever DO see this 502 body in the surrogate,
                     it means the back nav hit the network (not the
                     cache-miss path); that would be a different bug.
  GET  /detail       detail page with an in-page "Back" button
                     (mimics the SigImg.asp "Back" button)

Reproduction
------------
  1. Open  /                                in safeview
  2. Submit the form     (POST /results)    -> results page renders
  3. Click "View Detail" (GET  /detail)     -> detail page renders
  4. Click "Back" (in-page, OR browser back)

  Expected in safeview (with bfcache off): chrome-error://chromewebdata/
    page rendered for /results; the WebSocket frames show
    [history_jump,-1] then a set_doctype to chrome-error://chromewebdata/.

  Expected in native Chrome: bfcache restores the page; you do NOT see a
    POST on the wire, because no fetch happens.

  If you want to also see native fall back to ERR_CACHE_MISS, disable
    bfcache: chrome --disable-features=BackForwardCache.

Run
---
  python3 test_app.py            # listens on 0.0.0.0:8080
  python3 test_app.py 9000       # listens on 0.0.0.0:9000

Then put it behind whatever public hostname you usually use for repros
(e.g. corgi.webredirect.org/menlo/sv31869-bug) and access it through the
isolated browser.
"""

import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
      <!-- Mimics the in-page Back button on tntexpress SigImg.asp.
           Clicking it triggers history.back() which is what fails. -->
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


# Body served on GET to /results. Kept SHORT so the surrogate's net stack
# is more likely to escalate to a chrome-error page rather than render the
# 502 body inline. Also includes a marker string the user can grep for in
# their Squid/network logs.
ERROR_BODY = """\
<!DOCTYPE html>
<html><head><title>Bad Gateway</title></head>
<body>
<h1>Bad Gateway (502)</h1>
<p>This URL is POST-only. SV-31869 reproducer marker.</p>
</body></html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "SV31869Repro/1.0"

    def _send(self, status: int, body: str, ctype: str = "text/html; charset=utf-8",
              extra_headers: dict | None = None) -> None:
        body_bytes = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body_bytes)

    # --- GET ---
    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)

        if path == "/" or path == "":
            self._send(200, FORM_PAGE)
            return

        if path == "/results":
            # If you ever see this body rendered in the surrogate, it means
            # the back nav reached the network (not the cache-miss path).
            # Under SV-31869 the surrogate should never reach this branch:
            # LOAD_ONLY_FROM_CACHE on history-back fails before the network
            # is consulted, and the user lands on chrome-error directly.
            self.log_message("GET /results -> 502 (POST-only)")
            self._send(502, ERROR_BODY)
            return

        if path == "/detail":
            con = (query.get("con") or ["?"])[0]
            conid = (query.get("conID") or ["?"])[0]
            self._send(200, detail_page(con, conid))
            return

        self._send(404, "<h1>404</h1>")

    # --- POST ---
    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length > 0 else b""
        form = parse_qs(raw.decode("utf-8", errors="replace"))

        if path == "/results":
            con = (form.get("con") or ["?"])[0]
            conid = (form.get("conID") or ["?"])[0]
            if not con or con == "?":
                # Empty POST body -> still 502, so a back-nav that loses
                # the body shows the bug even if the method survived.
                self.log_message("POST /results with empty body -> 502")
                self._send(502, ERROR_BODY)
                return
            self.log_message("POST /results con=%s -> 200", con)
            self._send(200, results_page(con, conid))
            return

        self._send(404, "<h1>404</h1>")

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        sys.stderr.write("[%s] %s\n" % (
            time.strftime("%H:%M:%S"), fmt % args))


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"SV-31869 reproducer listening on http://0.0.0.0:{port}/")
    print("  GET  /         - search form")
    print("  POST /results  - results page (200)")
    print("  GET  /results  - 502 (POST-only)")
    print("  GET  /detail   - detail page with in-page Back button")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
