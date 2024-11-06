import asyncio
import json
import time
from pymycobot import MyCobot
import argparse
import numpy as np
from scipy.interpolate import griddata

# 机械臂的工作范围
ARM_X_MIN = 150
ARM_X_MAX = 270
ARM_Y_MIN = -100
ARM_Y_MAX = 100
ARM_Z_DOWN = 90 #70 # 假设Z轴高度固定
ARM_Z_UP = 100  # 假设Z轴高度固定


class SketchServer:
    def __init__(self, host, port, scan_file, enable_compensation=True):
        self.host = host
        self.port = port
        self.clients = set()
        self.mc = MyCobot("/dev/ttyAMA0", 1000000)
        self.mc.set_fresh_mode(0)
        print(f"fresh mode:{self.mc.get_fresh_mode()}")
        self.width = 800
        self.height = 600
        
        # 是否启用误差补偿
        self.enable_compensation = enable_compensation
        if self.enable_compensation:
            print("Error compensation enabled")
            self.load_compensation_data(scan_file)
        else:
            print("Error compensation disabled")
    
    def load_compensation_data(self, scan_file):
        """加载误差补偿数据"""
        data = np.load(scan_file)
        self.target_points = data['target_points']
        self.actual_points = data['actual_points']
        self.errors = self.actual_points[:, :3] - self.target_points[:, :3]
        print("Loaded compensation data")
    
    def predict_error_at_point(self, point, method='linear'):
        """预测特定点的误差"""
        predicted_error = []
        for i in range(3):  # x, y, z 三个方向
            error_i = griddata((self.target_points[:, 0], self.target_points[:, 1]),
                             self.errors[:, i],
                             (point[0], point[1]),
                             method=method)
            if np.isnan(error_i):
                distances = np.linalg.norm(self.target_points[:, :2] - np.array([point[0], point[1]]), axis=1)
                nearest_idx = np.argmin(distances)
                error_i = self.errors[nearest_idx, i]
            predicted_error.append(float(error_i))
        return np.array(predicted_error)
    
    def send_coords_with_compensation(self, coords, speed, mode):
        """发送经过误差补偿的坐标"""
        if not self.enable_compensation:
            # 如果未启用补偿，直接发送原始坐标
            self.mc.send_coords(coords, speed, mode)
            return
            
        original_point = np.array(coords[:3])
        predicted_error = self.predict_error_at_point(original_point)
        
        # 计算补偿后的位置
        compensated_position = original_point - predicted_error
        
        # 构建完整的补偿后坐标
        compensated_coords = [
            compensated_position[0],  # x
            compensated_position[1],  # y
            compensated_position[2],  # z
            coords[3],  # rx
            coords[4],  # ry
            coords[5]   # rz
        ]
        
        print(f"Original coords: {coords}")
        print(f"Predicted error: {predicted_error}")
        print(f"Compensated coords: {compensated_coords}")
        
        # 发送补偿后的坐标
        self.mc.send_coords(compensated_coords, speed, mode)

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
        
        #print(f"scale:{scale}")

        # 计算偏移量，使图像居中
        offset_x = ARM_X_MIN + (arm_width - w * scale) / 2
        offset_y = ARM_Y_MIN + (arm_height - h * scale) / 2

        x = x * scale + offset_x
        y = y * scale + offset_y
        #print(f"after convert:{x}, {y}")
        return x, -y

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"New connection from {addr}")
        self.clients.add(writer)
        
        try:
            while True:
                data = await reader.read(409600)
                if not data:
                    print(f"Client {addr} disconnected")
                    self.mc.send_angles([0, 0, -90, 0, 0, 0], 50)
                    time.sleep(2)
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
                            self.send_coords_with_compensation([x, y, ARM_Z_UP, -175, 0, -90], 100, 1)
                            time.sleep(2)
                            last = time.time()
                            for point_index, point in enumerate(line):
                                x, y = self.convert(point['x'], point['y'], self.width, self.height)
                                self.send_coords_with_compensation([x, y, ARM_Z_DOWN, -175, 0, -90], 100, 1)

                                time.sleep(0.2)
                                print(self.mc.get_coords())
                                now = time.time()
                                
                                print(f"    Point {point_index + 1}: ({x}, {y}), {now-last}")

                                interval = 0.30
                                if now - last < interval:
                                    time.sleep(interval- now + last)
                                last = time.time()
                            # pen up
                            time.sleep(1)
                            self.send_coords_with_compensation([x, y, ARM_Z_UP, -175, 0, -90], 60, 1)
                            time.sleep(1)

                    elif message['type'] == "RESET":
                        dimensions = message['data']
                        self.width, self.height = dimensions['width'], dimensions['height']
                        print(f"Reset request received. Screen size: {self.width} x {self.height}")
                        self.send_coords_with_compensation([210, 0, ARM_Z_UP, -175, 0, -90], 50, 1)
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
    parser = argparse.ArgumentParser(description='Start sketch server with error compensation')
    parser.add_argument('scan_file', help='Path to the scan results NPZ file')
    parser.add_argument('--host', default='0.0.0.0', help='Host address')
    parser.add_argument('--port', type=int, default=6666, help='Port number')
    parser.add_argument('--no-compensation', action='store_true', 
                       help='Disable error compensation')
    args = parser.parse_args()
    
    sketch_server = SketchServer(args.host, args.port, args.scan_file, 
                               enable_compensation=not args.no_compensation)
    asyncio.run(sketch_server.start_server())
