import DOMPurify from "dompurify";
import type { CellOutput } from "../useKernel";
import ExplanationCard from "./ExplanationCard";
import Markdown from "./Markdown";

// Rich output comes from learner code, so HTML is sanitised before it's shown.
export default function CellOutputView({
  output,
  onGoToLine,
}: {
  output: CellOutput;
  onGoToLine: (line: number) => void;
}) {
  if (output.kind === "stream") {
    return <pre className={`cell-stream ${output.name}`}>{output.text}</pre>;
  }
  if (output.kind === "error") {
    return (
      <ExplanationCard
        explanation={{
          title: output.ename,
          message: output.explanation || `${output.ename}: ${output.evalue}`,
          line: output.line,
          raw: output.traceback || `${output.ename}: ${output.evalue}`,
        }}
        onGoToLine={onGoToLine}
      />
    );
  }
  const { data } = output;
  if (data["image/png"]) {
    return <img className="cell-image" src={`data:image/png;base64,${data["image/png"]}`} alt="Chart output" />;
  }
  if (data["image/svg+xml"]) {
    return <div className="cell-svg" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(data["image/svg+xml"]) }} />;
  }
  if (data["text/html"]) {
    return (
      <div
        className="cell-html"
        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(data["text/html"]) }}
      />
    );
  }
  if (data["text/markdown"]) return <Markdown>{data["text/markdown"]}</Markdown>;
  return <pre className="cell-text">{data["text/plain"] ?? ""}</pre>;
}
