"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  content: string;
}

export default function MarkdownViewer({ content }: Props) {
  return (
    <div className="prose prose-invert prose-sm max-w-none text-zinc-300
      prose-headings:text-zinc-100 prose-headings:font-semibold
      prose-h1:text-base prose-h1:border-b prose-h1:border-zinc-700 prose-h1:pb-2
      prose-h2:text-sm prose-h3:text-sm
      prose-p:text-zinc-300 prose-p:leading-relaxed
      prose-strong:text-zinc-100
      prose-em:text-zinc-400
      prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline
      prose-code:bg-zinc-900 prose-code:text-emerald-400 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs
      prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-zinc-800
      prose-blockquote:border-l-zinc-600 prose-blockquote:text-zinc-400
      prose-hr:border-zinc-700
      prose-table:text-xs
      prose-th:bg-zinc-800 prose-th:text-zinc-400
      prose-td:border-zinc-800
      prose-li:text-zinc-300">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
