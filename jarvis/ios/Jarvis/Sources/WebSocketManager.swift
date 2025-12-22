//
//  WebSocketManager.swift
//  Jarvis
//
//  WebSocket connection for real-time streaming (optional upgrade from REST).
//

import Foundation
import Combine

/// WebSocket manager for real-time voice streaming
class WebSocketManager: NSObject, ObservableObject {
    @Published var isConnected = false
    @Published var latestMessage: WebSocketMessage?

    private var webSocket: URLSessionWebSocketTask?
    private var session: URLSession?

    private let serverURL: String
    private let userId: String

    init(serverURL: String, userId: String) {
        self.serverURL = serverURL
        self.userId = userId
        super.init()
    }

    // MARK: - Connection

    func connect() {
        let wsURL = serverURL
            .replacingOccurrences(of: "http://", with: "ws://")
            .replacingOccurrences(of: "https://", with: "wss://")

        guard let url = URL(string: "\(wsURL)/ws/chat/\(userId)") else {
            print("Invalid WebSocket URL")
            return
        }

        session = URLSession(configuration: .default, delegate: self, delegateQueue: OperationQueue())
        webSocket = session?.webSocketTask(with: url)
        webSocket?.resume()

        receiveMessage()
    }

    func disconnect() {
        webSocket?.cancel(with: .normalClosure, reason: nil)
        isConnected = false
    }

    // MARK: - Sending

    func sendAudio(_ data: Data) {
        let message = URLSessionWebSocketTask.Message.data(data)
        webSocket?.send(message) { error in
            if let error = error {
                print("WebSocket send error: \(error)")
            }
        }
    }

    func sendText(_ text: String) {
        let message = URLSessionWebSocketTask.Message.string(text)
        webSocket?.send(message) { error in
            if let error = error {
                print("WebSocket send error: \(error)")
            }
        }
    }

    // MARK: - Receiving

    private func receiveMessage() {
        webSocket?.receive { [weak self] result in
            switch result {
            case .success(let message):
                self?.handleMessage(message)
                self?.receiveMessage() // Continue listening

            case .failure(let error):
                print("WebSocket receive error: \(error)")
                DispatchQueue.main.async {
                    self?.isConnected = false
                }
            }
        }
    }

    private func handleMessage(_ message: URLSessionWebSocketTask.Message) {
        switch message {
        case .string(let text):
            if let data = text.data(using: .utf8),
               let wsMessage = try? JSONDecoder().decode(WebSocketMessage.self, from: data) {
                DispatchQueue.main.async {
                    self.latestMessage = wsMessage
                }
            }

        case .data(let data):
            // Audio data - play it
            DispatchQueue.main.async {
                self.latestMessage = WebSocketMessage(type: "audio", data: data)
            }

        @unknown default:
            break
        }
    }
}

// MARK: - URLSessionWebSocketDelegate

extension WebSocketManager: URLSessionWebSocketDelegate {
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol protocol: String?) {
        DispatchQueue.main.async {
            self.isConnected = true
        }
    }

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        DispatchQueue.main.async {
            self.isConnected = false
        }
    }
}

// MARK: - Models

struct WebSocketMessage: Identifiable {
    let id = UUID()
    let type: String
    var text: String?
    var data: Data?

    init(type: String, text: String? = nil, data: Data? = nil) {
        self.type = type
        self.text = text
        self.data = data
    }
}

extension WebSocketMessage: Codable {
    enum CodingKeys: String, CodingKey {
        case type, text
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        type = try container.decode(String.self, forKey: .type)
        text = try container.decodeIfPresent(String.self, forKey: .text)
        data = nil
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(type, forKey: .type)
        try container.encodeIfPresent(text, forKey: .text)
    }
}
