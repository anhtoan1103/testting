const RESULTS_GET_ERROR_BODY = `<!doctype html>
<html><body style="font-family:sans-serif;margin:2em">
  <h1 style="color:#c0392b">502 Bad Gateway</h1>
  <p>This endpoint is POST-only. Direct GET requests are refused.</p>
  <p>If you reached this page via the browser back button on a Safeview tab,
     the surrogate browser issued a GET to a POST-only URL - SV-31869.</p>
</body></html>`;

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
  <p style="margin-top:1em"><a href="/sigimg?con=${encodeURIComponent(con)}" id="view-pod">View POD Image</a></p>
  <hr><p><small>Rendered via POST. Back-nav as GET trips the error path.</small></p>
</body></html>`;

function noCache(res) {
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');
  res.setHeader('Pragma', 'no-cache');
  res.setHeader('Expires', '-1');
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
}

module.exports = (req, res) => {
  noCache(res);
  if (req.method === 'GET') {
    res.statusCode = 502;
    return res.end(RESULTS_GET_ERROR_BODY);
  }
  if (req.method === 'POST') {
    // Vercel auto-parses application/x-www-form-urlencoded into req.body
    const con = (req.body && req.body.con) || 'FJP001034947';
    res.statusCode = 200;
    return res.end(resultsPage(con));
  }
  res.statusCode = 405;
  res.end('<h1>405 Method Not Allowed</h1>');
};
