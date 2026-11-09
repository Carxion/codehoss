import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Lesson text is authored content; react-markdown never renders raw HTML.
export default function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
