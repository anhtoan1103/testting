const sigimgPage = (con) => `<!doctype html>
<html><head><title>Proof of Delivery</title></head>
<body style="font-family:sans-serif;margin:2em">
  <h2 style="color:#d35400">Proof of Delivery Details</h2>
  <p><b>Consignment No:</b> ${con}</p>
  <p>Signed by: Ludwic &nbsp; | &nbsp; Date: 20/03/2025 12:01</p>
  <p>Delivery Notation: We've delivered your shipment</p>
  <hr><div style="margin-top:2em">
    <button id="in-page-back" onclick="history.back()">Back</button>
    <span style="margin-left:2em;color:#888">(or use the browser's back button)</span>
  </div>
</body></html>`;

module.exports = (req, res) => {
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');
  res.setHeader('Pragma', 'no-cache');
  res.setHeader('Expires', '-1');
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  const con = (req.query && req.query.con) || 'FJP001034947';
  res.statusCode = 200;
  res.end(sigimgPage(con));
};
