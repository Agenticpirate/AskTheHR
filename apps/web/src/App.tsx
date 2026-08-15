import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Home } from "./pages/Home";
import { Jobs } from "./pages/Jobs";
import { JobDetail } from "./pages/JobDetail";
import { Me } from "./pages/Me";
import { Streak } from "./pages/Streak";
import { Board } from "./pages/Board";
import { Countries } from "./pages/Countries";
import { Country } from "./pages/Country";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/jobs/:id" element={<JobDetail />} />
        <Route path="/me" element={<Me />} />
        <Route path="/streak" element={<Streak />} />
        <Route path="/board" element={<Board />} />
        <Route path="/countries" element={<Countries />} />
        <Route path="/countries/:slug" element={<Country />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
