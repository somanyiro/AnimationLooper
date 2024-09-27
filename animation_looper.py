bl_info = {
    "name": "Animation Looper",
    "blender": (4, 3, 0),  # Blender version
    "category": "Animation",
    "author": "Soma Nyiro",
    "version": (0, 1),
    "location": "View3D > Tool Shelf",
    "description": "A simple tool for creating looping animations from motion capture data",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
}

import bpy  # Importing Blender's Python API
from mathutils import Vector, Quaternion

# Define a simple operator (action)
class MakeLoopOperator(bpy.types.Operator):
    bl_idname = "object.make_loop_operator"
    bl_label = "Make Loop"

    ratio: bpy.props.FloatProperty(
        name="Loop Ratio",
        description="Ratio of looping blend between start and end",
        default=0.5,
        min=0.0,
        max=1.0
    )

    dt: bpy.props.FloatProperty(
        name="Time Delta",
        description="Time delta for computing velocity",
        default=1.0 / 60.0
    )
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    
    def execute(self, context):
        # Get the selected object
        obj = context.object
        
        # Ensure the object has animation data
        if obj.animation_data is None or obj.animation_data.action is None:
            self.report({'ERROR'}, "Selected object has no animation data")
            return {'CANCELLED'}

        # Call the loop_animation function with the selected object
        try:
            loop_animation(obj.name, self.ratio, self.dt)
            self.report({'INFO'}, f"Looped animation for {obj.name}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to loop animation: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}
    
    
def loop_animation(object_name, ratio, dt):
    obj = bpy.data.objects[object_name]
    action = obj.animation_data.action
    
    # Assuming we're working with bone animations in an armature
    bones = obj.pose.bones
    num_frames = int(action.frame_range[1] - action.frame_range[0])
    
    # Gather raw bone positions and rotations over time (fcurve sampling)
    raw_bone_positions = []
    raw_bone_rotations = []
    
    for frame in range(num_frames):
        bpy.context.scene.frame_set(frame)
        raw_bone_positions.append([bone.location.copy() for bone in bones])
        raw_bone_rotations.append([bone.rotation_quaternion.copy() for bone in bones])
    
    # Prepare arrays to store the looped results
    looped_bone_positions = [[Vector() for _ in bones] for _ in range(num_frames)]
    looped_bone_rotations = [[Quaternion() for _ in bones] for _ in range(num_frames)]
    offset_bone_positions = [[Vector() for _ in bones] for _ in range(num_frames)]
    offset_bone_rotations = [[Vector() for _ in bones] for _ in range(num_frames)]
    
    # Calculate positional and rotational differences
    pos_diff, vel_diff = compute_start_end_positional_difference(raw_bone_positions, dt)
    rot_diff, ang_diff = compute_start_end_rotational_difference(raw_bone_rotations, dt)
    
    # Compute offsets
    compute_linear_offsets(offset_bone_positions, pos_diff, ratio)
    compute_linear_offsets(offset_bone_rotations, rot_diff, ratio)
    
    # Apply offsets
    apply_positional_offsets(looped_bone_positions, raw_bone_positions, offset_bone_positions)
    apply_rotational_offsets(looped_bone_rotations, raw_bone_rotations, offset_bone_rotations)
    
    # Write the looped animation back to Blender
    for frame in range(num_frames):
        bpy.context.scene.frame_set(frame)
        for idx, bone in enumerate(bones):
            bone.location = looped_bone_positions[frame][idx]
            bone.rotation_quaternion = looped_bone_rotations[frame][idx]
        bpy.context.view_layer.update()

    bpy.context.scene.frame_set(0)



def compute_start_end_positional_difference(pos, dt):
    pos_diff = []
    vel_diff = []
    for j in range(len(pos[0])):
        diff_pos = pos[-1][j] - pos[0][j]
        diff_vel = ((pos[-1][j] - pos[-2][j]) / dt) - ((pos[1][j] - pos[0][j]) / dt)
        pos_diff.append(diff_pos)
        vel_diff.append(diff_vel)
    return pos_diff, vel_diff


def compute_start_end_rotational_difference(rot, dt):
    rot_diff = []
    vel_diff = []
    for j in range(len(rot[0])):
        diff_rot = quat_to_scaled_angle_axis(rot[-1][j].rotation_difference(rot[0][j]))
        diff_vel = quat_differentiate_angular_velocity(rot[-1][j], rot[-2][j], dt) - \
                quat_differentiate_angular_velocity(rot[1][j], rot[0][j], dt)
        rot_diff.append(diff_rot)
        vel_diff.append(diff_vel)
    return rot_diff, vel_diff


def quat_to_scaled_angle_axis(q):
    return q.axis * q.angle


def quat_differentiate_angular_velocity(q1, q2, dt):
    delta_q = q1.rotation_difference(q2)
    axis, angle = delta_q.axis, delta_q.angle
    return axis * (angle / dt)


def compute_linear_offsets(offsets, diff, ratio):
    for i in range(len(offsets)):
        for j in range(len(offsets[i])):
            factor = ratio * (ratio - 1.0) * (i / (len(offsets) - 1))
            offsets[i][j] = factor * diff[j]


def apply_positional_offsets(looped_positions, raw_positions, offsets):
    for i in range(len(raw_positions)):
        for j in range(len(raw_positions[i])):
            looped_positions[i][j] = raw_positions[i][j] + offsets[i][j]

def apply_rotational_offsets(looped_rotations, raw_rotations, offsets):
        for i in range(len(raw_rotations)):
            for j in range(len(raw_rotations[i])):
                looped_rotations[i][j] = Quaternion(offsets[i][j]).normalized() @ raw_rotations[i][j]


class RemoveRootMotionOperator(bpy.types.Operator):
    bl_idname = "object.remove_root_motion_operator"
    bl_label = "Remove Root Motion"
    bl_description = "Remove keyframes on X and Z axes for the Hips bone"

    def execute(self, context):
        obj = context.object  # Get the currently selected object
        
        # Check if an armature is selected and it has animation data
        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "No armature selected")
            return {'CANCELLED'}
        
        if obj.animation_data is None or obj.animation_data.action is None:
            self.report({'WARNING'}, "No animation data found")
            return {'CANCELLED'}
        
        action = obj.animation_data.action  # Access the animation action

        # Loop through the F-Curves to find the keyframes for the "Hips" bone's location
        for fcurve in action.fcurves:
            # We need to target the 'pose.bones["Hips"].location' data path
            if fcurve.data_path == 'pose.bones["Hips"].location':
                # For X-axis (location[0]) and Z-axis (location[2])
                if fcurve.array_index == 0:  # X-axis (location[0])
                    self.report({'INFO'}, "Zeroing X-axis keyframes for Hips")
                    for keyframe in fcurve.keyframe_points:
                        keyframe.co[1] = 0  # Set the keyframe value (Y-coordinate) to 0

                elif fcurve.array_index == 2:  # Z-axis (location[2])
                    self.report({'INFO'}, "Zeroing Z-axis keyframes for Hips")
                    for keyframe in fcurve.keyframe_points:
                        keyframe.co[1] = 0  # Set the keyframe value (Y-coordinate) to 0
        
        return {'FINISHED'}
    

class MakeLoopPanel(bpy.types.Panel):
    bl_label = "Make Loop Panel"  # Panel label
    bl_idname = "OBJECT_PT_make_loop_panel"  # Unique identifier for the panel
    bl_space_type = 'VIEW_3D'  # Where this panel will appear
    bl_region_type = 'UI'  # The region of the interface
    bl_category = "Tool"  # The tab where it will appear

    def draw(self, context):
        layout = self.layout

        layout.operator("object.make_loop_operator")
        layout.operator("object.remove_root_motion_operator")

def register():
    bpy.utils.register_class(MakeLoopOperator)
    bpy.utils.register_class(MakeLoopPanel)
    bpy.utils.register_class(RemoveRootMotionOperator)

def unregister():
    bpy.utils.unregister_class(MakeLoopOperator)
    bpy.utils.unregister_class(MakeLoopPanel)
    bpy.utils.unregister_class(RemoveRootMotionOperator)

if __name__ == "__main__":
    register()
