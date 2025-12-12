import { useState } from 'react'
import { Save, Plus, Trash2 } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type Personality } from '../services/api'
import { useStore } from '../hooks/useStore'
import clsx from 'clsx'

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const { activePersonality, setActivePersonality } = useStore()
  const [selectedPersonalityId, setSelectedPersonalityId] = useState<string | null>(
    activePersonality?.id || null
  )
  const [editedPrompt, setEditedPrompt] = useState('')

  const { data: personalities } = useQuery({
    queryKey: ['personalities'],
    queryFn: () => api.listPersonalities(),
  })

  const selectedPersonality = personalities?.find(
    (p) => p.id === selectedPersonalityId
  )

  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: Partial<Personality> }) =>
      api.updatePersonality(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['personalities'] })
    },
  })

  const handleSelectPersonality = (personality: Personality) => {
    setSelectedPersonalityId(personality.id)
    setEditedPrompt(personality.system_prompt)
  }

  const handleSavePrompt = () => {
    if (selectedPersonalityId && editedPrompt) {
      updateMutation.mutate({
        id: selectedPersonalityId,
        updates: { system_prompt: editedPrompt },
      })
    }
  }

  return (
    <div className="flex-1 flex">
      {/* Personality List */}
      <div className="w-72 border-r border-companion-border bg-companion-surface flex flex-col">
        <div className="h-14 px-4 flex items-center border-b border-companion-border">
          <h2 className="font-semibold">Personalities</h2>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {personalities?.map((personality) => (
            <button
              key={personality.id}
              onClick={() => handleSelectPersonality(personality)}
              className={clsx(
                'w-full p-3 rounded-lg text-left transition-colors mb-1',
                selectedPersonalityId === personality.id
                  ? 'bg-primary-600/20 border border-primary-500/50'
                  : 'hover:bg-companion-border'
              )}
            >
              <div className="font-medium">{personality.name}</div>
              <div className="text-xs text-companion-muted mt-0.5 line-clamp-2">
                {personality.description}
              </div>
            </button>
          ))}
        </div>

        <div className="p-3 border-t border-companion-border">
          <button className="w-full py-2.5 flex items-center justify-center gap-2 border border-companion-border rounded-lg hover:bg-companion-border transition-colors">
            <Plus className="w-4 h-4" />
            New Personality
          </button>
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 flex flex-col">
        {selectedPersonality ? (
          <>
            {/* Header */}
            <div className="h-14 px-6 flex items-center justify-between border-b border-companion-border bg-companion-surface">
              <div>
                <h1 className="font-semibold">{selectedPersonality.name}</h1>
                <p className="text-xs text-companion-muted">
                  {selectedPersonality.description}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSavePrompt}
                  disabled={updateMutation.isPending}
                  className="px-4 py-2 flex items-center gap-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
                >
                  <Save className="w-4 h-4" />
                  {updateMutation.isPending ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* System Prompt */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  System Prompt
                </label>
                <textarea
                  value={editedPrompt}
                  onChange={(e) => setEditedPrompt(e.target.value)}
                  className="w-full h-48 px-4 py-3 bg-companion-bg border border-companion-border rounded-lg resize-none focus:outline-none focus:border-primary-500 font-mono text-sm"
                  placeholder="Enter the system prompt for this personality..."
                />
                <p className="text-xs text-companion-muted mt-1">
                  This defines the base behavior and personality of the companion.
                </p>
              </div>

              {/* Quick Settings */}
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Verbosity
                  </label>
                  <select
                    value={selectedPersonality.settings.verbosity}
                    className="w-full px-3 py-2 bg-companion-bg border border-companion-border rounded-lg focus:outline-none focus:border-primary-500"
                  >
                    <option value="minimal">Minimal</option>
                    <option value="concise">Concise</option>
                    <option value="medium">Medium</option>
                    <option value="detailed">Detailed</option>
                    <option value="comprehensive">Comprehensive</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Formality
                  </label>
                  <select
                    value={selectedPersonality.settings.formality}
                    className="w-full px-3 py-2 bg-companion-bg border border-companion-border rounded-lg focus:outline-none focus:border-primary-500"
                  >
                    <option value="formal">Formal</option>
                    <option value="professional">Professional</option>
                    <option value="conversational">Conversational</option>
                    <option value="casual">Casual</option>
                    <option value="warm">Warm</option>
                  </select>
                </div>
              </div>

              {/* Guardrails */}
              <div>
                <h3 className="text-sm font-medium mb-3">Guardrails</h3>
                <div className="space-y-3">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      defaultChecked={
                        selectedPersonality.guardrails.always_cite_sources
                      }
                      className="rounded border-companion-border bg-companion-bg"
                    />
                    <span className="text-sm">Always cite sources</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      defaultChecked={
                        selectedPersonality.guardrails.show_confidence
                      }
                      className="rounded border-companion-border bg-companion-bg"
                    />
                    <span className="text-sm">Show confidence scores</span>
                  </label>
                </div>

                <div className="mt-4">
                  <label className="block text-sm mb-2">Topics to Avoid</label>
                  <input
                    type="text"
                    defaultValue={selectedPersonality.guardrails.avoid_topics.join(
                      ', '
                    )}
                    placeholder="Enter comma-separated topics..."
                    className="w-full px-3 py-2 bg-companion-bg border border-companion-border rounded-lg focus:outline-none focus:border-primary-500"
                  />
                </div>
              </div>

              {/* Voice Settings */}
              <div>
                <h3 className="text-sm font-medium mb-3">Voice Settings</h3>
                <label className="flex items-center gap-3 cursor-pointer mb-3">
                  <input
                    type="checkbox"
                    defaultChecked={selectedPersonality.voice.enabled}
                    className="rounded border-companion-border bg-companion-bg"
                  />
                  <span className="text-sm">Enable voice output</span>
                </label>
                <div>
                  <label className="block text-sm mb-2">Speaker ID</label>
                  <input
                    type="number"
                    defaultValue={selectedPersonality.voice.speaker_id}
                    min="0"
                    max="10"
                    className="w-24 px-3 py-2 bg-companion-bg border border-companion-border rounded-lg focus:outline-none focus:border-primary-500"
                  />
                </div>
              </div>

              {/* Danger Zone */}
              {selectedPersonality.id !== 'default' && (
                <div className="p-4 border border-red-500/30 rounded-lg bg-red-500/5">
                  <h3 className="text-sm font-medium text-red-400 mb-2">
                    Danger Zone
                  </h3>
                  <p className="text-xs text-companion-muted mb-3">
                    Permanently delete this personality profile.
                  </p>
                  <button className="px-4 py-2 flex items-center gap-2 border border-red-500/50 text-red-400 rounded-lg hover:bg-red-500/20 transition-colors">
                    <Trash2 className="w-4 h-4" />
                    Delete Personality
                  </button>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-companion-muted">
            Select a personality to edit
          </div>
        )}
      </div>
    </div>
  )
}
