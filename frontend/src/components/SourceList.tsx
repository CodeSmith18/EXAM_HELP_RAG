import { FileText } from "lucide-react";
import { SourceRef } from "../types";

interface SourceListProps {
  sources: SourceRef[];
}

export function SourceList({ sources }: SourceListProps) {
  if (!sources.length) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {sources.map((source) => (
        <span
          key={`${source.chunk_id}-${source.page_number}`}
          className="inline-flex max-w-full items-center gap-1 rounded-md border border-line bg-slate-50 px-2 py-1 text-xs font-medium text-slate-600"
          title={source.chunk_id}
        >
          <FileText size={13} aria-hidden="true" />
          <span className="truncate">
            {source.file_name} p.{source.page_number}
          </span>
        </span>
      ))}
    </div>
  );
}

