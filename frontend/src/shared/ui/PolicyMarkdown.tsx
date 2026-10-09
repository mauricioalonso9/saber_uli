import type { ComponentPropsWithoutRef } from "react";
import ReactMarkdown, { type Components } from "react-markdown";

import { cn } from "@/shared/lib/utils";

/** Quita `node` (el árbol de Markdown) para no pasarlo al DOM. */
function domProps<P extends { node?: unknown }>(props: P): Omit<P, "node"> {
  const rest = { ...props };
  delete rest.node;
  return rest;
}

const components: Components = {
  h1: ({ children, ...props }) => (
    <h2 className="mb-3 mt-2 text-xl font-bold" {...domProps(props)}>
      {children}
    </h2>
  ),
  h2: ({ children, ...props }) => (
    <h3 className="mb-2 mt-5 text-lg font-semibold" {...domProps(props)}>
      {children}
    </h3>
  ),
  h3: ({ children, ...props }) => (
    <h4 className="mb-2 mt-4 font-semibold" {...domProps(props)}>
      {children}
    </h4>
  ),
  h4: ({ children, ...props }) => (
    <h5 className="mb-2 mt-3 font-semibold" {...domProps(props)}>
      {children}
    </h5>
  ),
  p: (props) => <p className="mb-3 leading-relaxed" {...domProps(props)} />,
  ul: (props) => <ul className="mb-3 list-disc pl-6" {...domProps(props)} />,
  ol: (props) => <ol className="mb-3 list-decimal pl-6" {...domProps(props)} />,
  blockquote: (props) => (
    <blockquote
      className="mb-3 border-l-4 border-amber-400 bg-amber-50 px-4 py-2"
      {...domProps(props)}
    />
  ),
  a: ({ children, ...props }) => (
    <a className="underline" target="_blank" rel="noopener noreferrer" {...domProps(props)}>
      {children}
    </a>
  ),
};

interface PolicyMarkdownProps extends ComponentPropsWithoutRef<"article"> {
  markdown: string;
  /** Nombre accesible del artículo (título de la versión). */
  title: string;
}

/**
 * Texto de la política en Markdown (research R-40).
 *
 * `react-markdown` crea elementos de React sin `dangerouslySetInnerHTML`; `skipHtml` descarta el
 * HTML incrustado y no se usa `rehype-raw`. Los enlaces conservan el filtro de URL por defecto
 * (anula `javascript:` y otros esquemas inseguros). Los títulos bajan un nivel para que la página
 * conserve un único `h1`.
 */
export function PolicyMarkdown({ markdown, title, className, ...props }: PolicyMarkdownProps) {
  return (
    <article aria-label={title} className={cn("text-base", className)} {...props}>
      <ReactMarkdown skipHtml components={components}>
        {markdown}
      </ReactMarkdown>
    </article>
  );
}
