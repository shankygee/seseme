import React, { useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../stores/appStore';
import { usePermissions, useScreenCapture, useAgent, useTauriEvents } from '../hooks/useTauri';
import { useVoiceCapture } from '../hooks/useVoiceCapture';

// Icons as simple SVG components
const MicIcon = ({ active }: { active: boolean }) => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill={active ? '#22c55e' : 'currentColor'}>
    <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3z" />
    <path d="M19 10v1a7 7 0 0 1-14 0v-1" stroke={active ? '#22c55e' : 'currentColor'} strokeWidth="2" fill="none" />
    <line x1="12" y1="19" x2="12" y2="23" stroke="currentColor" strokeWidth="2" />
    <line x1="8" y1="23" x2="16" y2="23" stroke="currentColor" strokeWidth="2" />
  </svg>
);

const StopIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
    <rect x="6" y="6" width="12" height="12" rx="2" />
  </svg>
);

const SettingsIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="3" />
    <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
  </svg>
);

const ScreenIcon = ({ active }: { active: boolean }) => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={active ? '#22c55e' : 'currentColor'} strokeWidth="2">
    <rect x="2" y="3" width="20" height="14" rx="2" />
    <line x1="8" y1="21" x2="16" y2="21" />
    <line x1="12" y1="17" x2="12" y2="21" />
  </svg>
);

const ControlPanel: React.FC = () => {
  const {
    status,
    setStatus,
    permissions,
    isCapturing,
    agentHasControl,
    conversation,
    addTurn,
    showSettings,
    setShowSettings,
    error,
    setError,
    apiConfig,
  } = useAppStore();

  const { checkPermissions, requestPermission } = usePermissions();
  const { startCapture, stopCapture, captureFrame } = useScreenCapture();
  const { sendMessage, interrupt } = useAgent();
  const captureIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Set up Tauri event listeners
  useTauriEvents();

  // Voice capture with auto transcription
  const { isRecording, audioLevel, isSpeaking, startRecording, stopRecording } = useVoiceCapture({
    onSpeechStart: () => {
      setStatus('listening');
    },
    onTranscription: async (text) => {
      // Add user message to conversation
      addTurn({ role: 'user', text });

      // Capture current screen
      const frame = await captureFrame(0.5, 70);

      // Send to agent
      const response = await sendMessage({
        text,
        screen_frame: frame?.data,
        cursor_position: frame ? [frame.cursor_x, frame.cursor_y] : undefined,
        active_window: frame?.active_window ?? undefined,
      });

      if (response?.speech) {
        setStatus('speaking');
        // TTS will be handled by the Rust backend
      } else {
        setStatus('idle');
      }
    },
  });

  // Check permissions on mount
  useEffect(() => {
    checkPermissions();
  }, [checkPermissions]);

  // Start/stop screen capture loop
  useEffect(() => {
    if (isCapturing) {
      captureIntervalRef.current = setInterval(async () => {
        await captureFrame(0.5, 60);
      }, 200); // 5 FPS
    } else if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }

    return () => {
      if (captureIntervalRef.current) {
        clearInterval(captureIntervalRef.current);
      }
    };
  }, [isCapturing, captureFrame]);

  const toggleScreenShare = useCallback(async () => {
    if (isCapturing) {
      await stopCapture();
    } else {
      await startCapture();
    }
  }, [isCapturing, startCapture, stopCapture]);

  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  const handleInterrupt = useCallback(async () => {
    await interrupt();
    stopRecording();
  }, [interrupt, stopRecording]);

  // Status indicator colors
  const statusColors: Record<string, string> = {
    idle: '#6b7280',
    listening: '#22c55e',
    thinking: '#eab308',
    speaking: '#3b82f6',
    acting: '#8b5cf6',
    error: '#ef4444',
  };

  // Check if we have required API keys
  const hasRequiredKeys = apiConfig.llm_provider === 'Anthropic'
    ? !!apiConfig.anthropic_api_key
    : !!apiConfig.openai_api_key;

  return (
    <div className="control-panel">
      <style>{`
        .control-panel {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
          color: #fff;
          padding: 16px;
        }

        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding-bottom: 16px;
          border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        .title {
          font-size: 18px;
          font-weight: 600;
        }

        .status-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          margin-right: 8px;
        }

        .status-container {
          display: flex;
          align-items: center;
          font-size: 12px;
          color: rgba(255,255,255,0.7);
          text-transform: capitalize;
        }

        .settings-btn {
          background: transparent;
          border: none;
          color: rgba(255,255,255,0.6);
          cursor: pointer;
          padding: 4px;
          border-radius: 4px;
          transition: all 0.2s;
        }

        .settings-btn:hover {
          background: rgba(255,255,255,0.1);
          color: #fff;
        }

        .main-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          padding: 24px 0;
        }

        .mic-button {
          width: 80px;
          height: 80px;
          border-radius: 50%;
          border: none;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: #fff;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
          transition: all 0.2s;
        }

        .mic-button:hover {
          transform: scale(1.05);
        }

        .mic-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .mic-button.recording {
          background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
          box-shadow: 0 4px 20px rgba(34, 197, 94, 0.4);
        }

        .audio-level {
          width: 120px;
          height: 4px;
          background: rgba(255,255,255,0.1);
          border-radius: 2px;
          margin-top: 16px;
          overflow: hidden;
        }

        .audio-level-bar {
          height: 100%;
          background: #22c55e;
          border-radius: 2px;
          transition: width 0.1s;
        }

        .conversation {
          flex: 1;
          overflow-y: auto;
          padding: 16px 0;
          max-height: 200px;
        }

        .message {
          padding: 8px 12px;
          margin-bottom: 8px;
          border-radius: 8px;
          font-size: 14px;
        }

        .message.user {
          background: rgba(255,255,255,0.1);
          margin-left: 20%;
        }

        .message.agent {
          background: rgba(102, 126, 234, 0.2);
          margin-right: 20%;
        }

        .controls {
          display: flex;
          gap: 12px;
          padding-top: 16px;
          border-top: 1px solid rgba(255,255,255,0.1);
        }

        .control-btn {
          flex: 1;
          padding: 12px;
          border: none;
          border-radius: 8px;
          background: rgba(255,255,255,0.1);
          color: #fff;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          font-size: 14px;
          transition: all 0.2s;
        }

        .control-btn:hover {
          background: rgba(255,255,255,0.2);
        }

        .control-btn.active {
          background: rgba(34, 197, 94, 0.2);
        }

        .control-btn.danger {
          background: rgba(239, 68, 68, 0.2);
        }

        .control-btn.danger:hover {
          background: rgba(239, 68, 68, 0.3);
        }

        .permission-warning {
          padding: 12px;
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 8px;
          font-size: 12px;
          color: #fca5a5;
          margin-bottom: 16px;
        }

        .permission-warning button {
          margin-top: 8px;
          padding: 6px 12px;
          background: rgba(239, 68, 68, 0.2);
          border: 1px solid rgba(239, 68, 68, 0.4);
          border-radius: 4px;
          color: #fff;
          cursor: pointer;
          font-size: 12px;
        }

        .agent-control-indicator {
          position: fixed;
          top: 8px;
          left: 50%;
          transform: translateX(-50%);
          padding: 6px 16px;
          background: rgba(139, 92, 246, 0.9);
          border-radius: 16px;
          font-size: 12px;
          font-weight: 500;
          display: flex;
          align-items: center;
          gap: 8px;
          z-index: 1000;
        }

        .error-toast {
          position: fixed;
          bottom: 16px;
          left: 50%;
          transform: translateX(-50%);
          padding: 12px 20px;
          background: rgba(239, 68, 68, 0.9);
          border-radius: 8px;
          font-size: 14px;
          max-width: 80%;
          z-index: 1000;
        }

        .no-api-key {
          text-align: center;
          padding: 20px;
          color: rgba(255,255,255,0.7);
          font-size: 14px;
        }

        .no-api-key button {
          margin-top: 12px;
          padding: 8px 16px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border: none;
          border-radius: 6px;
          color: #fff;
          cursor: pointer;
        }
      `}</style>

      {/* Header */}
      <div className="header">
        <div>
          <div className="title">Live Agent</div>
          <div className="status-container">
            <motion.div
              className="status-dot"
              style={{ backgroundColor: statusColors[status] }}
              animate={{ scale: status === 'listening' ? [1, 1.2, 1] : 1 }}
              transition={{ repeat: status === 'listening' ? Infinity : 0, duration: 1 }}
            />
            {status}
          </div>
        </div>
        <button className="settings-btn" onClick={() => setShowSettings(!showSettings)}>
          <SettingsIcon />
        </button>
      </div>

      {/* Agent control indicator */}
      <AnimatePresence>
        {agentHasControl && (
          <motion.div
            className="agent-control-indicator"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ repeat: Infinity, duration: 1.5 }}
              style={{ width: 8, height: 8, borderRadius: '50%', background: '#fff' }}
            />
            Agent is controlling
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main content */}
      <div className="main-content">
        {/* Permission warnings */}
        {permissions && permissions.screen_capture !== 'Granted' && (
          <div className="permission-warning">
            Screen capture permission required
            <button onClick={() => requestPermission('screen_capture')}>Grant Access</button>
          </div>
        )}

        {permissions && permissions.microphone !== 'Granted' && (
          <div className="permission-warning">
            Microphone permission required
            <button onClick={() => requestPermission('microphone')}>Grant Access</button>
          </div>
        )}

        {!hasRequiredKeys && (
          <div className="no-api-key">
            <p>Configure your API keys to get started</p>
            <button onClick={() => setShowSettings(true)}>Open Settings</button>
          </div>
        )}

        {hasRequiredKeys && (
          <>
            {/* Mic button */}
            <motion.button
              className={`mic-button ${isRecording ? 'recording' : ''}`}
              onClick={toggleRecording}
              whileTap={{ scale: 0.95 }}
              disabled={!isCapturing}
            >
              <MicIcon active={isRecording} />
            </motion.button>

            {/* Audio level indicator */}
            <div className="audio-level">
              <motion.div
                className="audio-level-bar"
                style={{ width: `${audioLevel * 100}%` }}
              />
            </div>

            {/* Conversation */}
            {conversation.length > 0 && (
              <div className="conversation">
                {conversation.slice(-5).map((turn, i) => (
                  <motion.div
                    key={turn.timestamp}
                    className={`message ${turn.role}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                  >
                    {turn.text}
                  </motion.div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Bottom controls */}
      <div className="controls">
        <button
          className={`control-btn ${isCapturing ? 'active' : ''}`}
          onClick={toggleScreenShare}
        >
          <ScreenIcon active={isCapturing} />
          {isCapturing ? 'Stop Share' : 'Share Screen'}
        </button>

        {(isRecording || status === 'speaking' || status === 'acting') && (
          <motion.button
            className="control-btn danger"
            onClick={handleInterrupt}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <StopIcon />
            Stop
          </motion.button>
        )}
      </div>

      {/* Error toast */}
      <AnimatePresence>
        {error && (
          <motion.div
            className="error-toast"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            onClick={() => setError(null)}
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ControlPanel;
