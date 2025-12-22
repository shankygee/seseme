//
//  VoiceAssistant.swift
//  Jarvis
//
//  Core voice assistant logic - recording, API communication, and playback.
//

import Foundation
import AVFoundation
import Combine

/// Main voice assistant controller
class VoiceAssistant: NSObject, ObservableObject {
    // MARK: - Published State

    @Published var isListening = false
    @Published var isProcessing = false
    @Published var isSpeaking = false
    @Published var statusText = "Tap to speak"
    @Published var lastResponse = ""
    @Published var showTextInput = false
    @Published var currentTranscription = ""

    // MARK: - Private Properties

    private var appState: AppState?
    private var audioRecorder: AVAudioRecorder?
    private var audioPlayer: AVAudioPlayer?
    private var recordingURL: URL?
    private var conversationId: String?

    private let audioSession = AVAudioSession.sharedInstance()
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Configuration

    func configure(appState: AppState) {
        self.appState = appState
        setupAudioSession()
    }

    private func setupAudioSession() {
        do {
            try audioSession.setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker, .allowBluetooth])
            try audioSession.setActive(true)
        } catch {
            print("Failed to setup audio session: \(error)")
        }
    }

    // MARK: - Recording

    func startListening() {
        guard !isListening else { return }

        // Request microphone permission if needed
        audioSession.requestRecordPermission { [weak self] granted in
            DispatchQueue.main.async {
                if granted {
                    self?.beginRecording()
                } else {
                    self?.statusText = "Microphone access denied"
                }
            }
        }
    }

    private func beginRecording() {
        // Create temp file for recording
        let tempDir = FileManager.default.temporaryDirectory
        recordingURL = tempDir.appendingPathComponent("jarvis_recording_\(UUID().uuidString).wav")

        guard let url = recordingURL else { return }

        // Audio settings for Whisper compatibility
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatLinearPCM),
            AVSampleRateKey: 16000.0,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsFloatKey: false,
            AVLinearPCMIsBigEndianKey: false
        ]

        do {
            audioRecorder = try AVAudioRecorder(url: url, settings: settings)
            audioRecorder?.delegate = self
            audioRecorder?.record()

            isListening = true
            statusText = "Listening..."
            currentTranscription = ""

            // Add haptic feedback
            let generator = UIImpactFeedbackGenerator(style: .medium)
            generator.impactOccurred()

        } catch {
            print("Failed to start recording: \(error)")
            statusText = "Recording error"
        }
    }

    func stopListening() {
        guard isListening else { return }

        audioRecorder?.stop()
        isListening = false
        statusText = "Processing..."
        isProcessing = true

        // Haptic feedback
        let generator = UIImpactFeedbackGenerator(style: .light)
        generator.impactOccurred()

        // Send to server
        processRecording()
    }

    // MARK: - API Communication

    private func processRecording() {
        guard let url = recordingURL,
              let appState = appState,
              let audioData = try? Data(contentsOf: url) else {
            statusText = "Error reading recording"
            isProcessing = false
            return
        }

        Task {
            await sendVoiceMessage(audioData: audioData, serverURL: appState.serverURL, userId: appState.userId)
        }
    }

    private func sendVoiceMessage(audioData: Data, serverURL: String, userId: String) async {
        let endpoint = "\(serverURL)/api/v1/chat/voice"

        guard let url = URL(string: endpoint) else {
            await MainActor.run {
                statusText = "Invalid server URL"
                isProcessing = false
            }
            return
        }

        // Create multipart form data
        let boundary = UUID().uuidString
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()

        // Add audio file
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"audio\"; filename=\"recording.wav\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: audio/wav\r\n\r\n".data(using: .utf8)!)
        body.append(audioData)
        body.append("\r\n".data(using: .utf8)!)

        // Add user_id
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"user_id\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(userId)\r\n".data(using: .utf8)!)

        // Add conversation_id if exists
        if let convId = conversationId {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"conversation_id\"\r\n\r\n".data(using: .utf8)!)
            body.append("\(convId)\r\n".data(using: .utf8)!)
        }

        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        do {
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }

            let voiceResponse = try JSONDecoder().decode(VoiceResponse.self, from: data)

            await MainActor.run {
                handleResponse(voiceResponse)
            }

        } catch {
            await MainActor.run {
                statusText = "Connection error"
                isProcessing = false
                print("API Error: \(error)")
            }
        }

        // Cleanup recording file
        if let recordingURL = recordingURL {
            try? FileManager.default.removeItem(at: recordingURL)
        }
    }

    private func handleResponse(_ response: VoiceResponse) {
        conversationId = response.conversationId
        lastResponse = response.text
        statusText = "Tap to speak"
        isProcessing = false

        // Decode and play audio
        if let audioData = Data(base64Encoded: response.audioBase64) {
            playAudio(audioData)
        }

        // Show tools used (optional feedback)
        if !response.toolsUsed.isEmpty {
            print("Tools used: \(response.toolsUsed.joined(separator: ", "))")
        }
    }

    // MARK: - Text Input

    func sendTextMessage(_ text: String) {
        guard let appState = appState else { return }

        isProcessing = true
        statusText = "Processing..."

        Task {
            await sendTextRequest(text: text, serverURL: appState.serverURL, userId: appState.userId)
        }
    }

    private func sendTextRequest(text: String, serverURL: String, userId: String) async {
        let endpoint = "\(serverURL)/api/v1/chat/text"

        guard let url = URL(string: endpoint) else {
            await MainActor.run {
                statusText = "Invalid server URL"
                isProcessing = false
            }
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = TextRequest(text: text, userId: userId, conversationId: conversationId)
        request.httpBody = try? JSONEncoder().encode(body)

        do {
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }

            let voiceResponse = try JSONDecoder().decode(VoiceResponse.self, from: data)

            await MainActor.run {
                handleResponse(voiceResponse)
            }

        } catch {
            await MainActor.run {
                statusText = "Connection error"
                isProcessing = false
            }
        }
    }

    // MARK: - Audio Playback

    private func playAudio(_ data: Data) {
        do {
            audioPlayer = try AVAudioPlayer(data: data)
            audioPlayer?.delegate = self
            audioPlayer?.prepareToPlay()
            audioPlayer?.play()
            isSpeaking = true
        } catch {
            print("Failed to play audio: \(error)")
            isSpeaking = false
        }
    }

    // MARK: - Cleanup

    func reset() {
        conversationId = nil
        lastResponse = ""
        statusText = "Tap to speak"
    }
}

// MARK: - AVAudioRecorderDelegate

extension VoiceAssistant: AVAudioRecorderDelegate {
    func audioRecorderDidFinishRecording(_ recorder: AVAudioRecorder, successfully flag: Bool) {
        if !flag {
            statusText = "Recording failed"
            isListening = false
            isProcessing = false
        }
    }
}

// MARK: - AVAudioPlayerDelegate

extension VoiceAssistant: AVAudioPlayerDelegate {
    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        DispatchQueue.main.async {
            self.isSpeaking = false
        }
    }
}

// MARK: - API Models

struct VoiceResponse: Codable {
    let text: String
    let audioBase64: String
    let conversationId: String
    let toolsUsed: [String]

    enum CodingKeys: String, CodingKey {
        case text
        case audioBase64 = "audio_base64"
        case conversationId = "conversation_id"
        case toolsUsed = "tools_used"
    }
}

struct TextRequest: Codable {
    let text: String
    let userId: String
    let conversationId: String?

    enum CodingKeys: String, CodingKey {
        case text
        case userId = "user_id"
        case conversationId = "conversation_id"
    }
}
