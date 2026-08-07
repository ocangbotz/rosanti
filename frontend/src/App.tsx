import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { AnalysisPage } from "@/pages/AnalysisPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { JournalPage } from "@/pages/JournalPage";
import { MarketPage } from "@/pages/MarketPage";
import { PerformancePage } from "@/pages/PerformancePage";
import { SettingsPage } from "@/pages/SettingsPage";
import { TelegramPage } from "@/pages/TelegramPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="market" element={<MarketPage />} />
        <Route path="analysis" element={<AnalysisPage />} />
        <Route path="journal" element={<JournalPage />} />
        <Route path="performance" element={<PerformancePage />} />
        <Route path="telegram" element={<TelegramPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
