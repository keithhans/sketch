import asyncio
import json
import time
from pymycobot import MyCobot
import argparse
import numpy as np
import matplotlib.pyplot as plt
import csv
from datetime import datetime
import os
from pathlib import Path

# 机械臂的工作范围
ARM_X_MIN = 150
ARM_X_MAX = 270
ARM_Y_MIN = -100
ARM_Y_MAX = 100
ARM_Z_DIFF = 59
ARM_Z_UP = 100

class SketchServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = set()
        self.mc = MyCobot("/dev/ttyAMA0", 1000000)
        self.mc.set_fresh_mode(0)
        print(f"fresh mode:{self.mc.get_fresh_mode()}")
        self.width = 800
        self.height = 600
        
        # 添加位置记录列表
        self.position_records = []
        
        # 创建保存数据的目录
        self.data_dir = Path("position_records")
        self.data_dir.mkdir(exist_ok=True)
        
        # 创建新的会话文件名
        self.session_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 加载保存的 arm_z_up 值
        self.config_file = Path("robot_config.json")
        self.load_config()

    def load_config(self):
        """从配置文件加载 arm_z_up 值"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.arm_z_up = config.get('arm_z_up', ARM_Z_UP)
                print(f"Loaded ARM_Z_UP from config: {self.arm_z_up}")
            except Exception as e:
                print(f"Error loading config: {e}")
                self.arm_z_up = ARM_Z_UP
        else:
            self.arm_z_up = ARM_Z_UP
            self.save_config()

    def save_config(self):
        """保存 arm_z_up 值到配置文件"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump({'arm_z_up': self.arm_z_up}, f)
            print(f"Saved ARM_Z_UP to config: {self.arm_z_up}")
        except Exception as e:
            print(f"Error saving config: {e}")

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
        
        # 计算偏移量，使图像居中
        offset_x = ARM_X_MIN + (arm_width - w * scale) / 2
        offset_y = ARM_Y_MIN + (arm_height - h * scale) / 2

        x = x * scale + offset_x
        y = y * scale + offset_y
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
        
        # 绘制目标位置和实际位置
        plt.scatter(target_positions[:, 0], target_positions[:, 1], 
                   c='blue', label='Target Positions', alpha=0.5)
        plt.scatter(actual_positions[:, 0], actual_positions[:, 1], 
                   c='red', label='Actual Positions', alpha=0.5)
        
        # 绘制连接线
        for target, actual in zip(target_positions, actual_positions):
            plt.plot([target[0], actual[0]], [target[1], actual[1]], 
                    'g-', alpha=0.3)
        
        plt.title('Target vs Actual Positions')
        plt.xlabel('X Position')
        plt.ylabel('Y Position')
        plt.legend()
        plt.grid(True)
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
                data = await reader.read(4096000)
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
                            self.mc.send_coords([x, y, self.arm_z_up, -180, 0, -90], 100, 1)
                            time.sleep(2)
                            last = time.time()
                            for point_index, point in enumerate(line):
                                x, y = self.convert(point['x'], point['y'], self.width, self.height)
                                self.mc.send_coords([x, y, self.arm_z_up - ARM_Z_DIFF, -180, 0, -90], 100, 1)
                                time.sleep(0.27)
                                
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
                            self.mc.send_coords([x, y, self.arm_z_up, -180, 0, -90], 60, 1)
                            time.sleep(1)
                        
                        # 在完成所有线条后保存和绘制位置数据
                        self.save_and_plot_positions()
                        
                    elif message['type'] == "RESET":
                        dimensions = message['data']
                        self.width, self.height = dimensions['width'], dimensions['height']
                        print(f"Reset request received. Screen size: {self.width} x {self.height}")
                        self.mc.send_coords([210, 0, self.arm_z_up, -180, 0, -90], 50, 1)
                        time.sleep(2)
                        # 在新会话开始时清空位置记录
                        self.position_records = []
                    elif message['type'] == "ADJUST_HEIGHT":
                        increase = message['data']['increase']
                        if increase:
                            self.arm_z_up += 1
                        else:
                            self.arm_z_up -= 1
                        print(f"Adjusted ARM_Z_UP to: {self.arm_z_up}")
                        
                        # 保存新的高度值
                        self.save_config()
                        
                        # 立即移动到新的高度以展示效果
                        current_coords = self.mc.get_coords()
                        if current_coords:
                            self.mc.send_coords([
                                current_coords[0],
                                current_coords[1],
                                self.arm_z_up,
                                -180, 0, -90
                            ], 50, 1)
                    else:
                        print(f"Unknown message type: {message['type']}")
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON received from {addr}")
                    print(f"Error details: {str(e)}")
                    print("Received data:")
                    try:
                        decoded_data = data.decode()
                        print(f"Length: {len(decoded_data)} bytes")
                        print(f"Content: {decoded_data}")
                    except UnicodeDecodeError:
                        print("Failed to decode data as UTF-8")
                        print(f"Raw data length: {len(data)} bytes")
                        print(f"Raw data: {data}")
                
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
    args = parser.parse_args()
    
    sketch_server = SketchServer(args.host, args.port)
    asyncio.run(sketch_server.start_server())
