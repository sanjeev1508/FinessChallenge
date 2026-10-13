import { lazy, Suspense } from "react";
import { NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useCurrentUser } from "./useCurrentUser.js";
import { setAccessToken } from "./api.js";
import Leaderboard from "./pages/Leaderboard.jsx";
import LogActivity from "./pages/LogActivity.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import { Loading } from "./components/Status.jsx";
import PageBoundary from "./components/PageBoundary.jsx";

const Dashboard = lazy(() => import("./pages/Dashboard.jsx"));

export default function App() {
  const [userId, setUserId] = useCurrentUser();
  const nav = useNavigate();
  function logout() {
    setAccessToken(null);
    setUserId(null);
    nav("/");
  }
  return (
    <div className="shell">
      <header className="topbar">
        <NavLink to="/" className="brand" aria-label="Fitness Challenge home">
          <span className="brand-mark" aria-hidden="true">FC</span>
          <span className="brand-name">Fitness Challenge</span>
        </NavLink>
        <nav className="nav" aria-label="Main">
          <NavLink to="/" end>Leaderboard</NavLink>
          {userId ? (
            <>
              <NavLink to="/dashboard">My dashboard</NavLink>
              <NavLink to="/log" className="nav-cta">Log activity</NavLink>
              <button type="button" className="nav-logout" onClick={logout}>Log out</button>
            </>
          ) : (
            <>
              <NavLink to="/login">Log in</NavLink>
              <NavLink to="/join" className="nav-cta">Join challenge</NavLink>
            </>
          )}
        </nav>
      </header>
      <main className="page">
        <PageBoundary>
          <Suspense fallback={<Loading what="Loading page" />}>
            <Routes>
              <Route path="/" element={<Leaderboard currentUserId={userId} />} />
              <Route path="/dashboard" element={userId ? <Dashboard userId={userId} /> : <Navigate to="/login" replace />} />
              <Route path="/dashboard/:viewedUserId" element={userId ? <Dashboard userId={userId} /> : <Navigate to="/login" replace />} />
              <Route path="/log" element={userId ? <LogActivity userId={userId} /> : <Navigate to="/login" replace />} />
              <Route path="/join" element={userId ? <Navigate to="/dashboard" replace /> : <Register setUserId={setUserId} />} />
              <Route path="/login" element={userId ? <Navigate to="/dashboard" replace /> : <Login setUserId={setUserId} />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </PageBoundary>
      </main>
      <footer className="footer">
        Points: running 100/km, walking 50/km, cycling 25/km, swimming 15/min, gym 5/min, 1 per 100 steps. All calendar days use UTC.
      </footer>
    </div>
  );
}
