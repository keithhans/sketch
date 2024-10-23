import asyncio
import json
import time
from pymycobot import MyCobot

# 机械臂的工作范围
ARM_X_MIN = 140
ARM_X_MAX = 280
ARM_Y_MIN = -100
ARM_Y_MAX = 100
ARM_Z_DOWN = 55  # 假设Z轴高度固定
ARM_Z_UP = 70  # 假设Z轴高度固定


class SketchServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = set()
        self.mc = MyCobot("/dev/ttyAMA0", 1000000)
        self.mc.set_fresh_mode(0)
        self.width = 800
        self.heigth = 600

    def convert(self, x, y, w, h):
        # 计算原始图片的纵横比
        original_aspect_ratio = w / h
        
        # 计算机械臂工作范围的宽度和高度
        arm_width = ARM_X_MAX - ARM_X_MIN
        arm_height = ARM_Y_MAX - ARM_Y_MIN
        arm_aspect_ratio = arm_width / arm_height
        
        # 计算缩放因子
        if original_aspect_ratio > arm_aspect_ratio:
            # 宽图，以宽度为基准进行缩放
            scale = arm_width / w
        else:
            # 高图，以高度为基准进行缩放
            scale = arm_height / h
        
        print(f"scale:{scale}")

        # 计算偏移量，使图像居中
        offset_x = ARM_X_MIN + (arm_width - w * scale) / 2
        offset_y = ARM_Y_MIN + (arm_height - h * scale) / 2

        x = x * scale + offset_x
        y = y * scale + offset_y
        print(f"after convert:{x}, {y}")
        return x, y

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
                            x, y = self.convert(line[0]['x'], line[0]['y'], self.width, self.height)
                            self.mc.send_coords([x, y, ARM_Z_UP, 179, 0, -90], 100, 1)
                            time.sleep(2)
                            for point_index, point in enumerate(line):
                                print(f"    Point {point_index + 1}: ({point['x']}, {point['y']})")
                                x, y = self.convert(point['x'], point['y'], self.width, self.height)
                                self.mc.send_coords([x, y, ARM_Z_DOWN, 179, 0, -90], 100, 1)
                                time.sleep(1)
                            self.mc.send_coord(3, ARM_Z_UP, 60)
                            time.sleep(1)

                    elif message['type'] == "RESET":
                        dimensions = message['data']
                        self.width, self.height = dimensions['width'], dimensions['height']
                        print(f"Reset request received. Screen size: {self.width} x {self.height}")                        
                        self.mc.send_coords([230, -50, ARM_Z_UP, 179, 0, -90], 50, 1)
                        time.sleep(2)
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
