// src/main.jsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { AppProvider } from "./context/AppContext";
import "./App.css";

// ══════════════════════════════════════════════════════════════════
// Activation des mocks (si VITE_USE_MOCKS=true)
// ══════════════════════════════════════════════════════════════════
if (import.meta.env.VITE_USE_MOCKS === "true") {
  import("./mocks/mockApi").then(({ setupMocks }) => {
    setupMocks();
    console.log("[RiskGuard] ✅ Mocks activés");
  });
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <AppProvider>
          <App />
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                fontFamily: "'DM Sans', system-ui, sans-serif",
                fontSize: "14px",
                borderRadius: "12px",
                boxShadow: "0 8px 24px rgba(0,0,0,.12)",
                border: "1px solid #E5E7EB",
              },
              success: {
                iconTheme: { primary: "#10B981", secondary: "#fff" },
                style: { borderLeft: "4px solid #10B981" },
              },
              error: {
                iconTheme: { primary: "#EF4444", secondary: "#fff" },
                style: { borderLeft: "4px solid #EF4444" },
              },
            }}
          />
        </AppProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
