import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

// #region agent log
try {
  fetch("http://127.0.0.1:7832/ingest/8a067dd9-fa67-459c-9257-28e916d33083", { method: "POST", headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "b65a9c" }, body: JSON.stringify({ sessionId: "b65a9c", location: "main.jsx", message: "SPA mount start", data: { pathname: window.location.pathname }, hypothesisId: "H4", timestamp: Date.now() }) }).catch(() => {});
} catch (e) {}
// #endregion

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
