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
    @State private var serverAddress = ""
    @State private var isConnected = false
    
    var body: some View {
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
                            currentLine = Line(points: [value.location])
                        } else {
                            currentLine?.points.append(value.location)
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
                    
                    Button(action: {
                        resetRobot()
                    }) {
                        Image(systemName: "arrow.counterclockwise")
                            .foregroundColor(.white)
                            .padding(10)
                            .background(Color.blue)
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
        // 发送新的线段
        let newLinesCount = lines.count - sentLinesCount
        if newLinesCount > 0 {
            print("发送了 \(newLinesCount) 条新线段")
            for i in sentLinesCount..<lines.count {
                let line = lines[i]
                if let startPoint = line.points.first, let endPoint = line.points.last {
                    print("线段 \(i + 1):")
                    print("  起点: x: \(startPoint.x), y: \(startPoint.y)")
                    print("  终点: x: \(endPoint.x), y: \(endPoint.y)")
                }
            }
            sentLinesCount = lines.count
        }
    }
    
    private func toggleConnection() {
        if isConnected {
            // 断开连接
            print("断开连接")
            isConnected = false
        } else {
            // 连接服务器
            connectToServer()
        }
    }
    
    private func resetRobot() {
        // TODO: 实现复位功能
        print("复位机器")
    }
    
    private func connectToServer() {
        guard let host = serverAddress.components(separatedBy: ":").first,
              let portString = serverAddress.components(separatedBy: ":").last,
              let port = Int(portString) else {
            print("Invalid server address")
            return
        }
        
        let task = Task {
            do {
                let (stream, _) = try await TCPClient.connect(host: host, port: port)
                print("Connected to server")
                DispatchQueue.main.async {
                    self.isConnected = true
                }
                // 在这里可以进行进一步的通信
            } catch {
                print("Connection failed: \(error.localizedDescription)")
                DispatchQueue.main.async {
                    self.isConnected = false
                }
            }
        }
    }
}

struct Line {
    var points: [CGPoint]
    
    mutating func mergeCloseAngles() {
        guard points.count > 2 else { return }
        
        var newPoints = [points[0]]
        var lastAngle = angle(between: points[0], points[1])
        
        for i in 1..<points.count - 1 {
            let currentAngle = angle(between: points[i], points[i+1])
            let angleDifference = abs(currentAngle - lastAngle)
            
            if angleDifference > 10 * .pi / 180 {
                newPoints.append(points[i])
                lastAngle = currentAngle
            }
        }
        
        newPoints.append(points.last!)
        points = newPoints
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

class TCPClient {
    static func connect(host: String, port: Int) async throws -> (NWConnection, NWEndpoint) {
        let endpoint = NWEndpoint.hostPort(host: NWEndpoint.Host(host), port: NWEndpoint.Port(integerLiteral: UInt16(port)))
        let connection = NWConnection(to: endpoint, using: .tcp)
        
        return try await withCheckedThrowingContinuation { continuation in
            connection.stateUpdateHandler = { state in
                switch state {
                case .ready:
                    continuation.resume(returning: (connection, endpoint))
                case .failed(let error):
                    continuation.resume(throwing: error)
                case .cancelled:
                    continuation.resume(throwing: NSError(domain: "TCPClient", code: 0, userInfo: [NSLocalizedDescriptionKey: "Connection cancelled"]))
                default:
                    break
                }
            }
            connection.start(queue: .global())
        }
    }
}
