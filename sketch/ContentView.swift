//
//  ContentView.swift
//  sketch
//
//  Created by 皮卡熊 on 2024/10/23.
//

import SwiftUI
import Foundation
import Network

struct ContentView: View {
    @State private var lines: [Line] = []
    @State private var currentLine: Line?
    @State private var showPlus = true
    @State private var sentLinesCount = 0
    @State private var showConfigSheet = false
    @AppStorage("serverAddress") private var serverAddress = "192.168.31.158:6666"
    @State private var isConnected = false
    @State private var connection: NWConnection?
    @State private var screenSize: CGSize = .zero
    
    var body: some View {
        GeometryReader { geometry in
            ZStack {
                Canvas { context, size in
                    for (index, line) in lines.enumerated() {
                        var path = Path()
                        path.addLines(line.points)
                        context.stroke(path, with: .color(index < sentLinesCount ? .gray : .black), lineWidth: 3)
                        
                        if showPlus {
                            for point in line.points {
                                let color = Color(hue: Double(index) / Double(lines.count), saturation: 1, brightness: 1)
                                drawPlus(context: context, at: point, color: color)
                            }
                        }
                    }
                    
                    if let line = currentLine {
                        var path = Path()
                        path.addLines(line.points)
                        context.stroke(path, with: .color(.black), lineWidth: 3)
                        
                        if showPlus {
                            for point in line.points {
                                drawPlus(context: context, at: point, color: .blue)
                            }
                        }
                    }
                }
                .gesture(
                    DragGesture(minimumDistance: 0, coordinateSpace: .local)
                        .onChanged { value in
                            if currentLine == nil {
                                let timestamp = round(Date().timeIntervalSince1970 * 1000) / 1000
                                currentLine = Line(
                                    points: [value.location],
                                    timestamps: [timestamp]
                                )
                            } else {
                                currentLine?.points.append(value.location)
                                let timestamp = round(Date().timeIntervalSince1970 * 1000) / 1000
                                currentLine?.timestamps.append(timestamp)
                            }
                        }
                        .onEnded { _ in
                            if var line = currentLine {
                                line.mergeCloseAngles()
                                lines.append(line)
                                currentLine = nil
                            }
                        }
                )
                .background(Color.white)
                
                VStack {
                    HStack {
                        Button(action: {
                            showConfigSheet = true
                        }) {
                            Image(systemName: "gear")
                                .foregroundColor(.white)
                                .padding(10)
                                .background(Color.gray)
                                .clipShape(Circle())
                        }
                        
                        Button(action: {
                            toggleConnection()
                        }) {
                            Image(systemName: isConnected ? "checkmark.circle" : "xmark.circle")
                                .foregroundColor(.white)
                                .padding(10)
                                .background(isConnected ? Color.green : Color.red)
                                .clipShape(Circle())
                        }
                        
                        Spacer()
                        
                        Button(action: {
                            lines.removeAll()
                            currentLine = nil
                            sentLinesCount = 0
                        }) {
                            Image(systemName: "trash")
                                .foregroundColor(.white)
                                .padding(10)
                                .background(Color.red)
                                .clipShape(Circle())
                        }
                    }
                    .padding(.top, 50)
                    .padding(.horizontal, 20)
                    
                    Spacer()
                    
                    HStack {
                        Spacer()
                        Button(action: {
                            showPlus.toggle()
                        }) {
                            Image(systemName: showPlus ? "plus.circle.fill" : "plus.circle")
                                .foregroundColor(.white)
                                .padding(10)
                                .background(Color.blue)
                                .clipShape(Circle())
                        }
                        
                        Button(action: {
                            undoLastLine()
                        }) {
                            Image(systemName: "arrow.uturn.backward")
                                .foregroundColor(.white)
                                .padding(10)
                                .background(Color.orange)
                                .clipShape(Circle())
                        }
                        .disabled(lines.count <= sentLinesCount)
                        
                        Button(action: {
                            sendLines()
                        }) {
                            Image(systemName: "paperplane.fill")
                                .foregroundColor(.white)
                                .padding(10)
                                .background(Color.green)
                                .clipShape(Circle())
                        }
                        .disabled(lines.count <= sentLinesCount)
                    }
                    .padding(.bottom, 20)
                    .padding(.trailing, 20)
                }
            }
            .onAppear {
                screenSize = geometry.size
            }
        }
        .edgesIgnoringSafeArea(.all)
        .sheet(isPresented: $showConfigSheet) {
            ConfigView(serverAddress: $serverAddress)
        }
    }
    
    private func drawPlus(context: GraphicsContext, at point: CGPoint, color: Color) {
        let size: CGFloat = 10
        context.stroke(
            Path { path in
                path.move(to: CGPoint(x: point.x - size/2, y: point.y))
                path.addLine(to: CGPoint(x: point.x + size/2, y: point.y))
                path.move(to: CGPoint(x: point.x, y: point.y - size/2))
                path.addLine(to: CGPoint(x: point.x, y: point.y + size/2))
            },
            with: .color(color),
            lineWidth: 2
        )
    }
    
    private func undoLastLine() {
        if lines.count > sentLinesCount {
            _ = lines.popLast()
        }
    }
    
    private func sendLines() {
        let newLinesCount = lines.count - sentLinesCount
        if newLinesCount > 0 {
            print("发送了 \(newLinesCount) 条新线段")
            let newLines = Array(lines[sentLinesCount...])
            let linesData = newLines.map { line -> [[String: Any]] in
                zip(line.points, line.timestamps).map { point, timestamp in
                    [
                        "x": point.x,
                        "y": point.y
                    ]
                }
            }
            let message: [String: Any] = [
                "type": "LINES",
                "data": linesData
            ]
            sendJSONMessage(message)
            sentLinesCount = lines.count
            
            // 打印每条线的所有点坐标和时间戳
            for (lineIndex, line) in newLines.enumerated() {
                print("Line \(lineIndex + 1):")
                for i in 0..<line.points.count {
                    let point = line.points[i]
                    let timestamp = line.timestamps[i]
                    let milliseconds = Int((timestamp.truncatingRemainder(dividingBy: 1)) * 1000)
                    let date = Date(timeIntervalSince1970: timestamp)
                    let formatter = DateFormatter()
                    formatter.dateFormat = "HH:mm:ss"
                    let timeString = "\(formatter.string(from: date)).\(String(format: "%03d", milliseconds))"
                    print("  Point \(i + 1): (x: \(point.x), y: \(point.y)) - Time: \(timeString)")
                }
            }
        }
    }
    
    private func toggleConnection() {
        if isConnected {
            // 断开连接
            disconnectFromServer()
        } else {
            // 连接服务器
            connectToServer()
        }
    }
    
    private func sendJSONMessage(_ message: [String: Any]) {
        guard let connection = connection else {
            print("No active connection")
            return
        }
        
        do {
            let jsonData = try JSONSerialization.data(withJSONObject: message, options: [])
            connection.send(content: jsonData, completion: .contentProcessed { error in
                if let error = error {
                    print("Failed to send message: \(error)")
                } else {
                    print("Message sent successfully")
                }
            })
        } catch {
            print("Failed to serialize JSON: \(error)")
        }
    }
    
    private func connectToServer() {
        guard let host = serverAddress.components(separatedBy: ":").first,
              let portString = serverAddress.components(separatedBy: ":").last,
              let port = Int(portString) else {
            print("Invalid server address")
            return
        }
        
        Task {
            do {
                let (newConnection, _) = try await TCPClient.connect(host: host, port: port)
                self.connection = newConnection
                print("Connected to server")
                DispatchQueue.main.async {
                    self.isConnected = true
                    self.sendResetMessage() // 连接成功后发送重置消息
                }
            } catch {
                print("Connection failed: \(error.localizedDescription)")
                DispatchQueue.main.async {
                    self.isConnected = false
                    self.connection = nil
                }
            }
        }
    }
    
    private func sendResetMessage() {
        let message: [String: Any] = [
            "type": "RESET",
            "data": [
                "width": screenSize.width,
                "height": screenSize.height
            ]
        ]
        sendJSONMessage(message)
        print("Sent reset message with screen size: \(screenSize.width) x \(screenSize.height)")
    }
    
    private func disconnectFromServer() {
        Task {
            await TCPClient.disconnect(connection: connection)
            self.connection = nil
            print("Disconnected from server")
            DispatchQueue.main.async {
                self.isConnected = false
            }
        }
    }
}

struct Line {
    var points: [CGPoint]
    var timestamps: [TimeInterval]
    
    init(points: [CGPoint], timestamps: [TimeInterval] = []) {
        self.points = points
        self.timestamps = timestamps
    }
    
    mutating func mergeCloseAngles() {
        guard points.count > 2 else { return }
        
        var newPoints = [points[0]]
        var lastAngle = angle(between: points[0], points[1])
        var newTimestamps = [timestamps[0]]

        for i in 1..<points.count - 1 {
            let currentAngle = angle(between: points[i], points[i+1])
            let angleDifference = abs(currentAngle - lastAngle)

            if angleDifference > 10 * .pi / 180 || timestamps[i+1] - newTimestamps.last! > 0.03 {
                newPoints.append(points[i])
                newTimestamps.append(timestamps[i])
                lastAngle = currentAngle
            }
        }
        
        newPoints.append(points.last!)
        newTimestamps.append(timestamps.last!)
        points = newPoints
        timestamps = newTimestamps
    }
    
    private func angle(between point1: CGPoint, _ point2: CGPoint) -> CGFloat {
        return atan2(point2.y - point1.y, point2.x - point1.x)
    }
}

struct ConfigView: View {
    @Binding var serverAddress: String
    @Environment(\.presentationMode) var presentationMode
    
    var body: some View {
        VStack {
            HStack {
                Text("配置")
                    .font(.headline)
                Spacer()
                Button("完成") {
                    presentationMode.wrappedValue.dismiss()
                }
            }
            .padding()
            
            Form {
                Section(header: Text("服务器配置")) {
                    TextField("IP:Port", text: $serverAddress)
                }
            }
        }
        .frame(width: 300, height: 150)
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}

actor TCPClientActor {
    private var hasResumed = false
    
    func markAsResumed() {
        hasResumed = true
    }
    
    func hasAlreadyResumed() -> Bool {
        return hasResumed
    }
}

class TCPClient {
    static func connect(host: String, port: Int) async throws -> (NWConnection, NWEndpoint) {
        let endpoint = NWEndpoint.hostPort(host: NWEndpoint.Host(host), port: NWEndpoint.Port(integerLiteral: UInt16(port)))
        let connection = NWConnection(to: endpoint, using: .tcp)
        let actor = TCPClientActor()
        
        return try await withCheckedThrowingContinuation { continuation in
            connection.stateUpdateHandler = { state in
                Task {
                    guard !(await actor.hasAlreadyResumed()) else { return }
                    
                    switch state {
                    case .ready:
                        await actor.markAsResumed()
                        continuation.resume(returning: (connection, endpoint))
                    case .failed(let error):
                        await actor.markAsResumed()
                        continuation.resume(throwing: error)
                    case .cancelled:
                        await actor.markAsResumed()
                        continuation.resume(throwing: NSError(domain: "TCPClient", code: 0, userInfo: [NSLocalizedDescriptionKey: "Connection cancelled"]))
                    default:
                        break
                    }
                }
            }
            
            connection.start(queue: .global())
        }
    }
    
    static func disconnect(connection: NWConnection?) async {
        guard let connection = connection else { return }
        return await withCheckedContinuation { continuation in
            connection.cancel()
            continuation.resume()
        }
    }
}
