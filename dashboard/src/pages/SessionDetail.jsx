import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { getSession, getSessionTrace } from "../api.js";

function buildHistory(trace, startingValue) {
  const sorted = [...trace].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  let cumulative = startingValue || 0;
  return sorted.map((item) => {
    cumulative += item.tokens_used;
    return {
      time: new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      tokens: cumulative,
      tool: item.tool_name,
    };
  });
}

export default function SessionDetailPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [trace, setTrace] = useState([]);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!sessionId) return;
    loadSession();
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/sessions/${sessionId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.event === "burn_update") {
          setHistory((current) => {
            const lastTokens = current.length ? current[current.length - 1].tokens : 0;
            return [
              ...current,
              {
                time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                tokens: lastTokens + Number(payload.tokens_spent || 0),
                tool: "live event",
              },
            ];
          });
          setSession((prev) => prev ? { ...prev, tokens_spent: (prev.tokens_spent || 0) + Number(payload.tokens_spent || 0) } : prev);
        }
      } catch (err) {
        console.warn(err);
      }
    });

    ws.addEventListener("error", (err) => {
      console.warn("WebSocket error", err);
    });

    return () => {
      ws.close();
    };
  }, [sessionId]);

  async function loadSession() {
    try {
      const data = await getSession(sessionId);
      setSession(data);
      const traceData = await getSessionTrace(sessionId);
      setTrace(traceData);
      setHistory(buildHistory(traceData, 0));
    } catch (err) {
      setError(err.message);
    }
  }

  const totalBurn = useMemo(() => session?.tokens_spent ?? 0, [session]);
  const budget = useMemo(() => session?.token_budget ?? 0, [session]);
  const ratio = budget ? ((totalBurn / budget) * 100).toFixed(1) : "0";

  return (
    <div>
      <div className="page-header">
        <div>
          <button className="back-button" onClick={() => navigate(-1)}>
            ← Back
          </button>
          <h1>Session {sessionId?.slice(0, 8)}</h1>
          <p>Project: {session?.project_id}</p>
        </div>
      </div>

      {error ? (
        <div className="empty-state error">{error}</div>
      ) : !session ? (
        <div className="empty-state">Loading session…</div>
      ) : (
        <>
          <section className="panel stats-panel">
            <div>
              <span className="stat-label">Status</span>
              <strong>{session.status}</strong>
            </div>
            <div>
              <span className="stat-label">Budget</span>
              <strong>{budget}</strong>
            </div>
            <div>
              <span className="stat-label">Tokens spent</span>
              <strong>{totalBurn}</strong>
            </div>
            <div>
              <span className="stat-label">Burn ratio</span>
              <strong>{ratio}%</strong>
            </div>
          </section>

          <section className="panel">
            <h2>Burn timeline</h2>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={history} margin={{ top: 20, right: 24, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="#2f3340" />
                  <XAxis dataKey="time" stroke="#8899aa" />
                  <YAxis stroke="#8899aa" />
                  <Tooltip contentStyle={{ backgroundColor: "#12131a", borderColor: "#2f3340" }} />
                  <Line type="monotone" dataKey="tokens" stroke="#00ff88" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="panel">
            <h2>Tool call trace</h2>
            {trace.length === 0 ? (
              <div className="empty-state">No trace events yet.</div>
            ) : (
              <div className="grid-table">
                <div className="table-row header">
                  <span>Time</span>
                  <span>Tool</span>
                  <span>Tokens</span>
                </div>
                {trace.map((entry) => (
                  <div key={entry.call_id} className="table-row">
                    <span>{new Date(entry.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                    <span>{entry.tool_name}</span>
                    <span>{entry.tokens_used}</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
