import React from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import SessionsPage from "./pages/Sessions.jsx";
import SessionDetailPage from "./pages/SessionDetail.jsx";
import "./styles.css";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="topbar">
          <div className="brand">AgentBreaker</div>
          <nav>
            <Link to="/">Sessions</Link>
          </nav>
        </header>
        <main className="content">
          <Routes>
            <Route path="/" element={<SessionsPage />} />
            <Route path="/sessions/:sessionId" element={<SessionDetailPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
