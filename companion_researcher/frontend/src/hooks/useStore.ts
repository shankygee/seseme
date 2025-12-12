/**
 * Global state management using Zustand
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Message, Personality, ResearchResult } from '../services/api'

interface ChatState {
  messages: Message[]
  sessionId: string | null
  isLoading: boolean
  error: string | null
}

interface PersonalityState {
  activePersonality: Personality | null
  personalities: Personality[]
}

interface UIState {
  showResearchPanel: boolean
  showControlPanel: boolean
  showSessionsPanel: boolean
  currentResearchResult: ResearchResult | null
}

interface AppState extends ChatState, PersonalityState, UIState {
  // Chat actions
  addMessage: (message: Message) => void
  setMessages: (messages: Message[]) => void
  clearMessages: () => void
  setSessionId: (id: string | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void

  // Personality actions
  setActivePersonality: (personality: Personality) => void
  setPersonalities: (personalities: Personality[]) => void
  updatePersonalitySettings: (settings: Partial<Personality['settings']>) => void

  // UI actions
  toggleResearchPanel: () => void
  toggleControlPanel: () => void
  toggleSessionsPanel: () => void
  setCurrentResearchResult: (result: ResearchResult | null) => void
  closeAllPanels: () => void
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Initial state
      messages: [],
      sessionId: null,
      isLoading: false,
      error: null,
      activePersonality: null,
      personalities: [],
      showResearchPanel: false,
      showControlPanel: false,
      showSessionsPanel: false,
      currentResearchResult: null,

      // Chat actions
      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message],
        })),

      setMessages: (messages) => set({ messages }),

      clearMessages: () => set({ messages: [], sessionId: null }),

      setSessionId: (id) => set({ sessionId: id }),

      setLoading: (loading) => set({ isLoading: loading }),

      setError: (error) => set({ error }),

      // Personality actions
      setActivePersonality: (personality) =>
        set({ activePersonality: personality }),

      setPersonalities: (personalities) => set({ personalities }),

      updatePersonalitySettings: (settings) =>
        set((state) => ({
          activePersonality: state.activePersonality
            ? {
                ...state.activePersonality,
                settings: { ...state.activePersonality.settings, ...settings },
              }
            : null,
        })),

      // UI actions
      toggleResearchPanel: () =>
        set((state) => ({
          showResearchPanel: !state.showResearchPanel,
          showControlPanel: false,
          showSessionsPanel: false,
        })),

      toggleControlPanel: () =>
        set((state) => ({
          showControlPanel: !state.showControlPanel,
          showResearchPanel: false,
          showSessionsPanel: false,
        })),

      toggleSessionsPanel: () =>
        set((state) => ({
          showSessionsPanel: !state.showSessionsPanel,
          showResearchPanel: false,
          showControlPanel: false,
        })),

      setCurrentResearchResult: (result) =>
        set({
          currentResearchResult: result,
          showResearchPanel: result !== null,
        }),

      closeAllPanels: () =>
        set({
          showResearchPanel: false,
          showControlPanel: false,
          showSessionsPanel: false,
        }),
    }),
    {
      name: 'companion-researcher-storage',
      partialize: (state) => ({
        sessionId: state.sessionId,
        activePersonality: state.activePersonality
          ? { id: state.activePersonality.id }
          : null,
      }),
    }
  )
)

export default useStore
