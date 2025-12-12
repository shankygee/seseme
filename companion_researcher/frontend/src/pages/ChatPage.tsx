import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Volume2, VolumeX, FileText } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useChat } from '../hooks/useChat'
import { useStore } from '../hooks/useStore'
import ControlPanel from '../components/ControlPanel'
import ResearchPanel from '../components/ResearchPanel'
import SessionsPanel from '../components/SessionsPanel'
import clsx from 'clsx'

export default function ChatPage() {
  const [input, setInput] = useState('')
  const [voiceEnabled, setVoiceEnabled] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const { messages, isLoading, error, sendMessage } = useChat()
  const {
    activePersonality,
    showControlPanel,
    showResearchPanel,
    showSessionsPanel,
    currentResearchResult,
    toggleResearchPanel,
  } = useStore()

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
      inputRef.current.style.height = `${inputRef.current.scrollHeight}px`
    }
  }, [input])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      sendMessage(input.trim())
      setInput('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Sessions Panel */}
      {showSessionsPanel && <SessionsPanel />}

      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="h-14 px-4 flex items-center justify-between border-b border-companion-border bg-companion-surface">
          <div className="flex items-center gap-3">
            <h1 className="font-semibold">
              {activePersonality?.name || 'Companion Researcher'}
            </h1>
            {activePersonality && (
              <span className="text-xs text-companion-muted px-2 py-0.5 bg-companion-border rounded">
                {activePersonality.settings.tone}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {currentResearchResult && (
              <button
                onClick={toggleResearchPanel}
                className={clsx(
                  'p-2 rounded-lg transition-colors',
                  showResearchPanel
                    ? 'bg-primary-600 text-white'
                    : 'text-companion-muted hover:text-companion-text hover:bg-companion-border'
                )}
                title="View Research"
              >
                <FileText className="w-5 h-5" />
              </button>
            )}

            <button
              onClick={() => setVoiceEnabled(!voiceEnabled)}
              className={clsx(
                'p-2 rounded-lg transition-colors',
                voiceEnabled
                  ? 'bg-primary-600 text-white'
                  : 'text-companion-muted hover:text-companion-text hover:bg-companion-border'
              )}
              title={voiceEnabled ? 'Disable voice' : 'Enable voice'}
            >
              {voiceEnabled ? (
                <Volume2 className="w-5 h-5" />
              ) : (
                <VolumeX className="w-5 h-5" />
              )}
            </button>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 rounded-2xl bg-companion-surface flex items-center justify-center mb-4">
                <span className="text-3xl">
                  {activePersonality?.id === 'researcher'
                    ? '🔬'
                    : activePersonality?.id === 'coach'
                    ? '💪'
                    : activePersonality?.id === 'producer'
                    ? '🎬'
                    : '✨'}
                </span>
              </div>
              <h2 className="text-xl font-semibold mb-2">
                {activePersonality?.name || 'Welcome to Companion Researcher'}
              </h2>
              <p className="text-companion-muted max-w-md">
                {activePersonality?.description ||
                  'Ask me anything - I can help with research, answer questions, or just chat.'}
              </p>
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {[
                  'Research the best AI video tools',
                  'Explain quantum computing simply',
                  'Help me brainstorm project ideas',
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setInput(suggestion)}
                    className="px-3 py-1.5 text-sm bg-companion-surface hover:bg-companion-border rounded-lg transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={clsx(
                'flex',
                message.role === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              <div
                className={clsx(
                  'max-w-[80%] px-4 py-3',
                  message.role === 'user'
                    ? 'message-user'
                    : 'message-assistant'
                )}
              >
                {message.role === 'assistant' ? (
                  <div className="markdown-content">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p>{message.content}</p>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="message-assistant px-4 py-3">
                <div className="typing-indicator flex gap-1">
                  <span className="w-2 h-2 bg-companion-muted rounded-full" />
                  <span className="w-2 h-2 bg-companion-muted rounded-full" />
                  <span className="w-2 h-2 bg-companion-muted rounded-full" />
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="flex justify-center">
              <div className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg text-sm">
                {error}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-companion-border bg-companion-surface">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your message... (Shift+Enter for new line)"
                className="w-full px-4 py-3 bg-companion-bg border border-companion-border rounded-xl resize-none focus:outline-none focus:border-primary-500 min-h-[48px] max-h-[200px]"
                rows={1}
                disabled={isLoading}
              />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="px-4 py-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </form>
        </div>
      </div>

      {/* Side Panels */}
      {showResearchPanel && <ResearchPanel />}
      {showControlPanel && <ControlPanel />}
    </div>
  )
}
