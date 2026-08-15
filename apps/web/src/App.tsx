import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { MarketingLayout } from "./components/MarketingLayout";
import { Home } from "./pages/Home";
import { Jobs } from "./pages/Jobs";
import { JobDetail } from "./pages/JobDetail";
import { Marketing } from "./pages/Marketing";
import { Me } from "./pages/Me";
import { Streak } from "./pages/Streak";
import { Board } from "./pages/Board";
import { Countries } from "./pages/Countries";
import { Country } from "./pages/Country";
import { Join } from "./pages/Join";
import { Terms } from "./pages/Terms";

export default function App() {
  return (
    <Routes>
      <Route element={<MarketingLayout />}>
        <Route path="/" element={<Marketing />} />
      </Route>
      <Route element={<Layout />}>
        <Route path="/app" element={<Home />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/jobs/:id" element={<JobDetail />} />
        <Route path="/me" element={<Me />} />
        <Route path="/streak" element={<Streak />} />
        <Route path="/board" element={<Board />} />
        <Route path="/countries" element={<Countries />} />
        <Route path="/countries/:slug" element={<Country />} />
        <Route path="/join" element={<Join />} />
        <Route path="/terms" element={<Terms />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
