import { useState } from "react";
import type { Explanation } from "../api";
import Markdown from "./Markdown";

export default function ExplanationCard({
  explanation,
  onGoToLine,
}: {
  explanation: Explanation;
  onGoToLine: (line: number) => void;
}) {
  const [showRaw, setShowRaw] = useState(false);
  return (
    <div className="explanation" role="alert">
      <div className="explanation-head">
        <strong>{explanation.title}</strong>
        {explanation.line && (
          <button className="link small" onClick={() => onGoToLine(explanation.line!)}>
            Go to line {explanation.line}
          </button>
        )}
      </div>
      <Markdown>{explanation.message}</Markdown>
      <button className="link small" onClick={() => setShowRaw(!showRaw)}>
        {showRaw ? "Hide" : "Show"} Python's original message
      </button>
      {showRaw && <pre className="raw">{explanation.raw}</pre>}
    </div>
  );
}
