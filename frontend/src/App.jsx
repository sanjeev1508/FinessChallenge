import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useCurrentUser } from "./useCurrentUser.js";
import Leaderboard from "./pages/Leaderboard.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import LogActivity from "./pages/LogActivity.jsx";
import Register from "./pages/Register.jsx";

export default function App() {
  const [userId, setUserId] = useCurrentUser();
  return (
    <div className="shell">
      <header className="topbar">
        <NavLink to="/" className="brand" aria-label="Fitness Challenge home">
          <span className="brand-mark" aria-hidden="true">FC</span>
          <span className="brand-name">Fitness Challenge</span>
        </NavLink>
        <nav className="nav" aria-label="Main">
          <NavLink to="/" end>Leaderboard</NavLink>
          <NavLink to="/dashboard">My dashboard</NavLink>
          <NavLink to="/log" className="nav-cta">Log activity</NavLink>
        </nav>
      </header>
      <main className="page">
        <Routes>
          <Route path="/" element={<Leaderboard currentUserId={userId} />} />
          <Route path="/dashboard" element={<Dashboard userId={userId} setUserId={setUserId} />} />
          <Route path="/dashboard/:id" element={<Dashboard userId={userId} setUserId={setUserId} />} />
          <Route path="/log" element={<LogActivity userId={userId} setUserId={setUserId} />} />
          <Route path="/join" element={<Register setUserId={setUserId} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer className="footer">
        Points: running 100/km, walking 50/km, cycling 25/km, swimming 15/min, gym 5/min, 1 per 100 steps. All calendar days use UTC.
      </footer>
    </div>
  );
}
