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
</body></html>`;

module.exports = (req, res) => {
  if (req.method == 'POST') {

  const con = (req.body && req.body.con) || 'FJP001034947';
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 'private');
  res.setHeader('Content-Type', 'text/html');
  res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains;');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Frame-Options', 'SAMEORIGIN');
  res.setHeader('X-Tnt', '5FE265A');
  res.setHeader('X-Xss-Protection', '1; mode=block');
  res.statusCode = 200;
  res.end(resultsPage(con));
  }
};

