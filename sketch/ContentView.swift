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
        .edgesIgnoringSafeArea(.all)
    }
}

struct Line {
    var points: [CGPoint]
}

#Preview {
    ContentView()
}
