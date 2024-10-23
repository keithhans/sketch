import asyncio

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
                data = await reader.read(1024)  # 增加读取的数据量
                if not data:
                    print(f"Client {addr} disconnected")
                    break
                message = data.decode().strip()
                print(f"Received message from {addr}")
                
                if message.startswith("LINES"):
                    lines = message.split('\n')[1:]
                    print("Received lines:")
                    for line in lines:
                        x1, y1, x2, y2 = map(float, line.split(','))
                        print(f"  Start: ({x1}, {y1}), End: ({x2}, {y2})")
                elif message.startswith("RESET"):
                    _, dimensions = message.split('\n')
                    width, height = map(float, dimensions.split(','))
                    print(f"Reset request received. Screen size: {width} x {height}")
                else:
                    print(f"Unknown message: {message}")
                
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
