/**
 * Custom hook for chat functionality
 */
import { useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api, type Message } from '../services/api'
import { useStore } from './useStore'

export function useChat() {
  const {
    messages,
    sessionId,
    isLoading,
    error,
    activePersonality,
    addMessage,
    setSessionId,
    setLoading,
    setError,
    setCurrentResearchResult,
  } = useStore()

  const sendMessageMutation = useMutation({
    mutationFn: async (content: string) => {
      const response = await api.sendMessage(
        content,
        activePersonality?.id || 'default',
        sessionId || undefined
      )
      return response
    },
    onMutate: (content) => {
      // Optimistically add user message
      const userMessage: Message = {
        id: `temp-${Date.now()}`,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      }
      addMessage(userMessage)
      setLoading(true)
      setError(null)
    },
    onSuccess: (response) => {
      // Update session ID if new
      if (!sessionId) {
        setSessionId(response.session_id)
      }

      // Add assistant message
      const assistantMessage: Message = {
        id: response.message_id,
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString(),
        metadata: response.metadata,
      }
      addMessage(assistantMessage)

      // Handle research result
      if (response.is_research_response && response.research_result) {
        setCurrentResearchResult(response.research_result)
      }

      setLoading(false)
    },
    onError: (error: Error) => {
      setError(error.message)
      setLoading(false)
    },
  })

  const sendMessage = useCallback(
    (content: string) => {
      if (content.trim() && !isLoading) {
        sendMessageMutation.mutate(content)
      }
    },
    [isLoading, sendMessageMutation]
  )

  return {
    messages,
    sessionId,
    isLoading,
    error,
    sendMessage,
  }
}

export default useChat
