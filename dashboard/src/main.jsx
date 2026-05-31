import React from "react";
import { createRoot } from "react-dom/client";

function App() {
  return (
    <div style={{ padding: 24 }}>
      <h1>AgentBreaker Dashboard (Skeleton)</h1>
      <p>Real-time session burn and alerts will appear here.</p>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
