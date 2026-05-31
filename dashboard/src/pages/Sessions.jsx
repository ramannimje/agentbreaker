import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getSessions, createSession } from "../api.js";

export default function SessionsPage() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [projectId, setProjectId] = useState("default");
  const [tokenBudget, setTokenBudget] = useState(1000);

  useEffect(() => {
    loadSessions();
  }, []);

  async function loadSessions() {
    setLoading(true);
    try {
      const data = await getSessions();
      setSessions(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(ev) {
    ev.preventDefault();
    try {
      const created = await createSession({ project_id: projectId, token_budget: Number(tokenBudget) });
      window.location.href = `/sessions/${created.session_id}`;
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Sessions</h1>
          <p>Live sessions and budget burn from AgentBreaker.</p>
        </div>
      </div>

      <section className="panel form-panel">
        <h2>Create a new session</h2>
        <form onSubmit={handleCreate} className="form-grid">
          <label>
            Project ID
            <input value={projectId} onChange={(e) => setProjectId(e.target.value)} />
          </label>
          <label>
            Token budget
            <input type="number" value={tokenBudget} onChange={(e) => setTokenBudget(e.target.value)} />
          </label>
          <button type="submit">Create session</button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Active sessions</h2>
          <button onClick={loadSessions}>Refresh</button>
        </div>
        {loading ? (
          <div className="empty-state">Loading sessions…</div>
        ) : error ? (
          <div className="empty-state error">{error}</div>
        ) : sessions.length === 0 ? (
          <div className="empty-state">No sessions found.</div>
        ) : (
          <div className="grid-table">
            <div className="table-row header">
              <span>Session</span>
              <span>Project</span>
              <span>Status</span>
              <span>Budget</span>
              <span>Spent</span>
              <span>Details</span>
            </div>
            {sessions.map((session) => (
              <div key={session.session_id} className="table-row">
                <span>{session.session_id.slice(0, 8)}</span>
                <span>{session.project_id}</span>
                <span>{session.status}</span>
                <span>{session.token_budget}</span>
                <span>{session.tokens_spent}</span>
                <span>
                  <Link to={`/sessions/${session.session_id}`}>Open</Link>
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
