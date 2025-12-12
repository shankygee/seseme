import { X, MessageSquare, Trash2, Plus } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type SessionSummary } from '../services/api'
import { useStore } from '../hooks/useStore'
import clsx from 'clsx'

export default function SessionsPanel() {
  const queryClient = useQueryClient()
  const {
    sessionId,
    toggleSessionsPanel,
    setSessionId,
    clearMessages,
  } = useStore()

  const { data: sessions, isLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => api.listSessions(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteSession(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })

  const loadSession = async (session: SessionSummary) => {
    try {
      const fullSession = await api.getSession(session.id)
      setSessionId(fullSession.id)
      useStore.getState().setMessages(fullSession.messages)
    } catch (error) {
      console.error('Failed to load session:', error)
    }
  }

  const startNewSession = () => {
    clearMessages()
    toggleSessionsPanel()
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffDays = Math.floor(
      (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
    )

    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="w-72 border-r border-companion-border bg-companion-surface flex flex-col">
      {/* Header */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-companion-border">
        <h2 className="font-semibold">Sessions</h2>
        <button
          onClick={toggleSessionsPanel}
          className="p-1.5 rounded-lg hover:bg-companion-border transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* New Session Button */}
      <div className="p-3 border-b border-companion-border">
        <button
          onClick={startNewSession}
          className="w-full py-2.5 flex items-center justify-center gap-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Session
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 text-center text-companion-muted">
            Loading sessions...
          </div>
        ) : !sessions || sessions.length === 0 ? (
          <div className="p-4 text-center text-companion-muted">
            <MessageSquare className="w-10 h-10 mx-auto mb-2 opacity-50" />
            <p>No previous sessions</p>
            <p className="text-xs mt-1">Start a conversation to create one</p>
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={clsx(
                  'group p-3 rounded-lg cursor-pointer transition-colors',
                  session.id === sessionId
                    ? 'bg-primary-600/20 border border-primary-500/50'
                    : 'hover:bg-companion-border'
                )}
                onClick={() => loadSession(session)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">
                      {session.preview || 'Untitled conversation'}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-companion-muted">
                        {formatDate(session.updated_at)}
                      </span>
                      <span className="text-xs text-companion-muted">
                        {session.message_count} messages
                      </span>
                    </div>
                    {session.tags.length > 0 && (
                      <div className="flex gap-1 mt-1.5 flex-wrap">
                        {session.tags.slice(0, 3).map((tag) => (
                          <span
                            key={tag}
                            className="text-xs px-1.5 py-0.5 bg-companion-border rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      deleteMutation.mutate(session.id)
                    }}
                    className="p-1.5 rounded opacity-0 group-hover:opacity-100 hover:bg-red-500/20 hover:text-red-400 transition-all"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
