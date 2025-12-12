import { useState } from 'react'
import { X, Save } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { useStore } from '../hooks/useStore'
import clsx from 'clsx'

interface SliderProps {
  label: string
  leftLabel: string
  rightLabel: string
  value: number
  onChange: (value: number) => void
}

function Slider({ label, leftLabel, rightLabel, value, onChange }: SliderProps) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-companion-text">{label}</span>
        <span className="text-companion-muted">{value}%</span>
      </div>
      <input
        type="range"
        min="0"
        max="100"
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="w-full"
      />
      <div className="flex justify-between text-xs text-companion-muted">
        <span>{leftLabel}</span>
        <span>{rightLabel}</span>
      </div>
    </div>
  )
}

export default function ControlPanel() {
  const queryClient = useQueryClient()
  const {
    activePersonality,
    personalities,
    setActivePersonality,
    toggleControlPanel,
    updatePersonalitySettings,
  } = useStore()

  const [localSettings, setLocalSettings] = useState(
    activePersonality?.settings || {
      tone_scale: 50,
      depth_scale: 50,
      critical_scale: 50,
      speed_scale: 50,
    }
  )

  const activateMutation = useMutation({
    mutationFn: (id: string) => api.activatePersonality(id),
    onSuccess: async (_, id) => {
      const personality = personalities.find((p) => p.id === id)
      if (personality) {
        setActivePersonality(personality)
        setLocalSettings(personality.settings)
      }
    },
  })

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updatePersonality(activePersonality!.id, { settings: localSettings }),
    onSuccess: () => {
      updatePersonalitySettings(localSettings)
      queryClient.invalidateQueries({ queryKey: ['personalities'] })
    },
  })

  const handleSliderChange = (key: string, value: number) => {
    setLocalSettings((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="w-80 border-l border-companion-border bg-companion-surface flex flex-col">
      {/* Header */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-companion-border">
        <h2 className="font-semibold">Control Panel</h2>
        <button
          onClick={toggleControlPanel}
          className="p-1.5 rounded-lg hover:bg-companion-border transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Personality Selector */}
        <div>
          <label className="block text-sm font-medium mb-2">Personality</label>
          <div className="grid grid-cols-2 gap-2">
            {personalities.map((personality) => (
              <button
                key={personality.id}
                onClick={() => activateMutation.mutate(personality.id)}
                className={clsx(
                  'p-3 rounded-lg text-left transition-all border',
                  activePersonality?.id === personality.id
                    ? 'border-primary-500 bg-primary-500/10'
                    : 'border-companion-border hover:border-companion-muted'
                )}
              >
                <div className="font-medium text-sm truncate">
                  {personality.name}
                </div>
                <div className="text-xs text-companion-muted truncate">
                  {personality.description}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Sliders */}
        <div className="space-y-6">
          <h3 className="font-medium text-sm text-companion-muted uppercase tracking-wide">
            Style Adjustments
          </h3>

          <Slider
            label="Tone"
            leftLabel="Serious"
            rightLabel="Playful"
            value={localSettings.tone_scale}
            onChange={(v) => handleSliderChange('tone_scale', v)}
          />

          <Slider
            label="Depth"
            leftLabel="Brief"
            rightLabel="Comprehensive"
            value={localSettings.depth_scale}
            onChange={(v) => handleSliderChange('depth_scale', v)}
          />

          <Slider
            label="Approach"
            leftLabel="Critical"
            rightLabel="Supportive"
            value={localSettings.critical_scale}
            onChange={(v) => handleSliderChange('critical_scale', v)}
          />

          <Slider
            label="Speed"
            leftLabel="Fast Answer"
            rightLabel="Thorough"
            value={localSettings.speed_scale}
            onChange={(v) => handleSliderChange('speed_scale', v)}
          />
        </div>

        {/* Research Preferences */}
        <div className="space-y-4">
          <h3 className="font-medium text-sm text-companion-muted uppercase tracking-wide">
            Research Preferences
          </h3>

          <div>
            <label className="block text-sm mb-2">Default Depth</label>
            <select
              value={activePersonality?.research_preferences.default_depth}
              className="w-full px-3 py-2 bg-companion-bg border border-companion-border rounded-lg focus:outline-none focus:border-primary-500"
              onChange={() => {}}
            >
              <option value="quick">Quick Scan</option>
              <option value="medium">Balanced</option>
              <option value="deep">Deep Dive</option>
            </select>
          </div>

          <div>
            <label className="block text-sm mb-2">Source Types</label>
            <div className="space-y-2">
              {['academic', 'news', 'blogs', 'documentation'].map((source) => (
                <label
                  key={source}
                  className="flex items-center gap-2 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    defaultChecked={activePersonality?.research_preferences.preferred_source_types.includes(
                      source
                    )}
                    className="rounded border-companion-border bg-companion-bg"
                  />
                  <span className="text-sm capitalize">{source}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Guardrails */}
        <div className="space-y-4">
          <h3 className="font-medium text-sm text-companion-muted uppercase tracking-wide">
            Guardrails
          </h3>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              defaultChecked={activePersonality?.guardrails.always_cite_sources}
              className="rounded border-companion-border bg-companion-bg"
            />
            <span className="text-sm">Always cite sources</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              defaultChecked={activePersonality?.guardrails.show_confidence}
              className="rounded border-companion-border bg-companion-bg"
            />
            <span className="text-sm">Show confidence scores</span>
          </label>
        </div>
      </div>

      {/* Save Button */}
      <div className="p-4 border-t border-companion-border">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="w-full py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
        >
          <Save className="w-4 h-4" />
          {saveMutation.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </div>
  )
}
