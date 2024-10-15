bl_info = {
    "name": "Animation Looper",
    "blender": (4, 3, 0),
    "category": "Animation",
    "author": "Soma Nyiro",
    "version": (0, 1),
    "location": "View3D > Tool Shelf",
    "description": "A simple tool for creating looping animations from motion capture data",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
}

import bpy
from mathutils import Vector, Quaternion

class LoopAnimationOperator(bpy.types.Operator):
    bl_idname = "object.loop_animation_operator"
    bl_label = "Loop Animation"

    ratio: bpy.props.FloatProperty(
        name="Loop Ratio",
        description="Ratio of looping blend between start and end",
        default=0.5,
        min=0.0,
        max=1.0
    )

    action_enum: bpy.props.EnumProperty(
        name="Select Animation",
        description="Choose an animation to loop",
        items=lambda self, context: get_actions_enum(context)
    )

    dt = 1.0/60.0

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.object
        
        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "No armature selected")
            return {'CANCELLED'}
        
        if obj.animation_data is None or obj.animation_data.action is None:
            self.report({'ERROR'}, "Selected object has no animation data")
            return {'CANCELLED'}

        if self.action_enum == 'NONE':
            self.report({'ERROR'}, "No animation selected")
            return {'CANCELLED'}

        obj.animation_data.action = bpy.data.actions.get(self.action_enum)

        snap_keys_to_frames(obj.animation_data.action)

        try:
            loop_animation(obj, self.ratio, self.dt, self)
            self.report({'INFO'}, f"Looped animation for {obj.name}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to loop animation: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}

def get_actions_enum(context):
        obj = context.object
        if obj and obj.type == 'ARMATURE' and obj.animation_data:
            actions = [(action.name, action.name, "") for action in bpy.data.actions]
            if actions:
                return actions
        return [('NONE', 'None', '')]

def loop_animation(obj, ratio, dt, op):
    action = obj.animation_data.action
    
    bones = obj.pose.bones
    num_frames = int(action.frame_range[1] - action.frame_range[0])+1
    
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
    fcurves_location = {bone.name: [] for bone in bones}
    fcurves_rotation = {bone.name: [] for bone in bones}

    for fcurve in action.fcurves:
        for bone in bones:
            if f'pose.bones["{bone.name}"].location' in fcurve.data_path:
                fcurves_location[bone.name].append(fcurve)
            elif f'pose.bones["{bone.name}"].rotation_quaternion' in fcurve.data_path:
                fcurves_rotation[bone.name].append(fcurve)

    for bone_idx, bone in enumerate(bones):
        bone_name = bone.name
        
        if bone_name in fcurves_location:
            for axis, fcurve in enumerate(fcurves_location[bone_name]):
                if fcurve is not None:
                    for keyframe in fcurve.keyframe_points:
                        frame = int(round(keyframe.co[0]))
                        if 0 <= frame < num_frames:
                            keyframe.co[1] = looped_bone_positions[frame][bone_idx][axis]

        if bone_name in fcurves_rotation:
            for axis, fcurve in enumerate(fcurves_rotation[bone_name]):
                if fcurve is not None:
                    for keyframe in fcurve.keyframe_points:
                        frame = int(round(keyframe.co[0]))
                        if 0 <= frame < num_frames:
                            keyframe.co[1] = looped_bone_rotations[frame][bone_idx][axis]

    for fcurves in [fcurves_location, fcurves_rotation]:
        for bone_fcurves in fcurves.values():
            for fcurve in bone_fcurves:
                if fcurve is not None:
                    fcurve.update()
    
    bpy.context.view_layer.update()



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
        diff_rot = quat_to_scaled_angle_axis(rot[0][j].rotation_difference(rot[-1][j]))
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
            offsets[i][j] = lerp(ratio, ratio-1.0, i / (len(offsets) - 1)) * diff[j]


def apply_positional_offsets(looped_positions, raw_positions, offsets):
    for i in range(len(raw_positions)):
        for j in range(len(raw_positions[i])):
            looped_positions[i][j] = raw_positions[i][j] + offsets[i][j]

def apply_rotational_offsets(looped_rotations, raw_rotations, offsets):
        for i in range(len(raw_rotations)):
            for j in range(len(raw_rotations[i])):
                looped_rotations[i][j] = raw_rotations[i][j] @ Quaternion(offsets[i][j])

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def snap_keys_to_frames(action):
    for fcurve in action.fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.co[0] = round(keyframe.co[0])
        fcurve.update()

class RemoveRootMotionOperator(bpy.types.Operator):
    bl_idname = "object.remove_root_motion_operator"
    bl_label = "Remove Root Motion"
    bl_description = "Remove keyframes on the Hips bone"

    x: bpy.props.BoolProperty(default=True)
    y: bpy.props.BoolProperty(default=False)
    z: bpy.props.BoolProperty(default=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.object
        
        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "No armature selected")
            return {'CANCELLED'}
        
        if obj.animation_data is None or obj.animation_data.action is None:
            self.report({'WARNING'}, "No animation data found")
            return {'CANCELLED'}
        
        action = obj.animation_data.action

        for fcurve in action.fcurves:
            if fcurve.data_path == 'pose.bones["Hips"].location':
                if fcurve.array_index == 0 and self.x:
                    for keyframe in fcurve.keyframe_points:
                        keyframe.co[1] = 0

                elif fcurve.array_index == 1 and self.y:
                    for keyframe in fcurve.keyframe_points:
                        keyframe.co[1] = 0

                elif fcurve.array_index == 2 and self.z:
                    for keyframe in fcurve.keyframe_points:
                        keyframe.co[1] = 0
        
        if self.x:
            self.report({'INFO'}, "Root motion removed on x-axis")
        if self.y:
            self.report({'INFO'}, "Root motion removed on y-axis")
        if self.z:
            self.report({'INFO'}, "Root motion removed on z-axis")

        return {'FINISHED'}

class SnapKeysToFramesOperator(bpy.types.Operator):
    bl_idname = "object.snap_keys_to_frames_operator"
    bl_label = "Snap Keys to Frames"
    bl_description = "Snap keyframes to round frame numbers"

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "No armature selected")
            return {'CANCELLED'}
        
        if obj.animation_data is None or obj.animation_data.action is None:
            self.report({'WARNING'}, "No animation data found")
            return {'CANCELLED'}
        
        action = obj.animation_data.action
        snap_keys_to_frames(action)

        self.report({'INFO'}, "Keyframes snapped to exact frame numbers")

        return {'FINISHED'}
        
class LooperPanel(bpy.types.Panel):
    bl_label = "Animation Looper"
    bl_idname = "OBJECT_PT_make_loop_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit"

    def draw(self, context):
        layout = self.layout

        layout.operator("object.loop_animation_operator")
        layout.operator("object.remove_root_motion_operator")
        layout.operator("object.snap_keys_to_frames_operator")

def register():
    bpy.utils.register_class(LoopAnimationOperator)
    bpy.utils.register_class(LooperPanel)
    bpy.utils.register_class(RemoveRootMotionOperator)
    bpy.utils.register_class(SnapKeysToFramesOperator)

def unregister():
    bpy.utils.unregister_class(LoopAnimationOperator)
    bpy.utils.unregister_class(LooperPanel)
    bpy.utils.unregister_class(RemoveRootMotionOperator)
    bpy.utils.unregister_class(SnapKeysToFramesOperator)

if __name__ == "__main__":
    register()
