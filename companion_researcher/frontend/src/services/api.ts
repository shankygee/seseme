/**
 * API service for Companion Researcher backend
 */

const API_BASE = '/api'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  metadata?: Record<string, unknown>
}

export interface Personality {
  id: string
  name: string
  description: string
  system_prompt: string
  settings: {
    tone: string
    tone_scale: number
    depth: string
    depth_scale: number
    critical_vs_supportive: string
    critical_scale: number
    speed: string
    speed_scale: number
    verbosity: string
    formality: string
    humor: string
  }
  voice: {
    enabled: boolean
    speaker_id: number
  }
  guardrails: {
    avoid_topics: string[]
    always_cite_sources: boolean
    show_confidence: boolean
    max_response_length: number | null
  }
  research_preferences: {
    preferred_source_types: string[]
    source_weights: Record<string, number>
    default_depth: string
  }
}

export interface Source {
  id: string
  url: string
  title: string
  snippet: string
  source_type: string
  reliability_score: number
}

export interface ResearchResult {
  task_id: string
  query: string
  sources: Source[]
  summary: string
  synthesis: string
  confidence_score: number
  citations: Array<{ title: string; url: string; type: string }>
}

export interface ChatResponse {
  response: string
  session_id: string
  message_id: string
  is_research_response: boolean
  research_result?: ResearchResult
  audio_url?: string
  metadata: Record<string, unknown>
}

export interface Session {
  id: string
  personality_id: string
  messages: Message[]
  tags: string[]
  created_at: string
  updated_at: string
}

export interface SessionSummary {
  id: string
  personality_id: string
  message_count: number
  preview: string
  tags: string[]
  created_at: string
  updated_at: string
}

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || `API error: ${response.status}`)
    }

    return response.json()
  }

  // Chat
  async sendMessage(
    message: string,
    personalityId: string = 'default',
    sessionId?: string,
    researchDepth?: string
  ): Promise<ChatResponse> {
    return this.request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        personality_id: personalityId,
        session_id: sessionId,
        research_depth: researchDepth,
      }),
    })
  }

  // Research
  async research(
    query: string,
    depth: string = 'medium',
    maxSources: number = 5
  ): Promise<ResearchResult> {
    return this.request<ResearchResult>('/research', {
      method: 'POST',
      body: JSON.stringify({
        query,
        depth,
        max_sources: maxSources,
      }),
    })
  }

  // Personalities
  async listPersonalities(): Promise<Personality[]> {
    return this.request<Personality[]>('/personalities')
  }

  async getPersonality(id: string): Promise<Personality> {
    return this.request<Personality>(`/personalities/${id}`)
  }

  async updatePersonality(
    id: string,
    updates: Partial<Personality>
  ): Promise<Personality> {
    return this.request<Personality>(`/personalities/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    })
  }

  async activatePersonality(id: string): Promise<void> {
    await this.request(`/personalities/${id}/activate`, {
      method: 'POST',
    })
  }

  async getActivePersonality(): Promise<Personality> {
    return this.request<Personality>('/personalities/active')
  }

  // Sessions
  async listSessions(): Promise<SessionSummary[]> {
    return this.request<SessionSummary[]>('/sessions')
  }

  async getSession(id: string): Promise<Session> {
    return this.request<Session>(`/sessions/${id}`)
  }

  async deleteSession(id: string): Promise<void> {
    await this.request(`/sessions/${id}`, { method: 'DELETE' })
  }

  // Voice
  async generateVoice(text: string, speakerId: number = 0): Promise<Blob> {
    const response = await fetch(
      `${API_BASE}/voice/generate?text=${encodeURIComponent(text)}&speaker_id=${speakerId}`,
      { method: 'POST' }
    )
    if (!response.ok) {
      throw new Error('Voice generation failed')
    }
    return response.blob()
  }

  // Health
  async healthCheck(): Promise<{ status: string; version: string }> {
    return this.request('/health')
  }
}

export const api = new ApiService()
export default api
