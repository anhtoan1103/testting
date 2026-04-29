const resultsPage = (con, method) => `<!doctype html>
<html><head><title>Track Results</title></head>
<body style="font-family:sans-serif;margin:2em">
  <h2 style="color:#d35400">Consignment Status History</h2>
  <p><b>Consignment No:</b> ${con}</p>
  <p style="background:#fffbe6;border:1px solid #f0c36d;padding:6px 10px;display:inline-block">
    Rendered via <b>${method}</b>
    ${method === 'GET' ? ' &nbsp;←&nbsp; <span style="color:#c0392b">SV-31869: back-nav re-issued as GET instead of POST</span>' : ''}
  </p>
  <table border="1" cellpadding="6" cellspacing="0">
    <tr><th>Status</th><th>Date</th><th>Time</th><th>Depot</th></tr>
    <tr><td>Your shipment data is lodged</td><td>19/03/2025</td><td>15:35</td><td>Sydney - Enfield</td></tr>
    <tr><td>We're processing your shipment</td><td>19/03/2025</td><td>17:35</td><td>Sydney - Erskine Park</td></tr>
    <tr><td>Your shipment's with a driver</td><td>20/03/2025</td><td>09:51</td><td>Gold Coast</td></tr>
    <tr><td>We've delivered your shipment</td><td>20/03/2025</td><td>12:01</td><td>Gold Coast</td></tr>
  </table>
  <p style="margin-top:1em"><a href="/sigimg?con=${encodeURIComponent(con)}" id="view-pod">View POD Image</a></p>
</body></html>`;

function noCache(res) {
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');
  res.setHeader('Pragma', 'no-cache');
  res.setHeader('Expires', '-1');
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
}

module.exports = (req, res) => {
  noCache(res);

  if (req.method === 'POST') {
    const con = (req.body && req.body.con) || 'FJP001034947';
    res.statusCode = 200;
    return res.end(resultsPage(con, 'POST'));
  }

  if (req.method === 'GET') {
    // Back-nav lands here. Trang vẫn render bình thường để user không thấy
    // error page. Signal duy nhất là marker "Rendered via GET" + Vercel logs.
    const con = (req.query && req.query.con) || 'FJP001034947';
    res.statusCode = 200;
    return res.end(resultsPage(con, 'GET'));
  }

  res.statusCode = 405;
  res.end('<h1>405 Method Not Allowed</h1>');
};
