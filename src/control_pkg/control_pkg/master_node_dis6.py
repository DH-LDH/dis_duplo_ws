# import time

# import rclpy
# from rclpy.node import Node
# from srvs_pkg.srv import GetTargetPose
# from std_srvs.srv import SetBool, Trigger


# class BatteryDualDisassembly(Node):
#     def __init__(self):
#         super().__init__("master_node_dis6")

#         self.cli_v1 = self.create_client(GetTargetPose, "/get_target_pose")
#         self.cli_r1 = self.create_client(GetTargetPose, "/robot1/robot_move_step")
#         self.cli_r2 = self.create_client(GetTargetPose, "/robot2/robot_move_step")
#         self.cli_h1 = self.create_client(Trigger, "/robot1/robot_home")
#         self.cli_h2 = self.create_client(Trigger, "/robot2/robot_home")

#         self.robot1_gripper_service = self.declare_parameter(
#             "robot1_gripper_service",
#             "/control_gripper",
#         ).value
#         self.robot2_gripper_service = self.declare_parameter(
#             "robot2_gripper_service",
#             "/robot2/control_gripper",
#         ).value
#         self.cli_g1 = self.create_client(SetBool, self.robot1_gripper_service)
#         self.cli_g2 = self.create_client(SetBool, self.robot2_gripper_service)

#         self.wait_time = float(self.declare_parameter("wait_time", 1.5).value)
#         self.grip_wait_time = float(self.declare_parameter("grip_wait_time", 2.5).value)

#         self.z_off = float(self.declare_parameter("robot1_z_off", -85.0).value)
#         self.z_margin = float(self.declare_parameter("robot1_z_margin", 20.0).value)
#         self.robot1_initial_lift_mm = float(self.declare_parameter("robot1_initial_lift_mm", -20.0).value)
#         self.robot1_pull_up_mm = float(self.declare_parameter("robot1_pull_up_mm", -20.0).value)
        
#         # 로봇 1이 바닥에 내려놓을 때 겹치지 않게 우측으로 살짝 이동하는 값 (필요시 0으로 수정 가능)
#         self.robot1_place_right_x_mm = float(self.declare_parameter("robot1_place_right_x_mm", -100.0).value)
#         self.robot1_place_right_y_mm = float(self.declare_parameter("robot1_place_right_y_mm", 0.0).value)
#         self.robot1_place_down_mm = float(self.declare_parameter("robot1_place_down_mm", 20.0).value)

#         self.robot1_cam_x_off = -53.0
#         self.robot1_cam_y_off = 32.0
#         self.robot2_cam_x_off = -53.0
#         self.robot2_cam_y_off = 32.0

#         self.get_logger().info(
#             "Battery dual disassembly ready (Updated Sequence). "
#             f"g1={self.robot1_gripper_service}, g2={self.robot2_gripper_service}"
#         )

#     def call(self, cli, req):
#         while not cli.wait_for_service(timeout_sec=1.0):
#             self.get_logger().info(f"Waiting for {cli.srv_name}...")
#         future = cli.call_async(req)
#         rclpy.spin_until_future_complete(self, future)
#         return future.result()

#     def sleep(self):
#         time.sleep(self.wait_time)

#     def set_gripper(self, cli, closed):
#         res = self.call(cli, SetBool.Request(data=closed))
#         time.sleep(self.grip_wait_time)
#         return res.success

#     def move_z(self, cli, dz_mm):
#         req = GetTargetPose.Request()
#         req.target_size = "Z"
#         req.z = dz_mm
#         return self.call(cli, req).success

#     def move_xy_relative_via_camera_service(self, cli, robot_name, tool_x_mm, tool_y_mm):
#         if robot_name == "robot1":
#             cam_x_off = self.robot1_cam_x_off
#             cam_y_off = self.robot1_cam_y_off
#         else:
#             cam_x_off = self.robot2_cam_x_off
#             cam_y_off = self.robot2_cam_y_off

#         req = GetTargetPose.Request()
#         req.target_size = "XY"
#         req.x = (cam_y_off - tool_y_mm) / 1000.0
#         req.y = (tool_x_mm - cam_x_off) / 1000.0
#         return self.call(cli, req).success

#     def find_target_with_retry(self, color, retries=3):
#         for i in range(retries):
#             p = self.call(self.cli_v1, GetTargetPose.Request(target_color=color))
#             if p.success:
#                 return p
#             time.sleep(0.5) 
#         return None

#     def move_robot1_separation_pose(self):
#         req = GetTargetPose.Request()
#         req.target_size = "SEPARATION"
#         return self.call(self.cli_r1, req).success

#     def move_robot2_separation_pose(self):
#         req = GetTargetPose.Request()
#         req.target_size = "SEPARATION"
#         return self.call(self.cli_r2, req).success

#     # 신규: 로봇 2가 파랑 블럭을 내려놓을 특정 자세로 이동
#     def move_robot2_drop_pose(self):
#         req = GetTargetPose.Request()
#         req.target_size = "DROP"
#         return self.call(self.cli_r2, req).success

#     def robot1_top_pick_yellow(self):
#         target = "2x2_yellow"
#         self.get_logger().info(f"1) robot1: 비전 3단계 스캔 시작 [{target}]")

#         p = self.find_target_with_retry(target)
#         if not p:
#             self.get_logger().error("robot1: 1차 스캔(Yaw) 실패")
#             return False
#         req_yaw = GetTargetPose.Request()
#         req_yaw.target_size = "YAW"
#         req_yaw.yaw = p.yaw
#         self.call(self.cli_r1, req_yaw)
#         self.sleep()

#         p = self.find_target_with_retry(target)
#         if not p:
#             self.get_logger().error("robot1: 2차 스캔(XY) 실패")
#             return False
#         req_xy = GetTargetPose.Request()
#         req_xy.target_size = "XY"
#         req_xy.x = p.x
#         req_xy.y = p.y
#         self.call(self.cli_r1, req_xy)
#         self.sleep()

#         p = self.find_target_with_retry(target)
#         if not p:
#             self.get_logger().error("robot1: 3차 스캔(Z) 실패")
#             return False
        
#         z_move = (p.z * 1000.0) + self.z_off
#         self.move_z(self.cli_r1, z_move - self.z_margin)
#         self.sleep()
#         self.move_z(self.cli_r1, self.z_margin)
#         self.sleep()

#         self.set_gripper(self.cli_g1, True)
#         self.sleep()
        
#         self.move_z(self.cli_r1, self.robot1_initial_lift_mm)
#         self.sleep()

#         self.get_logger().info("robot1: 물체 분리 자세 이동")
#         self.move_robot1_separation_pose()
#         self.sleep()
#         return True

#     def robot2_side_hold_blue(self):
#         self.get_logger().info("2) robot2: 지정된 조인트(관절) 각도로 이동하여 하단 고정")
#         if not self.move_robot2_separation_pose():
#             self.get_logger().error("robot2: 고정 자세 이동 실패")
#             return False
#         self.sleep()

#         self.set_gripper(self.cli_g2, True)
#         return True

#     def robot1_pull_up(self):
#         self.get_logger().info("3) robot1: 노랑 블럭 2cm 추가 상승하여 강제 분리")
#         self.move_z(self.cli_r1, self.robot1_pull_up_mm)
#         self.sleep()
#         return True

#     def robot2_return_home_holding(self):
#         self.get_logger().info("4) robot2: 그리퍼 닫은 상태로 홈 위치 복귀")
#         self.call(self.cli_h2, Trigger.Request())
#         self.sleep()
#         return True

#     def robot1_place_yellow_and_home(self):
#         self.get_logger().info("5) robot1: 노랑 블럭 바닥에 내려놓고 홈 위치 복귀")
        
#         # (옵션) 제자리에서 바로 내리고 싶다면 아래 move_xy_relative 라인을 주석 처리하시면 됩니다.
#         self.move_xy_relative_via_camera_service(
#             self.cli_r1, "robot1", self.robot1_place_right_x_mm, self.robot1_place_right_y_mm
#         )
#         self.sleep()
        
#         self.move_z(self.cli_r1, self.robot1_place_down_mm)
#         self.sleep()
#         self.set_gripper(self.cli_g1, False)
#         self.sleep()
        
#         # 놓은 뒤 살짝 위로 다시 빠져나옴
#         self.move_z(self.cli_r1, -self.robot1_place_down_mm)
#         self.sleep()
        
#         # 로봇 1 홈으로 복귀
#         self.call(self.cli_h1, Trigger.Request())
#         self.sleep()
#         return True

#     def robot2_drop_blue(self):
#         self.get_logger().info("6) robot2: 지정된 조인트로 이동하여 파랑 블럭 내려놓기")
#         self.move_robot2_drop_pose()
#         self.sleep()
#         self.set_gripper(self.cli_g2, False)
#         self.sleep()
#         return True

#     def run_battery_once(self):
#         self.get_logger().info("배터리 협조 분해 시작")
#         self.call(self.cli_h1, Trigger.Request())
#         self.call(self.cli_h2, Trigger.Request())
#         self.set_gripper(self.cli_g1, False)
#         self.set_gripper(self.cli_g2, False)

#         # 1. 로봇1 스캔 -> 파지 -> 분리자세
#         if not self.robot1_top_pick_yellow(): return False
#         # 2. 로봇2 분리자세 -> 하단 고정
#         if not self.robot2_side_hold_blue(): return False
#         # 3. 로봇1 잡아당기기
#         if not self.robot1_pull_up(): return False
#         # 4. 로봇2 홈으로 복귀 (잡은 상태 유지)
#         if not self.robot2_return_home_holding(): return False
#         # 5. 로봇1 바닥에 놓고 홈으로 복귀
#         if not self.robot1_place_yellow_and_home(): return False
#         # 6. 로봇2 드랍 조인트로 이동하여 내려놓기
#         if not self.robot2_drop_blue(): return False

#         # 마지막으로 로봇 2도 홈으로 복귀하며 종료
#         self.call(self.cli_h2, Trigger.Request())
#         self.get_logger().info("배터리 협조 분해 완료")
#         return True

#     def run(self):
#         print("\n=== Battery Dual Disassembly Test ===")
#         self.get_logger().info("확인 입력 없이 바로 시작합니다.")
#         self.run_battery_once()


# def main():
#     rclpy.init()
#     node = BatteryDualDisassembly()
#     try:
#         node.run()
#     finally:
#         node.destroy_node()
#         rclpy.shutdown()


# if __name__ == "__main__":
#     main()

import time

import rclpy
from rclpy.node import Node
from srvs_pkg.srv import GetTargetPose
from std_srvs.srv import SetBool, Trigger


class BatteryDualDisassembly(Node):
    def __init__(self):
        super().__init__("master_node_dis6")

        self.cli_v1 = self.create_client(GetTargetPose, "/get_target_pose")
        self.cli_r1 = self.create_client(GetTargetPose, "/robot1/robot_move_step")
        self.cli_r2 = self.create_client(GetTargetPose, "/robot2/robot_move_step")
        self.cli_h1 = self.create_client(Trigger, "/robot1/robot_home")
        self.cli_h2 = self.create_client(Trigger, "/robot2/robot_home")

        self.robot1_gripper_service = self.declare_parameter(
            "robot1_gripper_service",
            "/control_gripper",
        ).value
        self.robot2_gripper_service = self.declare_parameter(
            "robot2_gripper_service",
            "/robot2/control_gripper",
        ).value
        self.cli_g1 = self.create_client(SetBool, self.robot1_gripper_service)
        self.cli_g2 = self.create_client(SetBool, self.robot2_gripper_service)

        self.wait_time = float(self.declare_parameter("wait_time", 1.5).value)
        self.grip_wait_time = float(self.declare_parameter("grip_wait_time", 2.5).value)

        self.z_off = float(self.declare_parameter("robot1_z_off", -85.0).value)
        self.z_margin = float(self.declare_parameter("robot1_z_margin", 20.0).value)
        self.robot1_initial_lift_mm = float(self.declare_parameter("robot1_initial_lift_mm", -20.0).value)
        self.robot1_pull_up_mm = float(self.declare_parameter("robot1_pull_up_mm", -20.0).value)

        self.robot1_cam_x_off = -53.0
        self.robot1_cam_y_off = 32.0
        self.robot2_cam_x_off = -53.0
        self.robot2_cam_y_off = 32.0

        self.get_logger().info(
            "Battery dual disassembly ready (Final Perfect Sequence). "
            f"g1={self.robot1_gripper_service}, g2={self.robot2_gripper_service}"
        )

    def call(self, cli, req):
        while not cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f"Waiting for {cli.srv_name}...")
        future = cli.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

    def sleep(self):
        time.sleep(self.wait_time)

    def set_gripper(self, cli, closed):
        res = self.call(cli, SetBool.Request(data=closed))
        time.sleep(self.grip_wait_time)
        return res.success

    def move_z(self, cli, dz_mm):
        req = GetTargetPose.Request()
        req.target_size = "Z"
        req.z = dz_mm
        return self.call(cli, req).success

    def find_target_with_retry(self, color, retries=3):
        for i in range(retries):
            p = self.call(self.cli_v1, GetTargetPose.Request(target_color=color))
            if p.success:
                return p
            time.sleep(0.5) 
        return None

    def move_robot1_separation_pose(self):
        req = GetTargetPose.Request()
        req.target_size = "SEPARATION"
        return self.call(self.cli_r1, req).success

    def move_robot2_separation_pose(self):
        req = GetTargetPose.Request()
        req.target_size = "SEPARATION"
        return self.call(self.cli_r2, req).success

    def move_robot1_drop_pose(self):
        req = GetTargetPose.Request()
        req.target_size = "DROP"
        return self.call(self.cli_r1, req).success

    def move_robot2_drop_pose(self):
        req = GetTargetPose.Request()
        req.target_size = "DROP"
        return self.call(self.cli_r2, req).success

    def robot1_top_pick_yellow(self):
        target = "2x2_yellow"
        self.get_logger().info(f"1) robot1: 비전 3단계 스캔 시작 [{target}]")

        p = self.find_target_with_retry(target)
        if not p:
            self.get_logger().error("robot1: 1차 스캔(Yaw) 실패")
            return False
        req_yaw = GetTargetPose.Request()
        req_yaw.target_size = "YAW"
        req_yaw.yaw = p.yaw
        self.call(self.cli_r1, req_yaw)
        self.sleep()

        p = self.find_target_with_retry(target)
        if not p:
            self.get_logger().error("robot1: 2차 스캔(XY) 실패")
            return False
        req_xy = GetTargetPose.Request()
        req_xy.target_size = "XY"
        req_xy.x = p.x
        req_xy.y = p.y
        self.call(self.cli_r1, req_xy)
        self.sleep()

        p = self.find_target_with_retry(target)
        if not p:
            self.get_logger().error("robot1: 3차 스캔(Z) 실패")
            return False
        
        z_move = (p.z * 1000.0) + self.z_off
        self.move_z(self.cli_r1, z_move - self.z_margin)
        self.sleep()
        self.move_z(self.cli_r1, self.z_margin)
        self.sleep()

        self.set_gripper(self.cli_g1, True)
        self.sleep()
        
        self.move_z(self.cli_r1, self.robot1_initial_lift_mm)
        self.sleep()

        self.get_logger().info("robot1: 물체 분리 자세 이동")
        self.move_robot1_separation_pose()
        self.sleep()
        return True

    def robot2_side_hold_blue(self):
        self.get_logger().info("2) robot2: 지정된 분리 조인트로 이동하여 하단 고정")
        if not self.move_robot2_separation_pose():
            self.get_logger().error("robot2: 고정 자세 이동 실패")
            return False
        self.sleep()

        self.set_gripper(self.cli_g2, True)
        return True

    def robot1_pull_up(self):
        self.get_logger().info("3) robot1: 노랑 블럭 2cm 추가 상승하여 강제 분리")
        self.move_z(self.cli_r1, self.robot1_pull_up_mm)
        self.sleep()
        return True

    def robot2_return_home_holding(self):
        self.get_logger().info("4) robot2: 파랑 블럭 잡은 상태로 홈 위치 복귀")
        self.call(self.cli_h2, Trigger.Request())
        self.sleep()
        return True

    def robot1_drop_yellow_and_home(self):
        self.get_logger().info("5) robot1: 노랑 블럭 DROP 조인트로 이동하여 내려놓고 홈 복귀")
        if not self.move_robot1_drop_pose():
            self.get_logger().error("robot1: DROP 자세 이동 실패")
            return False
        self.sleep()
        
        self.set_gripper(self.cli_g1, False)
        self.sleep()
        
        self.call(self.cli_h1, Trigger.Request())
        self.sleep()
        return True

    def robot2_drop_blue_and_home(self):
        self.get_logger().info("6) robot2: 파랑 블럭 DROP 조인트로 이동하여 내려놓고 홈 복귀")
        if not self.move_robot2_drop_pose():
            self.get_logger().error("robot2: DROP 자세 이동 실패")
            return False
        self.sleep()
        
        self.set_gripper(self.cli_g2, False)
        self.sleep()

        self.call(self.cli_h2, Trigger.Request())
        self.sleep()
        return True

    def run_battery_once(self):
        self.get_logger().info("배터리 협조 분해 시작")
        self.call(self.cli_h1, Trigger.Request())
        self.call(self.cli_h2, Trigger.Request())
        self.set_gripper(self.cli_g1, False)
        self.set_gripper(self.cli_g2, False)

        # 1. 로봇1 스캔 -> 파지 -> 분리자세 이동
        if not self.robot1_top_pick_yellow(): return False
        
        # 2. 로봇2 분리자세 이동 -> 하단 고정
        if not self.robot2_side_hold_blue(): return False
        
        # 3. 로봇1 잡아당기기 (분리)
        if not self.robot1_pull_up(): return False
        
        # 4. 로봇2 홈으로 복귀 (그리퍼 닫은 상태 유지)
        if not self.robot2_return_home_holding(): return False
        
        # 5. 로봇1 DROP 조인트로 이동 -> 내려놓기 -> 홈 복귀
        if not self.robot1_drop_yellow_and_home(): return False
        
        # 6. 로봇2 DROP 조인트로 이동 -> 내려놓기 -> 홈 복귀
        if not self.robot2_drop_blue_and_home(): return False

        self.get_logger().info("🎉 배터리 협조 분해 완벽 종료")
        return True

    def run(self):
        print("\n=== Battery Dual Disassembly Test ===")
        self.get_logger().info("확인 입력 없이 바로 시작합니다.")
        self.run_battery_once()


def main():
    rclpy.init()
    node = BatteryDualDisassembly()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()