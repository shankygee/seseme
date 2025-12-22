//
//  JarvisApp.swift
//  Jarvis - AI Personal Assistant
//
//  Main entry point for the iOS application.
//

import SwiftUI

@main
struct JarvisApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .preferredColorScheme(.dark)
        }
    }
}

/// Global application state
class AppState: ObservableObject {
    @Published var isAuthenticated = false
    @Published var userId: String = UUID().uuidString
    @Published var serverURL: String = "http://localhost:8000"

    init() {
        loadSettings()
    }

    func loadSettings() {
        if let savedURL = UserDefaults.standard.string(forKey: "serverURL") {
            serverURL = savedURL
        }
        if let savedUserId = UserDefaults.standard.string(forKey: "userId") {
            userId = savedUserId
        } else {
            UserDefaults.standard.set(userId, forKey: "userId")
        }
    }

    func saveSettings() {
        UserDefaults.standard.set(serverURL, forKey: "serverURL")
    }
}
