from art_brain_robot_interface import ArtBrainRobotInterface
from geometry_msgs.msg import PoseStamped
import rospy
from art_gripper import ArtGripper
from brain_utils import ArtBrainUtils
from art_msgs.srv import ReinitArmsRequest, ReinitArmsResponse
from std_srvs.srv import TriggerResponse, TriggerRequest
from std_msgs.msg import Bool
from std_srvs.srv import Empty, EmptyRequest


class ArtPr2Interface(ArtBrainRobotInterface):

    BOTH_ARM = "both_arm"
    LEFT_ARM = "left_arm"
    RIGHT_ARM = "right_arm"

    def __init__(self, robot_parameters, robot_ns, gripper_usage=BOTH_ARM):

        super(ArtPr2Interface, self).__init__(robot_parameters, robot_ns)
        self.gripper_usage = gripper_usage
        self.motors_halted_sub = rospy.Subscriber(
            "/pr2_ethercat/motors_halted", Bool, self.motors_halted_cb)
        self.halt_motors_srv = rospy.ServiceProxy(
            '/pr2_ethercat/halt_motors', Empty)  # TODO wait for service? where?

        self.reset_motors_srv = rospy.ServiceProxy(
            '/pr2_ethercat/reset_motors', Empty)  # TODO wait for service? where?

    def select_arm_for_pick(self, obj, objects_frame_id, tf_listener):
        free_arm = self.select_free_arm()
        if free_arm in [None, self.LEFT_ARM, self.RIGHT_ARM]:
            return free_arm
        objects_frame_id = ArtBrainUtils.normalize_frame_id(objects_frame_id)
        if tf_listener.frameExists(
                "base_link") and tf_listener.frameExists(ArtBrainUtils.normalize_frame_id(objects_frame_id)):
            if obj is not None:
                obj_pose = PoseStamped()
                obj_pose.pose = obj.pose
                obj_pose.header = objects_frame_id
                # exact time does not matter in this case
                obj_pose.header.stamp = rospy.Time(0)
                tf_listener.waitForTransform(
                    'base_link',
                    obj_pose.header.frame_id,
                    obj_pose.header.stamp,
                    rospy.Duration(1))
                obj_pose = tf_listener.transformPose(
                    'base_link', obj_pose)
                if obj_pose.pose.position.y < 0:
                    return self.RIGHT_ARM
                else:
                    return self.LEFT_ARM
        return self.LEFT_ARM

    def select_arm_for_pick_from_feeder(self, pick_pose, tf_listener):
        pick_pose.header.frame_id = ArtBrainUtils.normalize_frame_id(pick_pose.header.frame_id)
        free_arm = self.select_free_arm()
        if free_arm in [None, self.LEFT_ARM, self.RIGHT_ARM]:
            return free_arm
        print pick_pose.header.frame_id
        print tf_listener.frameExists("base_link")
        print tf_listener.frameExists(pick_pose.header.frame_id)
        print pick_pose
        # if tf_listener.frameExists("base_link") and tf_listener.frameExists(pick_pose.header.frame_id) \
        #        and pick_pose is not None:
        pick_pose.header.stamp = rospy.Time(0)
        tf_listener.waitForTransform(
            'base_link',
            pick_pose.header.frame_id,
            pick_pose.header.stamp,
            rospy.Duration(1))
        obj_pose = tf_listener.transformPose(
            'base_link', pick_pose)
        if obj_pose.pose.position.y < 0:
            return self.RIGHT_ARM
        else:
            return self.LEFT_ARM

    def select_free_arm(self):
        left_arm = self.get_arm_by_id(self.LEFT_ARM) if self.gripper_usage in [self.BOTH_ARM,
                                                                               self.LEFT_ARM] else None  # type: ArtGripper
        right_arm = self.get_arm_by_id(self.RIGHT_ARM) if self.gripper_usage in [self.BOTH_ARM,
                                                                                 self.RIGHT_ARM] else None  # type: ArtGripper
        if left_arm is None and right_arm is None:
            return None

        if self.gripper_usage == self.LEFT_ARM:
            if left_arm.holding_object:
                return None
            else:
                return left_arm.arm_id
        elif self.gripper_usage == self.RIGHT_ARM:
            if right_arm.holding_object:
                return None
            else:
                return right_arm.arm_id
        elif self.gripper_usage == self.BOTH_ARM:
            if left_arm.holding_object and not right_arm.holding_object:
                return right_arm.arm_id
            elif not left_arm.holding_object and right_arm.holding_object:
                return left_arm.arm_id
            elif left_arm.holding_object and right_arm.holding_object:
                return None
        return self.BOTH_ARM

    def restore_robot(self):
        self.reset_motors_srv.call(EmptyRequest())
        return True  # TODO: how to check if it worked? wait some time and check topic?

    def emergency_stop(self):
        self.halt_motors_srv.call(EmptyRequest())
        return True  # TODO: how to check if it worked? wait some time and check topic?

    def motors_halted_cb(self, req):

        if self.is_halted() and not req.data:
            self.arms_get_ready()

        self.set_halted(req.data)
