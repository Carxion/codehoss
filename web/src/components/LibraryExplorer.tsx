import { useEffect, useMemo, useState } from "react";
import { api, type Library, type LibraryIndex, type LibraryMember } from "../api";
import Markdown from "./Markdown";

interface Props {
  moduleId: string;
  glossary: Record<string, string>;
  onInsert: (text: string, importModule: string | null) => void;
  onClose: () => void;
}

interface Selected {
  library: string;
  member: LibraryMember;
  owner?: LibraryMember; // the class, for methods
}

const KIND_LABEL: Record<LibraryMember["kind"], string> = {
  function: "Functions",
  class: "Types & classes",
  value: "Values",
  exception: "Errors",
};

export default function LibraryExplorer({ moduleId, glossary, onInsert, onClose }: Props) {
  const [index, setIndex] = useState<LibraryIndex | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<string | null>("builtins");
  const [selected, setSelected] = useState<Selected | null>(null);

  useEffect(() => {
    api.library(moduleId).then(setIndex, (e) => setError(e.message));
  }, [moduleId]);

  const matches = useMemo(() => {
    if (!index || !query.trim()) return null;
    const q = query.toLowerCase();
    const hits: Selected[] = [];
    for (const library of index.libraries) {
      for (const member of library.members) {
        if (member.name.toLowerCase().includes(q) || member.doc.toLowerCase().includes(q)) {
          hits.push({ library: library.name, member });
        }
        for (const method of member.members ?? []) {
          if (method.name.toLowerCase().includes(q) || method.doc.toLowerCase().includes(q)) {
            hits.push({ library: library.name, member: method, owner: member });
          }
        }
      }
    }
    return hits.slice(0, 60);
  }, [index, query]);

  return (
    <aside className="library" aria-label="Library Explorer">
      <div className="library-head">
        <strong>Library Explorer</strong>
        <button className="link" onClick={onClose} aria-label="Close Library Explorer">
          ✕
        </button>
      </div>
      <input
        className="library-search"
        placeholder='Search, e.g. "round" or "sort"'
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {error && <p className="error-text small">{error}</p>}
      {selected && (
        <Details
          selected={selected}
          note={glossary[selected.member.name]}
          onInsert={onInsert}
          onBack={() => setSelected(null)}
        />
      )}
      {!selected && matches && (
        <ul className="library-list">
          {matches.length === 0 && <li className="muted small">Nothing found.</li>}
          {matches.map((hit) => (
            <li key={`${hit.library}.${hit.owner?.name ?? ""}.${hit.member.name}`}>
              <button className="library-item" onClick={() => setSelected(hit)}>
                <code>{qualifiedName(hit)}</code>
                <span className="muted small">{hit.member.doc}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {!selected && !matches && index && (
        <ul className="library-list">
          {orderLibraries(index).map((library) => (
            <li key={library.name}>
              <button
                className="library-lib"
                onClick={() => setOpen(open === library.name ? null : library.name)}
                aria-expanded={open === library.name}
              >
                <span>{open === library.name ? "▾" : "▸"}</span>
                <code>{library.name}</code>
                {index.featured.includes(library.name) && <span className="pill">featured</span>}
              </button>
              {open === library.name && <LibraryMembers library={library} onSelect={setSelected} />}
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

function LibraryMembers({ library, onSelect }: { library: Library; onSelect: (s: Selected) => void }) {
  const groups = (["function", "class", "value", "exception"] as const)
    .map((kind) => ({ kind, members: library.members.filter((m) => m.kind === kind) }))
    .filter((g) => g.members.length);
  return (
    <div className="library-members">
      {library.doc && <p className="muted small">{library.doc}</p>}
      {groups.map((group) => (
        <details key={group.kind} open={group.kind !== "exception"}>
          <summary>{KIND_LABEL[group.kind]} ({group.members.length})</summary>
          {group.members.map((member) => (
            <button
              key={member.name}
              className="library-item"
              onClick={() => onSelect({ library: library.name, member })}
            >
              <code>{member.name}</code>
              <span className="muted small">{member.doc}</span>
            </button>
          ))}
        </details>
      ))}
    </div>
  );
}

function Details({
  selected,
  note,
  onInsert,
  onBack,
}: {
  selected: Selected;
  note?: string;
  onInsert: Props["onInsert"];
  onBack: () => void;
}) {
  const { member, owner, library } = selected;
  const isMethod = Boolean(owner);
  const isBuiltin = library === "builtins";
  const snippet = isMethod
    ? `.${member.name}()`
    : member.kind === "value"
      ? `${isBuiltin ? "" : library + "."}${member.name}`
      : `${isBuiltin ? "" : library + "."}${member.name}()`;
  return (
    <div className="library-details">
      <button className="link small" onClick={onBack}>
        ← Back
      </button>
      <h3>
        <code>{qualifiedName(selected)}</code>
      </h3>
      {note && (
        <div className="hint">
          <Markdown>{`💡 ${note}`}</Markdown>
        </div>
      )}
      {member.signature && <pre className="signature">{member.name + member.signature}</pre>}
      <p>{member.doc || "No description available."}</p>
      {member.kind === "class" && member.members && member.members.length > 0 && (
        <p className="muted small">
          {member.members.length} methods, for example{" "}
          {member.members.slice(0, 5).map((m) => m.name).join(", ")}. Search for them by name.
        </p>
      )}
      <button
        className="primary small"
        onClick={() => onInsert(snippet, isMethod || isBuiltin ? null : library)}
      >
        Insert <code>{snippet}</code>
      </button>
      {isMethod && (
        <p className="muted small">
          Methods go after a value, e.g. <code>name{snippet}</code>
        </p>
      )}
    </div>
  );
}

function qualifiedName({ library, member, owner }: Selected) {
  if (owner) return `${owner.name}.${member.name}`;
  return library === "builtins" ? member.name : `${library}.${member.name}`;
}

function orderLibraries(index: LibraryIndex) {
  const featured = index.libraries.filter((l) => index.featured.includes(l.name));
  const rest = index.libraries.filter((l) => !index.featured.includes(l.name));
  return [...featured, ...rest];
}
