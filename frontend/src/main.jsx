import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "./ConfigContext";
import { AuthProvider } from "./auth/AuthContext";
import { ThemeProvider } from "./ThemeContext";
import { CurrencyProvider } from "./CurrencyContext";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <CurrencyProvider>
          <ConfigProvider>
            <AuthProvider>
              <App />
            </AuthProvider>
          </ConfigProvider>
        </CurrencyProvider>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
