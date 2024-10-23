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
    
    var body: some View {
        ZStack {
            Canvas { context, size in
                for line in lines {
                    var path = Path()
                    path.addLines(line.points)
                    context.stroke(path, with: .color(.black), lineWidth: 3)
                }
                
                if let line = currentLine {
                    var path = Path()
                    path.addLines(line.points)
                    context.stroke(path, with: .color(.black), lineWidth: 3)
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
                Spacer().frame(height: 50) // 添加一些顶部间距
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
                    .padding(.trailing, 20) // 增加右侧边距
                }
                Spacer()
            }
        }
        .edgesIgnoringSafeArea(.all)
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
