import { X, ExternalLink, AlertCircle, CheckCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useStore } from '../hooks/useStore'
import clsx from 'clsx'

export default function ResearchPanel() {
  const { currentResearchResult, toggleResearchPanel } = useStore()

  if (!currentResearchResult) {
    return null
  }

  const { query, sources, synthesis, confidence_score, citations } =
    currentResearchResult

  const confidenceLevel =
    confidence_score >= 0.8
      ? 'high'
      : confidence_score >= 0.5
      ? 'medium'
      : 'low'

  const confidenceColors = {
    high: 'text-green-400',
    medium: 'text-yellow-400',
    low: 'text-red-400',
  }

  return (
    <div className="w-96 border-l border-companion-border bg-companion-surface flex flex-col">
      {/* Header */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-companion-border">
        <h2 className="font-semibold">Research Results</h2>
        <button
          onClick={toggleResearchPanel}
          className="p-1.5 rounded-lg hover:bg-companion-border transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Query */}
        <div className="p-4 border-b border-companion-border">
          <div className="text-xs text-companion-muted uppercase tracking-wide mb-1">
            Query
          </div>
          <div className="font-medium">{query}</div>
        </div>

        {/* Confidence */}
        <div className="p-4 border-b border-companion-border flex items-center justify-between">
          <div>
            <div className="text-xs text-companion-muted uppercase tracking-wide mb-1">
              Confidence
            </div>
            <div className={clsx('font-medium', confidenceColors[confidenceLevel])}>
              {Math.round(confidence_score * 100)}% - {confidenceLevel} confidence
            </div>
          </div>
          {confidenceLevel === 'high' ? (
            <CheckCircle className="w-5 h-5 text-green-400" />
          ) : (
            <AlertCircle
              className={clsx(
                'w-5 h-5',
                confidenceLevel === 'medium' ? 'text-yellow-400' : 'text-red-400'
              )}
            />
          )}
        </div>

        {/* Sources */}
        <div className="p-4 border-b border-companion-border">
          <div className="text-xs text-companion-muted uppercase tracking-wide mb-3">
            Sources ({sources.length})
          </div>
          <div className="space-y-3">
            {sources.map((source) => (
              <div
                key={source.id}
                className="p-3 bg-companion-bg rounded-lg border border-companion-border"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium text-sm hover:text-primary-400 transition-colors line-clamp-2"
                    >
                      {source.title}
                    </a>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs px-1.5 py-0.5 bg-companion-border rounded">
                        {source.source_type}
                      </span>
                      <span className="text-xs text-companion-muted">
                        {Math.round(source.reliability_score * 100)}% reliable
                      </span>
                    </div>
                  </div>
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 rounded hover:bg-companion-border transition-colors"
                  >
                    <ExternalLink className="w-4 h-4 text-companion-muted" />
                  </a>
                </div>
                {source.snippet && (
                  <p className="text-xs text-companion-muted mt-2 line-clamp-2">
                    {source.snippet}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Synthesis */}
        <div className="p-4">
          <div className="text-xs text-companion-muted uppercase tracking-wide mb-3">
            Synthesis
          </div>
          <div className="markdown-content text-sm">
            <ReactMarkdown>{synthesis}</ReactMarkdown>
          </div>
        </div>

        {/* Citations */}
        {citations && citations.length > 0 && (
          <div className="p-4 border-t border-companion-border">
            <div className="text-xs text-companion-muted uppercase tracking-wide mb-3">
              Citations
            </div>
            <ol className="space-y-2 text-sm">
              {citations.map((citation, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-companion-muted">[{i + 1}]</span>
                  <a
                    href={citation.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-400 hover:text-primary-300 truncate"
                  >
                    {citation.title}
                  </a>
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </div>
  )
}
