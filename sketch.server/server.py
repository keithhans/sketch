import asyncio
import json
import time
from pymycobot import MyCobot
import argparse
import numpy as np
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
import csv
from datetime import datetime

# 添加新的导入
import os
from pathlib import Path

# 机械臂的工作范围
ARM_X_MIN = 150
ARM_X_MAX = 270
ARM_Y_MIN = -100
ARM_Y_MAX = 100
ARM_Z_DOWN = 59 #70 # 假设Z轴高度固定
ARM_Z_UP = 100  # 假设Z轴高度固定


class SketchServer:
    def __init__(self, host, port, scan_file=None, enable_compensation=False):
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
            if scan_file is None:
                raise ValueError("scan_file must be provided when compensation is enabled")
            print("Error compensation enabled")
            self.load_compensation_data(scan_file)
        else:
            print("Error compensation disabled")
        
        # 添加位置记录列表
        self.position_records = []
        
        # 创建保存数据的目录
        self.data_dir = Path("position_records")
        self.data_dir.mkdir(exist_ok=True)
        
        # 创建新的会话文件名
        self.session_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    
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

    def save_and_plot_positions(self):
        """保存位置数据并生成对比图"""
        if not self.position_records:
            return
            
        # 准备数据
        target_positions = np.array([[r['target_x'], r['target_y']] for r in self.position_records])
        actual_positions = np.array([[r['actual_x'], r['actual_y']] for r in self.position_records])
        
        # 保存CSV文件
        csv_path = self.data_dir / f"positions_{self.session_time}.csv"
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['target_x', 'target_y', 'actual_x', 'actual_y', 'error_x', 'error_y', 'error_distance'])
            for record in self.position_records:
                writer.writerow([
                    record['target_x'],
                    record['target_y'],
                    record['actual_x'],
                    record['actual_y'],
                    record['actual_x'] - record['target_x'],
                    record['actual_y'] - record['target_y'],
                    record['error_distance']
                ])
        
        # 创建图形
        plt.figure(figsize=(12, 8))
        
        # 绘制目标位置
        plt.scatter(target_positions[:, 0], target_positions[:, 1], 
                   c='blue', label='Target Positions', alpha=0.5)
        
        # 绘制实际位置
        plt.scatter(actual_positions[:, 0], actual_positions[:, 1], 
                   c='red', label='Actual Positions', alpha=0.5)
        
        # 绘制连接线
        for target, actual in zip(target_positions, actual_positions):
            plt.plot([target[0], actual[0]], [target[1], actual[1]], 
                    'g-', alpha=0.3)
        
        # 设置图形属性
        plt.title('Target vs Actual Positions')
        plt.xlabel('X Position')
        plt.ylabel('Y Position')
        plt.legend()
        plt.grid(True)
        
        # 保存图形
        plt.savefig(self.data_dir / f"positions_plot_{self.session_time}.png")
        plt.close()
        
        # 计算并打印误差统计
        errors = actual_positions - target_positions
        error_distances = np.sqrt(np.sum(errors**2, axis=1))
        print("\nPosition Error Statistics:")
        print(f"Mean Error Distance: {np.mean(error_distances):.2f}")
        print(f"Max Error Distance: {np.max(error_distances):.2f}")
        print(f"Min Error Distance: {np.min(error_distances):.2f}")
        print(f"Data saved to {csv_path}")

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
                                
                                # 获取实际位置并记录
                                actual_coords = self.mc.get_coords()
                                if actual_coords and len(actual_coords) >= 2:
                                    actual_x, actual_y = actual_coords[0], actual_coords[1]
                                    error_distance = np.sqrt((actual_x - x)**2 + (actual_y - y)**2)
                                    
                                    self.position_records.append({
                                        'target_x': x,
                                        'target_y': y,
                                        'actual_x': actual_x,
                                        'actual_y': actual_y,
                                        'error_distance': error_distance
                                    })
                                    
                                    print(f"    Point {point_index + 1}:")
                                    print(f"      Target: ({x:.2f}, {y:.2f})")
                                    print(f"      Actual: ({actual_x:.2f}, {actual_y:.2f})")
                                    print(f"      Error: {error_distance:.2f}")
                                
                                now = time.time()
                                
                                print(f"    Point {point_index + 1}: ({x}, {y}), {now-last:.3f}")

                                interval = 0.30
                                if now - last < interval:
                                    time.sleep(interval - (now - last))
                                last = time.time()
                            
                            # pen up
                            time.sleep(1)
                            self.send_coords_with_compensation([x, y, ARM_Z_UP, -175, 0, -90], 60, 1)
                            time.sleep(1)
                        
                        # 在完成所有线条后保存和绘制位置数据
                        self.save_and_plot_positions()
                        
                    elif message['type'] == "RESET":
                        dimensions = message['data']
                        self.width, self.height = dimensions['width'], dimensions['height']
                        print(f"Reset request received. Screen size: {self.width} x {self.height}")
                        self.send_coords_with_compensation([210, 0, ARM_Z_UP, -175, 0, -90], 50, 1)
                        time.sleep(2)
                        # 在新会话开始时清空位置记录
                        self.position_records = []
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
    parser = argparse.ArgumentParser(description='Start sketch server')
    parser.add_argument('--host', default='0.0.0.0', help='Host address')
    parser.add_argument('--port', type=int, default=6666, help='Port number')
    parser.add_argument('--enable-compensation', action='store_true', 
                       help='Enable error compensation')
    parser.add_argument('--scan-file', help='Path to the scan results NPZ file (required if compensation enabled)')
    args = parser.parse_args()
    
    if args.enable_compensation and not args.scan_file:
        parser.error("--scan-file is required when --enable-compensation is set")
    
    sketch_server = SketchServer(args.host, args.port, args.scan_file, 
                               enable_compensation=args.enable_compensation)
    asyncio.run(sketch_server.start_server())
