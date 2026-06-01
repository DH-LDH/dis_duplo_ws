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
        self.robot1_place_right_x_mm = float(self.declare_parameter("robot1_place_right_x_mm", -100.0).value)
        self.robot1_place_right_y_mm = float(self.declare_parameter("robot1_place_right_y_mm", 0.0).value)
        self.robot1_place_down_mm = float(self.declare_parameter("robot1_place_down_mm", 20.0).value)
        self.robot2_place_down_mm = float(self.declare_parameter("robot2_place_down_mm", 15.0).value)

        # robot_node2의 XY 변환식 역산용 기본 오프셋입니다.
        self.robot1_cam_x_off = -53.0
        self.robot1_cam_y_off = 32.0
        self.robot2_cam_x_off = -53.0
        self.robot2_cam_y_off = 32.0

        self.get_logger().info(
            "Battery dual disassembly ready (with 3-step Vision Scan). "
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

    def move_xy_relative_via_camera_service(self, cli, robot_name, tool_x_mm, tool_y_mm):
        if robot_name == "robot1":
            cam_x_off = self.robot1_cam_x_off
            cam_y_off = self.robot1_cam_y_off
        else:
            cam_x_off = self.robot2_cam_x_off
            cam_y_off = self.robot2_cam_y_off

        req = GetTargetPose.Request()
        req.target_size = "XY"
        req.x = (cam_y_off - tool_y_mm) / 1000.0
        req.y = (tool_x_mm - cam_x_off) / 1000.0
        return self.call(cli, req).success

    # ===== [수정됨] 기존 3단계 비전 스캔 로직 복구 =====
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

    # ===== [수정됨] 로봇 1 파지 시퀀스: 3번 반복 확인 로직 적용 =====
    def robot1_top_pick_yellow(self):
        target = "2x2_yellow"
        self.get_logger().info(f"1) robot1: 비전 3단계 스캔 시작 [{target}]")

        # 1차 스캔: Yaw 측정 및 회전
        p = self.find_target_with_retry(target)
        if not p:
            self.get_logger().error("robot1: 1차 스캔(Yaw) 실패")
            return False
        self.get_logger().info(f"robot1: 1차 스캔 - Yaw 회전 ({p.yaw:.1f})")
        req_yaw = GetTargetPose.Request()
        req_yaw.target_size = "YAW"
        req_yaw.yaw = p.yaw
        self.call(self.cli_r1, req_yaw)
        self.sleep()

        # 2차 스캔: XY 측정 및 이동
        p = self.find_target_with_retry(target)
        if not p:
            self.get_logger().error("robot1: 2차 스캔(XY) 실패")
            return False
        self.get_logger().info(f"robot1: 2차 스캔 - XY 정렬 (x={p.x:.4f}, y={p.y:.4f})")
        req_xy = GetTargetPose.Request()
        req_xy.target_size = "XY"
        req_xy.x = p.x
        req_xy.y = p.y
        self.call(self.cli_r1, req_xy)
        self.sleep()

        # 3차 스캔: Z(깊이) 측정 및 하강 파지
        p = self.find_target_with_retry(target)
        if not p:
            self.get_logger().error("robot1: 3차 스캔(Z) 실패")
            return False
        self.get_logger().info(f"robot1: 3차 스캔 - Z 하강 파지 (z={p.z:.4f})")
        
        z_move = (p.z * 1000.0) + self.z_off
        self.move_z(self.cli_r1, z_move - self.z_margin)
        self.sleep()
        self.move_z(self.cli_r1, self.z_margin)
        self.sleep()

        self.set_gripper(self.cli_g1, True)
        self.sleep()
        
        # 바닥 간섭 회피를 위한 초기 상승
        self.move_z(self.cli_r1, self.robot1_initial_lift_mm)
        self.sleep()

        self.get_logger().info("robot1: 물체 분리 자세 이동")
        self.move_robot1_separation_pose()
        self.sleep()
        return True

    def robot2_side_hold_blue(self):
        self.get_logger().info("2) robot2: 지정된 조인트(관절) 각도로 이동하여 하단 고정")

        if not self.move_robot2_separation_pose():
            self.get_logger().error("robot2: 고정 자세 이동 실패")
            return False
        self.sleep()

        self.set_gripper(self.cli_g2, True)
        return True

    def robot1_pull_and_place_yellow(self):
        self.get_logger().info("3) robot1: 노랑 블럭 2cm 추가 상승 후 오른쪽에 내려놓기")
        self.move_z(self.cli_r1, self.robot1_pull_up_mm)
        self.sleep()
        self.move_xy_relative_via_camera_service(
            self.cli_r1,
            "robot1",
            self.robot1_place_right_x_mm,
            self.robot1_place_right_y_mm,
        )
        self.sleep()
        self.move_z(self.cli_r1, self.robot1_place_down_mm)
        self.sleep()
        self.set_gripper(self.cli_g1, False)
        self.move_z(self.cli_r1, -self.robot1_place_down_mm)
        self.sleep()
        return True

    def robot2_place_blue(self):
        self.get_logger().info("4) robot2: 잡고 있던 파랑 블럭을 조금 내려놓고 해제")
        self.move_z(self.cli_r2, self.robot2_place_down_mm)
        self.sleep()
        self.set_gripper(self.cli_g2, False)
        self.move_z(self.cli_r2, -self.robot2_place_down_mm)
        self.sleep()
        return True

    def run_battery_once(self):
        self.get_logger().info("배터리 협조 분해 시작: 2x2_yellow / 2x2_blue")
        self.call(self.cli_h1, Trigger.Request())
        self.call(self.cli_h2, Trigger.Request())
        self.set_gripper(self.cli_g1, False)
        self.set_gripper(self.cli_g2, False)

        if not self.robot1_top_pick_yellow():
            return False
        if not self.robot2_side_hold_blue():
            return False
        if not self.robot1_pull_and_place_yellow():
            return False
        if not self.robot2_place_blue():
            return False

        self.call(self.cli_h1, Trigger.Request())
        self.call(self.cli_h2, Trigger.Request())
        self.get_logger().info("배터리 협조 분해 완료")
        return True

    def run(self):
        print("\n=== Battery Dual Disassembly Test ===")
        print("Required services:")
        print("  /get_target_pose")
        print("  /robot1/robot_move_step, /robot2/robot_move_step")
        print("  /robot1/robot_home, /robot2/robot_home")
        print(f"  {self.robot1_gripper_service}, {self.robot2_gripper_service}")
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