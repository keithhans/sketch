import asyncio
import json

class SketchServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = set()

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"New connection from {addr}")
        self.clients.add(writer)
        
        try:
            while True:
                data = await reader.read(4096)  # 增加读取的数据量
                if not data:
                    print(f"Client {addr} disconnected")
                    break
                try:
                    message = json.loads(data.decode())
                    print(f"Received message from {addr}")
                    
                    if message['type'] == "LINES":
                        lines = message['data']
                        print("Received lines:")
                        for line_index, line in enumerate(lines):
                            print(f"  Line {line_index + 1}:")
                            for point_index, point in enumerate(line):
                                print(f"    Point {point_index + 1}: ({point['x']}, {point['y']})")
                    elif message['type'] == "RESET":
                        dimensions = message['data']
                        width, height = dimensions['width'], dimensions['height']
                        print(f"Reset request received. Screen size: {width} x {height}")
                    else:
                        print(f"Unknown message type: {message['type']}")
                except json.JSONDecodeError:
                    print(f"Invalid JSON received from {addr}")
                
        except asyncio.CancelledError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            self.clients.remove(writer)
            print(f"Connection closed for {addr}")

    async def start_server(self):
        server = await asyncio.start_server(
            self.handle_client, self.host, self.port)

        addr = server.sockets[0].getsockname()
        print(f'Serving on {addr}')

        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    host = '0.0.0.0'  # 监听所有可用的网络接口
    port = 6666
    
    sketch_server = SketchServer(host, port)
    asyncio.run(sketch_server.start_server())
