import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { SessionProvider } from "./context/SessionContext";
import { Shell } from "./layout/Shell";
import { AchievementsPage } from "./pages/AchievementsPage";
import { AdminPage } from "./pages/AdminPage";
import { ChallengePage } from "./pages/ChallengePage";
import { FeedPage } from "./pages/FeedPage";
import { HeroPage } from "./pages/HeroPage";
import { MorePage } from "./pages/MorePage";
import { OnlinePage } from "./pages/OnlinePage";
import { ProfilePage } from "./pages/ProfilePage";
import { RanksPage } from "./pages/RanksPage";
import { ShopPage } from "./pages/ShopPage";
import { TournamentPage } from "./pages/TournamentPage";

export default function App() {
  return (
    <SessionProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Shell />}>
            <Route index element={<FeedPage />} />
            <Route path="ranks" element={<RanksPage />} />
            <Route path="shop" element={<ShopPage />} />
            <Route path="more" element={<MorePage />} />
            <Route path="me" element={<ProfilePage self />} />
            <Route path="u/:userId" element={<ProfilePage />} />
            <Route path="challenge" element={<ChallengePage />} />
            <Route path="hero" element={<HeroPage />} />
            <Route path="achievements" element={<AchievementsPage />} />
            <Route path="tournament" element={<TournamentPage />} />
            <Route path="online" element={<OnlinePage />} />
            <Route path="admin" element={<AdminPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </SessionProvider>
  );
}
