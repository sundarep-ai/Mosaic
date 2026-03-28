import { createContext, useContext, useState, useEffect } from "react";
import { fetchAppConfig } from "./config";

const ConfigContext = createContext({ userA: "", userB: "", userALogin: "", userBLogin: "" });

export function ConfigProvider({ children }) {
  const [users, setUsers] = useState({ userA: "", userB: "", userALogin: "", userBLogin: "" });
  const [ready, setReady] = useState(false);

  useEffect(() => {
    fetchAppConfig().then((data) => {
      setUsers({
        userA: data.userA,
        userB: data.userB,
        userALogin: data.userALogin || "",
        userBLogin: data.userBLogin || "",
      });
      setReady(true);
    });
  }, []);

  if (!ready) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <ConfigContext.Provider value={users}>{children}</ConfigContext.Provider>
  );
}

export function useUsers() {
  return useContext(ConfigContext);
}
