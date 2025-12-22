//
//  ContentView.swift
//  Jarvis
//
//  Main content view with the voice interface.
//

import SwiftUI
import AVFoundation

struct ContentView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var voiceAssistant = VoiceAssistant()
    @State private var showSettings = false
    @State private var showHistory = false

    var body: some View {
        ZStack {
            // Background gradient
            LinearGradient(
                gradient: Gradient(colors: [
                    Color(hex: "0a0a0f"),
                    Color(hex: "1a1a2e"),
                    Color(hex: "0a0a0f")
                ]),
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            VStack(spacing: 40) {
                // Header
                HStack {
                    Button(action: { showHistory = true }) {
                        Image(systemName: "clock.arrow.circlepath")
                            .font(.title2)
                            .foregroundColor(.white.opacity(0.7))
                    }

                    Spacer()

                    Text("JARVIS")
                        .font(.system(size: 24, weight: .light, design: .monospaced))
                        .foregroundColor(.white.opacity(0.9))
                        .tracking(8)

                    Spacer()

                    Button(action: { showSettings = true }) {
                        Image(systemName: "gearshape")
                            .font(.title2)
                            .foregroundColor(.white.opacity(0.7))
                    }
                }
                .padding(.horizontal, 24)
                .padding(.top, 20)

                Spacer()

                // Main orb visualization
                OrbView(
                    isListening: voiceAssistant.isListening,
                    isProcessing: voiceAssistant.isProcessing,
                    isSpeaking: voiceAssistant.isSpeaking
                )

                // Status text
                Text(voiceAssistant.statusText)
                    .font(.system(size: 16, weight: .light))
                    .foregroundColor(.white.opacity(0.6))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 40)
                    .frame(height: 50)

                // Last response preview
                if !voiceAssistant.lastResponse.isEmpty {
                    Text(voiceAssistant.lastResponse)
                        .font(.system(size: 14))
                        .foregroundColor(.white.opacity(0.5))
                        .multilineTextAlignment(.center)
                        .lineLimit(3)
                        .padding(.horizontal, 40)
                }

                Spacer()

                // Main action button
                MainButton(
                    isListening: voiceAssistant.isListening,
                    isProcessing: voiceAssistant.isProcessing,
                    action: {
                        if voiceAssistant.isListening {
                            voiceAssistant.stopListening()
                        } else {
                            voiceAssistant.startListening()
                        }
                    }
                )

                // Keyboard input option
                Button(action: { voiceAssistant.showTextInput = true }) {
                    HStack {
                        Image(systemName: "keyboard")
                        Text("Type instead")
                    }
                    .font(.system(size: 14))
                    .foregroundColor(.white.opacity(0.5))
                }
                .padding(.bottom, 40)
            }
        }
        .onAppear {
            voiceAssistant.configure(appState: appState)
        }
        .sheet(isPresented: $showSettings) {
            SettingsView()
        }
        .sheet(isPresented: $showHistory) {
            ConversationHistoryView()
        }
        .sheet(isPresented: $voiceAssistant.showTextInput) {
            TextInputView(voiceAssistant: voiceAssistant)
        }
    }
}

// MARK: - Orb Visualization

struct OrbView: View {
    let isListening: Bool
    let isProcessing: Bool
    let isSpeaking: Bool

    @State private var animationPhase: CGFloat = 0
    @State private var pulseScale: CGFloat = 1.0

    var orbColor: Color {
        if isListening { return Color(hex: "00d4ff") }
        if isProcessing { return Color(hex: "ff6b35") }
        if isSpeaking { return Color(hex: "7b68ee") }
        return Color(hex: "4a9eff")
    }

    var body: some View {
        ZStack {
            // Outer glow
            Circle()
                .fill(
                    RadialGradient(
                        gradient: Gradient(colors: [
                            orbColor.opacity(0.3),
                            orbColor.opacity(0.1),
                            Color.clear
                        ]),
                        center: .center,
                        startRadius: 60,
                        endRadius: 150
                    )
                )
                .frame(width: 300, height: 300)
                .scaleEffect(pulseScale)

            // Inner orb
            Circle()
                .fill(
                    RadialGradient(
                        gradient: Gradient(colors: [
                            orbColor.opacity(0.8),
                            orbColor.opacity(0.4),
                            orbColor.opacity(0.2)
                        ]),
                        center: .center,
                        startRadius: 20,
                        endRadius: 80
                    )
                )
                .frame(width: 160, height: 160)
                .overlay(
                    Circle()
                        .stroke(orbColor.opacity(0.5), lineWidth: 2)
                )

            // Core
            Circle()
                .fill(orbColor)
                .frame(width: 40, height: 40)
                .blur(radius: 10)

            // Activity indicator
            if isProcessing {
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle(tint: .white))
                    .scaleEffect(1.5)
            }
        }
        .onAppear {
            withAnimation(.easeInOut(duration: 2).repeatForever(autoreverses: true)) {
                pulseScale = 1.1
            }
        }
        .onChange(of: isListening) { _ in updateAnimation() }
        .onChange(of: isProcessing) { _ in updateAnimation() }
        .onChange(of: isSpeaking) { _ in updateAnimation() }
    }

    private func updateAnimation() {
        withAnimation(.spring(response: 0.3)) {
            if isListening || isProcessing || isSpeaking {
                pulseScale = 1.15
            } else {
                pulseScale = 1.0
            }
        }
    }
}

// MARK: - Main Button

struct MainButton: View {
    let isListening: Bool
    let isProcessing: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            gradient: Gradient(colors: [
                                Color(hex: isListening ? "ff4444" : "4a9eff"),
                                Color(hex: isListening ? "cc0000" : "2563eb")
                            ]),
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    .frame(width: 80, height: 80)
                    .shadow(color: Color(hex: isListening ? "ff4444" : "4a9eff").opacity(0.5), radius: 20)

                Image(systemName: isListening ? "stop.fill" : "mic.fill")
                    .font(.system(size: 30))
                    .foregroundColor(.white)
            }
        }
        .disabled(isProcessing)
        .opacity(isProcessing ? 0.5 : 1.0)
    }
}

// MARK: - Text Input View

struct TextInputView: View {
    @ObservedObject var voiceAssistant: VoiceAssistant
    @State private var inputText = ""
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationView {
            VStack {
                TextField("Type your message...", text: $inputText, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .padding()
                    .lineLimit(5...10)

                Button("Send") {
                    if !inputText.isEmpty {
                        voiceAssistant.sendTextMessage(inputText)
                        dismiss()
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(inputText.isEmpty)

                Spacer()
            }
            .navigationTitle("Message Jarvis")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }
}

// MARK: - Settings View

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) var dismiss
    @State private var serverURL: String = ""

    var body: some View {
        NavigationView {
            Form {
                Section("Server Configuration") {
                    TextField("Server URL", text: $serverURL)
                        .textContentType(.URL)
                        .autocapitalization(.none)
                }

                Section("About") {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("1.0.0")
                            .foregroundColor(.secondary)
                    }

                    HStack {
                        Text("User ID")
                        Spacer()
                        Text(appState.userId.prefix(8) + "...")
                            .foregroundColor(.secondary)
                            .font(.system(.body, design: .monospaced))
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        appState.serverURL = serverURL
                        appState.saveSettings()
                        dismiss()
                    }
                }
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
            .onAppear {
                serverURL = appState.serverURL
            }
        }
    }
}

// MARK: - Conversation History View

struct ConversationHistoryView: View {
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationView {
            List {
                Text("Conversation history coming soon...")
                    .foregroundColor(.secondary)
            }
            .navigationTitle("History")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

// MARK: - Color Extension

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

#Preview {
    ContentView()
        .environmentObject(AppState())
}
