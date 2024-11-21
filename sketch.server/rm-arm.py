import socket
import time
import json

class RoboticArm:
    def __init__(self):
        self.socket = None
        self.connected = False
        self.default_port = 8080
        self.buffer_size = 1024  # 接收缓冲区大小
    
    def connect(self, ip_address, timeout=5):
        """
        连接到指定IP地址的机械臂服务器
        
        Args:
            ip_address (str): 服务器IP地址
            timeout (int): 连接超时时间（秒）
            
        Returns:
            bool: 连接是否成功
        """
        try:
            # 创建TCP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            
            # 连接到服务器
            print(f"Connecting to {ip_address}:{self.default_port}...")
            self.socket.connect((ip_address, self.default_port))
            
            # 设置连接状态
            self.connected = True
            print("Successfully connected to robotic arm server")
            return True
            
        except socket.timeout:
            print(f"Connection timeout when connecting to {ip_address}:{self.default_port}")
            self.connected = False
            return False
            
        except ConnectionRefusedError:
            print(f"Connection refused by {ip_address}:{self.default_port}")
            self.connected = False
            return False
            
        except Exception as e:
            print(f"Failed to connect: {str(e)}")
            self.connected = False
            return False
    
    def disconnect(self):
        """
        断开与机械臂服务器的连接
        
        Returns:
            bool: 断开连接是否成功
        """
        if not self.connected or self.socket is None:
            print("Not connected to any server")
            return True
            
        try:
            self.socket.close()
            self.socket = None
            self.connected = False
            print("Successfully disconnected from robotic arm server")
            return True
            
        except Exception as e:
            print(f"Error while disconnecting: {str(e)}")
            return False
    
    def is_connected(self):
        """
        检查是否已连接到服务器
        
        Returns:
            bool: 是否已连接
        """
        return self.connected
    
    def moveJ(self, joint_angles, velocity=50, radius=0):
        """
        执行关节运动(MoveJ)
        
        Args:
            joint_angles (list): 目标关节角度列表，单位为度
            velocity (int): 速度百分比 (0-100)
            radius (float): 交融半径，单位为米（当前不支持，默认为0）
            
        Returns:
            bool: 运动是否成功
        """
        if not self.is_connected():
            print("Not connected to server")
            return False
            
        try:
            # 将角度值转换为整数（单位：0.001度）
            joint_angles_int = [int(angle * 1000) for angle in joint_angles]
            
            # 构建命令
            command = {
                "command": "movej",
                "joint": joint_angles_int,
                "v": velocity,
                "r": radius
            }
            
            # 发送命令，确保以\r\n结尾
            command_str = json.dumps(command) + "\r\n"
            self.socket.sendall(command_str.encode('utf-8'))
            print(f"Sent command: {command_str.strip()}")  # strip()用于打印时去除结尾的\r\n
            
            # 接收响应
            response = self.socket.recv(self.buffer_size)
            response_data = json.loads(response.decode('utf-8'))
            print(f"Received response: {response_data}")
            
            # 检查响应
            if response_data.get("state") == "current_trajectory_state":
                trajectory_state = response_data.get("trajectory_state", False)
                if trajectory_state:
                    print("Successfully moved to target position")
                else:
                    print("Failed to plan trajectory")
                return trajectory_state
            else:
                print("Unexpected response format")
                return False
                
        except socket.timeout:
            print("Timeout while waiting for response")
            return False
            
        except Exception as e:
            print(f"Error during moveJ: {str(e)}")
            return False
    
    def moveL(self, position, orientation, velocity=50, radius=0):
        """
        执行直线运动(MoveL)
        
        Args:
            position (list): 目标位置 [x, y, z]，单位为毫米
            orientation (list): 目标姿态 [rx, ry, rz]，单位为弧度
            velocity (int): 速度百分比 (0-100)
            radius (float): 交融半径，单位为毫米（当前不支持，默认为0）
            
        Returns:
            bool: 运动是否成功
        """
        if not self.is_connected():
            print("Not connected to server")
            return False
            
        try:
            # 将位置值转换为整数（单位：0.001mm）
            position_int = [int(pos * 1000) for pos in position]  # 毫米转换为0.001mm
            
            # 将姿态值转换为整数（单位：0.001rad）
            orientation_int = [int(ori * 1000) for ori in orientation]  # 弧度转换为0.001rad
            
            # 合并位置和姿态
            pose = position_int + orientation_int
            
            # 构建命令
            command = {
                "command": "movel",
                "pose": pose,
                "v": velocity,
                "r": radius
            }
            
            # 发送命令，确保以\r\n结尾
            command_str = json.dumps(command) + "\r\n"
            self.socket.sendall(command_str.encode('utf-8'))
            print(f"Sent command: {command_str.strip()}")  # strip()用于打印时去除结尾的\r\n
            
            # 接收响应
            response = self.socket.recv(self.buffer_size)
            response_data = json.loads(response.decode('utf-8'))
            print(f"Received response: {response_data}")
            
            # 检查响应
            if response_data.get("state") == "current_trajectory_state":
                trajectory_state = response_data.get("trajectory_state", False)
                if trajectory_state:
                    print("Successfully moved to target position")
                else:
                    print("Failed to plan trajectory")
                return trajectory_state
            else:
                print("Unexpected response format")
                return False
                
        except socket.timeout:
            print("Timeout while waiting for response")
            return False
            
        except Exception as e:
            print(f"Error during moveL: {str(e)}")
            return False
    
    def moveC(self, pose_via, pose_to, velocity=50, radius=0, loop=0):
        """
        执行圆弧运动(MoveC)
        
        Args:
            pose_via (list): 中间点位姿 [x,y,z,rx,ry,rz]，位置单位为毫米，姿态单位为弧度
            pose_to (list): 目标点位姿 [x,y,z,rx,ry,rz]，位置单位为毫米，姿态单位为弧度
            velocity (int): 速度百分比 (0-100)
            radius (float): 交融半径（当前不支持，默认为0）
            loop (int): 循环圈数（默认0）
            
        Returns:
            bool: 运动是否成功
        """
        if not self.is_connected():
            print("Not connected to server")
            return False
            
        try:
            # 转换中间点位姿
            pose_via_int = [
                int(pose_via[0] * 1000),  # x: mm -> 0.001mm
                int(pose_via[1] * 1000),  # y: mm -> 0.001mm
                int(pose_via[2] * 1000),  # z: mm -> 0.001mm
                int(pose_via[3] * 1000),  # rx: rad -> 0.001rad
                int(pose_via[4] * 1000),  # ry: rad -> 0.001rad
                int(pose_via[5] * 1000)   # rz: rad -> 0.001rad
            ]
            
            # 转换目标点位姿
            pose_to_int = [
                int(pose_to[0] * 1000),  # x: mm -> 0.001mm
                int(pose_to[1] * 1000),  # y: mm -> 0.001mm
                int(pose_to[2] * 1000),  # z: mm -> 0.001mm
                int(pose_to[3] * 1000),  # rx: rad -> 0.001rad
                int(pose_to[4] * 1000),  # ry: rad -> 0.001rad
                int(pose_to[5] * 1000)   # rz: rad -> 0.001rad
            ]
            
            # 构建命令
            command = {
                "command": "movec",
                "pose": {
                    "pose_via": pose_via_int,
                    "pose_to": pose_to_int
                },
                "v": velocity,
                "r": radius,
                "loop": loop
            }
            
            # 发送命令，确保以\r\n结尾
            command_str = json.dumps(command) + "\r\n"
            self.socket.sendall(command_str.encode('utf-8'))
            print(f"Sent command: {command_str.strip()}")  # strip()用于打印时去除结尾的\r\n
            
            # 接收响应
            response = self.socket.recv(self.buffer_size)
            response_data = json.loads(response.decode('utf-8'))
            print(f"Received response: {response_data}")
            
            # 检查响应
            if response_data.get("state") == "current_trajectory_state":
                trajectory_state = response_data.get("trajectory_state", False)
                if trajectory_state:
                    print("Successfully moved to target position")
                else:
                    print("Failed to plan trajectory")
                return trajectory_state
            else:
                print("Unexpected response format")
                return False
                
        except socket.timeout:
            print("Timeout while waiting for response")
            return False
            
        except Exception as e:
            print(f"Error during moveC: {str(e)}")
            return False
    
    def get_joint_degree(self):
        """
        获取机械臂关节角度
        
        Returns:
            list|None: 成功返回关节角度列表（单位：度），失败返回None
                      关节角度精度为0.001度
        """
        if not self.is_connected():
            print("Not connected to server")
            return None
            
        try:
            # 构建命令
            command = {
                "command": "get_joint_degree"
            }
            
            # 发送命令，确保以\r\n结尾
            command_str = json.dumps(command) + "\r\n"
            self.socket.sendall(command_str.encode('utf-8'))
            print(f"Sent command: {command_str.strip()}")
            
            # 接收响应
            response = self.socket.recv(self.buffer_size)
            response_data = json.loads(response.decode('utf-8'))
            print(f"Received response: {response_data}")
            
            # 检查响应
            if response_data.get("state") == "joint_degree":
                joint_angles = response_data.get("joint", [])
                # 将整数值转换为实际角度（除以1000，因为精度是0.001度）
                joint_angles = [angle / 1000.0 for angle in joint_angles]
                print(f"Current joint angles: {joint_angles}")
                return joint_angles
            else:
                print("Unexpected response format")
                return None
                
        except socket.timeout:
            print("Timeout while waiting for response")
            return None
            
        except Exception as e:
            print(f"Error during get_joint_degree: {str(e)}")
            return None

def main():
    # 测试代码
    arm = RoboticArm()
    
    # 测试连接
    ip = input("Enter IP address to connect (default: 127.0.0.1): ") or "127.0.0.1"
    if arm.connect(ip):
        print("Connection test successful")
        
        try:
            # 获取当前关节角度
            print("\nTesting get_joint_degree...")
            joint_angles = arm.get_joint_degree()
            if joint_angles is not None:
                print(f"Current joint angles: {joint_angles}")
                print("Get joint degree test successful")
            else:
                print("Get joint degree test failed")
            
            # 测试关节运动
            print("\nTesting moveJ...")
            joint_angles = [10.1, 0.2, 20.3, 30.4, 0.5, 20.6]
            success = arm.moveJ(joint_angles, velocity=50)
            if success:
                print("MoveJ test successful")
            else:
                print("MoveJ test failed")
            
            # 测试直线运动
            print("\nTesting moveL...")
            position = [100, 200, 30]  # 毫米
            orientation = [0.4, 0.5, 0.6]  # 弧度
            success = arm.moveL(position, orientation, velocity=50)
            if success:
                print("MoveL test successful")
            else:
                print("MoveL test failed")
                
            # 测试圆弧运动
            print("\nTesting moveC...")
            pose_via = [100, 200, 30, 0.4, 0.5, 0.6]
            pose_to = [200, 300, 30, 0.4, 0.5, 0.6]
            success = arm.moveC(pose_via, pose_to, velocity=50)
            if success:
                print("MoveC test successful")
            else:
                print("MoveC test failed")
                
        finally:
            # 断开连接
            if arm.disconnect():
                print("Disconnection test successful")
    else:
        print("Connection test failed")

if __name__ == "__main__":
    main() 