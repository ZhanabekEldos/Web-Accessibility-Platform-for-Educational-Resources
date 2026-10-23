import { createRoot } from "react-dom/client";
import App from "./app.jsx";
import { ConfirmProvider } from "./components/Dialog.jsx";
import { ToastProvider } from "./components/Toast.jsx";
import { I18nProvider } from "./i18n/index.jsx";
import { PrefsProvider } from "./prefs.jsx";
import "./styles/app.css";

createRoot(document.getElementById("root")).render(
  <PrefsProvider>
    <I18nProvider>
      <ToastProvider>
        <ConfirmProvider>
          <App />
        </ConfirmProvider>
      </ToastProvider>
    </I18nProvider>
  </PrefsProvider>,
);
