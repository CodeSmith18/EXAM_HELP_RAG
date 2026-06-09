import { useEffect, useMemo, useState } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "base",
  securityLevel: "strict",
  themeVariables: {
    primaryColor: "#eef6f4",
    primaryBorderColor: "#0f766e",
    primaryTextColor: "#172033",
    lineColor: "#4f46e5",
    secondaryColor: "#fff7ed",
    tertiaryColor: "#f8fafc"
  }
});

interface MermaidBlockProps {
  chart?: string | null;
}

export function MermaidBlock({ chart }: MermaidBlockProps) {
  const [svg, setSvg] = useState("");
  const [error, setError] = useState("");
  const chartId = useMemo(() => `mermaid-${Math.random().toString(36).slice(2)}`, [chart]);

  useEffect(() => {
    let cancelled = false;
    setSvg("");
    setError("");

    if (!chart?.trim()) {
      return;
    }

    mermaid
      .render(chartId, chart)
      .then((result) => {
        if (!cancelled) {
          setSvg(result.svg);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Diagram could not be rendered.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [chart, chartId]);

  if (!chart?.trim()) {
    return null;
  }

  return (
    <div className="rounded-lg border border-line bg-white p-4">
      {error ? <p className="text-sm font-medium text-red-600">{error}</p> : null}
      {svg ? <div className="overflow-x-auto" dangerouslySetInnerHTML={{ __html: svg }} /> : null}
    </div>
  );
}

