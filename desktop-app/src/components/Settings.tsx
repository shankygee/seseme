import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../stores/appStore';
import { useAgent } from '../hooks/useTauri';
import type { LlmProvider, SttProvider } from '../types';

const Settings: React.FC = () => {
  const { showSettings, setShowSettings, apiConfig, setApiConfig } = useAppStore();
  const { setApiConfiguration } = useAgent();

  const [localConfig, setLocalConfig] = useState(apiConfig);

  const handleSave = useCallback(async () => {
    await setApiConfiguration(localConfig);
    setShowSettings(false);
  }, [localConfig, setApiConfiguration, setShowSettings]);

  const updateConfig = useCallback((key: keyof typeof localConfig, value: string | LlmProvider | SttProvider) => {
    setLocalConfig((prev) => ({ ...prev, [key]: value }));
  }, []);

  if (!showSettings) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="settings-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={() => setShowSettings(false)}
      >
        <style>{`
          .settings-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 100;
          }

          .settings-panel {
            background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 16px;
            padding: 24px;
            width: 90%;
            max-width: 400px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
          }

          .settings-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
          }

          .settings-title {
            font-size: 20px;
            font-weight: 600;
            color: #fff;
          }

          .close-btn {
            background: transparent;
            border: none;
            color: rgba(255,255,255,0.6);
            cursor: pointer;
            font-size: 24px;
            padding: 0;
            line-height: 1;
          }

          .settings-section {
            margin-bottom: 24px;
          }

          .section-title {
            font-size: 14px;
            font-weight: 500;
            color: rgba(255,255,255,0.5);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
          }

          .form-group {
            margin-bottom: 16px;
          }

          .form-label {
            display: block;
            font-size: 14px;
            color: rgba(255,255,255,0.8);
            margin-bottom: 6px;
          }

          .form-input {
            width: 100%;
            padding: 10px 12px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
            outline: none;
            transition: all 0.2s;
          }

          .form-input:focus {
            border-color: #667eea;
            background: rgba(255,255,255,0.15);
          }

          .form-input::placeholder {
            color: rgba(255,255,255,0.3);
          }

          .form-select {
            width: 100%;
            padding: 10px 12px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
            outline: none;
            cursor: pointer;
          }

          .form-select option {
            background: #1a1a2e;
            color: #fff;
          }

          .provider-buttons {
            display: flex;
            gap: 8px;
          }

          .provider-btn {
            flex: 1;
            padding: 10px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: transparent;
            color: rgba(255,255,255,0.7);
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
          }

          .provider-btn.active {
            background: rgba(102, 126, 234, 0.2);
            border-color: #667eea;
            color: #fff;
          }

          .provider-btn:hover:not(.active) {
            background: rgba(255,255,255,0.05);
          }

          .save-btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 8px;
            color: #fff;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
          }

          .save-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
          }

          .hint-text {
            font-size: 12px;
            color: rgba(255,255,255,0.4);
            margin-top: 4px;
          }
        `}</style>

        <motion.div
          className="settings-panel"
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.9, y: 20 }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="settings-header">
            <div className="settings-title">Settings</div>
            <button className="close-btn" onClick={() => setShowSettings(false)}>
              ×
            </button>
          </div>

          {/* LLM Provider */}
          <div className="settings-section">
            <div className="section-title">AI Model</div>
            <div className="form-group">
              <label className="form-label">Provider</label>
              <div className="provider-buttons">
                <button
                  className={`provider-btn ${localConfig.llm_provider === 'Anthropic' ? 'active' : ''}`}
                  onClick={() => updateConfig('llm_provider', 'Anthropic')}
                >
                  Claude
                </button>
                <button
                  className={`provider-btn ${localConfig.llm_provider === 'OpenAI' ? 'active' : ''}`}
                  onClick={() => updateConfig('llm_provider', 'OpenAI')}
                >
                  GPT-4
                </button>
              </div>
            </div>
          </div>

          {/* API Keys */}
          <div className="settings-section">
            <div className="section-title">API Keys</div>

            {localConfig.llm_provider === 'Anthropic' && (
              <div className="form-group">
                <label className="form-label">Anthropic API Key</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="sk-ant-..."
                  value={localConfig.anthropic_api_key || ''}
                  onChange={(e) => updateConfig('anthropic_api_key', e.target.value)}
                />
                <div className="hint-text">Get your key from console.anthropic.com</div>
              </div>
            )}

            {localConfig.llm_provider === 'OpenAI' && (
              <div className="form-group">
                <label className="form-label">OpenAI API Key</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="sk-..."
                  value={localConfig.openai_api_key || ''}
                  onChange={(e) => updateConfig('openai_api_key', e.target.value)}
                />
                <div className="hint-text">Get your key from platform.openai.com</div>
              </div>
            )}

            {/* STT API Key (OpenAI for Whisper) */}
            {!localConfig.openai_api_key && localConfig.stt_provider === 'Whisper' && (
              <div className="form-group">
                <label className="form-label">OpenAI API Key (for Whisper STT)</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="sk-..."
                  value={localConfig.openai_api_key || ''}
                  onChange={(e) => updateConfig('openai_api_key', e.target.value)}
                />
              </div>
            )}

            {localConfig.stt_provider === 'Groq' && (
              <div className="form-group">
                <label className="form-label">Groq API Key</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="gsk_..."
                  value={localConfig.groq_api_key || ''}
                  onChange={(e) => updateConfig('groq_api_key', e.target.value)}
                />
                <div className="hint-text">Get your key from console.groq.com</div>
              </div>
            )}
          </div>

          {/* STT Provider */}
          <div className="settings-section">
            <div className="section-title">Speech Recognition</div>
            <div className="form-group">
              <label className="form-label">Provider</label>
              <div className="provider-buttons">
                <button
                  className={`provider-btn ${localConfig.stt_provider === 'Whisper' ? 'active' : ''}`}
                  onClick={() => updateConfig('stt_provider', 'Whisper')}
                >
                  Whisper
                </button>
                <button
                  className={`provider-btn ${localConfig.stt_provider === 'Groq' ? 'active' : ''}`}
                  onClick={() => updateConfig('stt_provider', 'Groq')}
                >
                  Groq
                </button>
              </div>
              <div className="hint-text">
                {localConfig.stt_provider === 'Groq'
                  ? 'Faster transcription, requires Groq API key'
                  : 'Uses OpenAI Whisper API'}
              </div>
            </div>
          </div>

          {/* TTS Server */}
          <div className="settings-section">
            <div className="section-title">Voice Output (TTS)</div>
            <div className="form-group">
              <label className="form-label">Sesame CSM Server URL</label>
              <input
                type="text"
                className="form-input"
                placeholder="http://localhost:8000"
                value={localConfig.csm_server_url || ''}
                onChange={(e) => updateConfig('csm_server_url', e.target.value)}
              />
              <div className="hint-text">
                Leave empty to use browser speech synthesis (less natural)
              </div>
            </div>
          </div>

          <button className="save-btn" onClick={handleSave}>
            Save Settings
          </button>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default Settings;
