import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { bootTelegram } from "./api/client";
import "./styles/global.css";

bootTelegram();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
