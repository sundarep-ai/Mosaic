import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { fetchAppConfig, API_BASE } from "./config";
import { fetchWithAuth } from "./api/fetchWithAuth";

const ConfigContext = createContext({ userA: "", userB: "", mode: "duo", setMode: () => {} });

export function ConfigProvider({ children }) {
  const [config, setConfig] = useState({ userA: "", userB: "", mode: "duo" });
  const [ready, setReady] = useState(false);

  useEffect(() => {
    fetchAppConfig().then((data) => {
      setConfig({
        userA: data.userA,
        userB: data.userB,
        mode: data.mode || "duo",
      });
      setReady(true);
    });
  }, []);

  const setMode = useCallback(async (newMode) => {
    const res = await fetchWithAuth(`${API_BASE}/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ app_mode: newMode }),
    });
    if (!res.ok) throw new Error("Failed to update mode");
    setConfig((prev) => ({ ...prev, mode: newMode }));
  }, []);

  if (!ready) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <ConfigContext.Provider value={{ ...config, setMode }}>
      {children}
    </ConfigContext.Provider>
  );
}

export function useUsers() {
  return useContext(ConfigContext);
}
