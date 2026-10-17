import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api } from "../api/client";
import type { Me } from "../api/types";

type Session = {
  me: Me | null;
  isSudo: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const Ctx = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [isSudo, setIsSudo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const m = await api<Me>("/api/me");
      setMe(m);
      setError(null);
      try {
        const adm = await api<{ is_sudo: boolean }>("/api/admin/me");
        setIsSudo(!!adm.is_sudo);
      } catch {
        setIsSudo(false);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "خطای ورود");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <Ctx.Provider value={{ me, isSudo, error, refresh }}>
      {children}
    </Ctx.Provider>
  );
}

export function useSession(): Session {
  const v = useContext(Ctx);
  if (!v) throw new Error("SessionProvider missing");
  return v;
}
