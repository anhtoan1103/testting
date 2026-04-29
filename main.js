#!/usr/bin/env node
/*
 * SV-31869 reproducer (Node.js port of test_app.py).
 *
 * Models the TNT Express failure: back navigation from a GET-loaded detail
 * page to a POST result page fails inside Safeview because the surrogate
 * re-issues the navigation as GET (POST body lost across pair/repair).
 *
 * Pages:
 *   GET  /         - search form, POSTs to /results
 *   POST /results  - renders the "Consignment Status" page
 *   GET  /results  - returns 502 (mirrors TNT: POST-only result page)
 *   GET  /sigimg   - POD page with in-page Back button (history.back())
 *
 * Run:  node test_app.js [PORT]   # default 8080
 */

const http = require('http');
const { URL } = require('url');
const querystring = require('querystring');

const FORM_PAGE = `<!doctype html>
<html><head><title>Tracking - SV-31869 Repro</title></head>
<body style="font-family:sans-serif;margin:2em">
  <h2>Consignment Tracking (SV-31869 reproducer)</h2>
  <p>Enter any consignment number and click Track. The form submits via POST
     to <code>/results</code>.</p>
  <form method="POST" action="/results">
    <label>Consignment No: <input name="con" value="FJP001034947" size="30"></label>
    <button type="submit">Track</button>
  </form>
</body></html>
`;

const resultsPage = (con) => `<!doctype html>
<html><head><title>Track Results</title></head>
<body style="font-family:sans-serif;margin:2em">
  <h2 style="color:#d35400">Consignment Status History</h2>
  <p><b>Consignment No:</b> ${con}</p>
  <table border="1" cellpadding="6" cellspacing="0">
    <tr><th>Status</th><th>Date</th><th>Time</th><th>Depot</th></tr>
    <tr><td>Your shipment data is lodged</td><td>19/03/2025</td><td>15:35</td><td>Sydney - Enfield</td></tr>
    <tr><td>We're processing your shipment</td><td>19/03/2025</td><td>17:35</td><td>Sydney - Erskine Park</td></tr>
    <tr><td>Your shipment's with a driver</td><td>20/03/2025</td><td>09:51</td><td>Gold Coast</td></tr>
    <tr><td>We've delivered your shipment</td><td>20/03/2025</td><td>12:01</td><td>Gold Coast</td></tr>
  </table>
  <p style="margin-top:1em">
    <a href="/sigimg?con=${encodeURIComponent(con)}" id="view-pod">View POD Image</a>
  </p>
  <hr>
  <p><small>This page was rendered via POST. Reloading or back-navigating to it
     as GET will trigger the error path (see /results GET handler).</small></p>
</body></html>
`;

const RESULTS_GET_ERROR_BODY = `<!doctype html>
<html><body style="font-family:sans-serif;margin:2em">
  <h1 style="color:#c0392b">502 Bad Gateway</h1>
  <p>This endpoint is POST-only. Direct GET requests are refused.</p>
  <p>If you reached this page via the browser back button on a Safeview tab,
     the surrogate browser issued a GET to a POST-only URL - which is the
     exact symptom described in <b>SV-31869</b>.</p>
</body></html>
`;

const sigimgPage = (con) => `<!doctype html>
<html><head><title>Proof of Delivery</title></head>
<body style="font-family:sans-serif;margin:2em">
  <h2 style="color:#d35400">Proof of Delivery Details</h2>
  <p><b>Consignment No:</b> ${con}</p>
  <p>Signed by: Ludwic &nbsp; | &nbsp; Date: 20/03/2025 12:01</p>
  <p>Delivery Notation: We've delivered your shipment</p>
  <hr>
  <div style="margin-top:2em">
    <!-- In-page back button: identical mechanism to TNT's SigImg.asp -->
    <button id="in-page-back" onclick="history.back()">Back</button>
    <span style="margin-left:2em;color:#888">
       (or use the browser's back button - both fail the same way in safeview)
    </span>
  </div>
</body></html>
`;

function send(res, status, body, contentType = 'text/html; charset=utf-8') {
  const buf = Buffer.from(body, 'utf-8');
  res.writeHead(status, {
    'Content-Type': contentType,
    'Content-Length': buf.length,
    'Cache-Control': 'no-store, no-cache, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '-1',
  });
  res.end(buf);
}

const server = http.createServer((req, res) => {
  const parsed = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const path = parsed.pathname;

  // Quieter logs (mirror Python log_message)
  process.stderr.write(`${req.socket.remoteAddress} - ${req.method} - ${req.url}\n`);

  if (req.method === 'GET') {
    const con = parsed.searchParams.get('con') || 'FJP001034947';
    if (path === '/' || path === '/index.html') return send(res, 200, FORM_PAGE);
    if (path === '/results')                    return send(res, 502, RESULTS_GET_ERROR_BODY);
    if (path === '/sigimg')                     return send(res, 200, sigimgPage(con));
    return send(res, 404, '<h1>404 Not Found</h1>');
  }

  if (req.method === 'POST') {
    if (path !== '/results') return send(res, 405, '<h1>405 Method Not Allowed</h1>');
    let body = '';
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', () => {
      const form = querystring.parse(body);
      const con = (Array.isArray(form.con) ? form.con[0] : form.con) || 'FJP001034947';
      send(res, 200, resultsPage(con));
    });
    return;
  }

  send(res, 405, '<h1>405 Method Not Allowed</h1>');
});

const port = parseInt(process.argv[2] || '8080', 10);
server.listen(port, '0.0.0.0', () => {
  console.log(`SV-31869 reproducer listening on http://0.0.0.0:${port}/`);
  console.log('  GET  /        - search form');
  console.log('  POST /results - renders status page (good)');
  console.log('  GET  /results - returns 502 (this is what trips safeview)');
  console.log('  GET  /sigimg  - POD detail page with in-page Back button');
});

process.on('SIGINT', () => {
  console.log('\nbye');
  process.exit(0);
});
