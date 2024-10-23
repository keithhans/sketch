//
//  ContentView.swift
//  sketch
//
//  Created by 皮卡熊 on 2024/10/23.
//

import SwiftUI

struct ContentView: View {
    @State private var lines: [Line] = []
    @State private var currentLine: Line?
    @State private var showPlus = true
    @State private var lastRemovedLine: Line?  // 存储最后一次撤回的线
    
    var body: some View {
        ZStack {
            Canvas { context, size in
                for (index, line) in lines.enumerated() {
                    var path = Path()
                    path.addLines(line.points)
                    context.stroke(path, with: .color(.black), lineWidth: 3)
                    
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
                            lastRemovedLine = nil  // 重置最后撤回的线
                        }
                    }
            )
            .background(Color.white)
            
            VStack {
                HStack {
                    Spacer()
                    Button(action: {
                        lines.removeAll()
                        currentLine = nil
                        lastRemovedLine = nil
                    }) {
                        Image(systemName: "trash")
                            .foregroundColor(.white)
                            .padding(10)
                            .background(Color.red)
                            .clipShape(Circle())
                    }
                    .padding(.top, 50)
                    .padding(.trailing, 20)
                }
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
                    .disabled(lines.isEmpty && lastRemovedLine == nil)
                    
                    Button(action: {
                        sendLines()
                    }) {
                        Image(systemName: "paperplane.fill")
                            .foregroundColor(.white)
                            .padding(10)
                            .background(Color.green)
                            .clipShape(Circle())
                    }
                }
                .padding(.bottom, 20)
                .padding(.trailing, 20)
            }
        }
        .edgesIgnoringSafeArea(.all)
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
        if lastRemovedLine == nil {
            if let lastLine = lines.popLast() {
                lastRemovedLine = lastLine
            }
        } 
    }
    
    private func sendLines() {
        // 发送按钮的逻辑暂时为空
        print("发送按钮被点击")
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

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
