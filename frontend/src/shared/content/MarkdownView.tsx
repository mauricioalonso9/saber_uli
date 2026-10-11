import "katex/dist/katex.min.css";

import ReactMarkdown, { type Components } from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import { cn } from "@/shared/lib/utils";
import { ScrollRegion } from "@/shared/ui/ScrollRegion";

/** Quita `node` (el árbol de Markdown) para no pasarlo al DOM. */
function domProps<P extends { node?: unknown }>(props: P): Omit<P, "node"> {
  const rest = { ...props };
  delete rest.node;
  return rest;
}

const components: Components = {
  p: (props) => <p className="mb-3 leading-relaxed last:mb-0" {...domProps(props)} />,
  ul: (props) => <ul className="mb-3 list-disc pl-6" {...domProps(props)} />,
  ol: (props) => <ol className="mb-3 list-decimal pl-6" {...domProps(props)} />,
  // Una tabla ancha se desplaza dentro de su región (ScrollRegion), no la página en el celular.
  table: (props) => (
    <div className="mb-3">
      <ScrollRegion label="Tabla">
        <table className="w-full border-collapse text-sm" {...domProps(props)} />
      </ScrollRegion>
    </div>
  ),
  th: (props) => (
    <th className="border border-border bg-muted px-2 py-1 text-left" {...domProps(props)} />
  ),
  td: (props) => <td className="border border-border px-2 py-1" {...domProps(props)} />,
  a: ({ children, ...props }) => (
    <a className="underline" target="_blank" rel="noopener noreferrer" {...domProps(props)}>
      {children}
    </a>
  ),
};

interface MarkdownViewProps {
  markdown: string;
  className?: string;
}

/**
 * Markdown del banco de ítems (research R-10): tablas GFM y fórmulas `$…$` con KaTeX, con salida
 * HTML y MathML para que los lectores de pantalla lean la fórmula. `skipHtml` descarta el HTML
 * crudo y no se usa `rehype-raw`, así el contenido nunca ejecuta código.
 */
export function MarkdownView({ markdown, className }: MarkdownViewProps) {
  return (
    <div className={cn("text-base", className)}>
      <ReactMarkdown
        skipHtml
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { output: "htmlAndMathml", throwOnError: false }]]}
        components={components}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
