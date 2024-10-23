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
    @State private var showPlus = true  // 新增状态变量来控制加号显示
    
    var body: some View {
        ZStack {
            Canvas { context, size in
                for (index, line) in lines.enumerated() {
                    var path = Path()
                    path.addLines(line.points)
                    context.stroke(path, with: .color(.black), lineWidth: 3)
                    
                    // 只在 showPlus 为 true 时绘制加号
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
                    
                    // 只在 showPlus 为 true 时绘制加号
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
                        if let line = currentLine {
                            lines.append(line)
                            currentLine = nil
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
                    .padding(.bottom, 20)
                    .padding(.trailing, 20)
                }
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
}

struct Line {
    var points: [CGPoint]
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
