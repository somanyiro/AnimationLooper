import bpy
from mathutils import Vector, Quaternion

# ==================== Operators ====================

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

    root_enum: bpy.props.EnumProperty(
        name="Select Root",
        description="Choose the root bone",
        items=lambda self, context: get_bones_enum(context)
    )

    loop_root_x: bpy.props.BoolProperty(name="Loop Root X", default=False)
    loop_root_y: bpy.props.BoolProperty(name="Loop Root Y", default=True)
    loop_root_z: bpy.props.BoolProperty(name="Loop Root Z", default=False)

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

class RemoveRootMotionOperator(bpy.types.Operator):
    bl_idname = "object.remove_root_motion_operator"
    bl_label = "Remove Root Motion"
    bl_description = "Remove keyframes on the Hips bone"

    root_enum: bpy.props.EnumProperty(
        name="Select Root",
        description="Choose the root bone",
        items=lambda self, context: get_bones_enum(context)
    )

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
            if fcurve.data_path == f'pose.bones["{self.root_enum}"].location':
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

class StitchAnimationsOperator(bpy.types.Operator):
    bl_idname = "object.stitch_animations_operator"
    bl_label = "Stitch Animations"
    bl_description = "Stitch animations together so that the transition between them is smooth"

    ratio: bpy.props.FloatProperty(
        name="Loop Ratio",
        description="Ratio of looping blend between start and end",
        default=0.5,
        min=0.0,
        max=1.0
    )

    start_enum: bpy.props.EnumProperty(
        name="Start Animation",
        description="Choose the first animation",
        items=lambda self, context: get_actions_enum(context)
    )

    end_enum: bpy.props.EnumProperty(
        name="End Animation",
        description="Choose the second animation",
        items=lambda self, context: get_actions_enum(context)
    )

    root_enum: bpy.props.EnumProperty(
        name="Select Root",
        description="Choose the root bone",
        items=lambda self, context: get_bones_enum(context)
    )

    stitch_root_x: bpy.props.BoolProperty(name="Stitch Root X", default=False)
    stitch_root_y: bpy.props.BoolProperty(name="Stitch Root Y", default=True)
    stitch_root_z: bpy.props.BoolProperty(name="Stitch Root Z", default=False)

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
        
        if self.start_enum == 'NONE' or self.end_enum == 'NONE':
            self.report({'WARNING'}, "No animations selected")
            return {'CANCELLED'}
        
        if self.start_enum == self.end_enum:
            self.report({'WARNING'}, "Start and end animations must be different")
            return {'CANCELLED'}

        bones = obj.pose.bones

        #anim 1
        obj.animation_data.action = bpy.data.actions.get(self.start_enum)
        snap_keys_to_frames(obj.animation_data.action)

        action_1 = obj.animation_data.action
        num_frames_1 = int(action_1.frame_range[1] - action_1.frame_range[0])+1

        raw_bone_positions_1 = []
        raw_bone_rotations_1 = []
        
        for frame in range(num_frames_1):
            bpy.context.scene.frame_set(frame)
            raw_bone_positions_1.append([bone.location.copy() for bone in bones])
            raw_bone_rotations_1.append([bone.rotation_quaternion.copy() for bone in bones])
        
        stitched_bone_positions_1 = [[Vector() for _ in bones] for _ in range(num_frames_1)]
        stitched_bone_rotations_1 = [[Quaternion() for _ in bones] for _ in range(num_frames_1)]
        offset_bone_positions_1 = [[Vector() for _ in bones] for _ in range(num_frames_1)]
        offset_bone_rotations_1 = [[Vector() for _ in bones] for _ in range(num_frames_1)]

        #anim 2
        obj.animation_data.action = bpy.data.actions.get(self.end_enum)
        snap_keys_to_frames(obj.animation_data.action)

        action_2 = obj.animation_data.action
        num_frames_2 = int(action_2.frame_range[1] - action_2.frame_range[0])+1

        raw_bone_positions_2 = []
        raw_bone_rotations_2 = []

        for frame in range(num_frames_2):
            bpy.context.scene.frame_set(frame)
            raw_bone_positions_2.append([bone.location.copy() for bone in bones])
            raw_bone_rotations_2.append([bone.rotation_quaternion.copy() for bone in bones])

        stitched_bone_positions_2 = [[Vector() for _ in bones] for _ in range(num_frames_2)]
        stitched_bone_rotations_2 = [[Quaternion() for _ in bones] for _ in range(num_frames_2)]
        offset_bone_positions_2 = [[Vector() for _ in bones] for _ in range(num_frames_2)]
        offset_bone_rotations_2 = [[Vector() for _ in bones] for _ in range(num_frames_2)]

        # Calculate positional and rotational differences
        pos_diff = compute_positional_difference(raw_bone_positions_1[-1], raw_bone_positions_2[0])
        rot_diff = compute_rotational_difference(raw_bone_rotations_1[-1], raw_bone_rotations_2[0])

        # Compute offsets
        compute_start_linear_offsets(offset_bone_positions_1, pos_diff, self.ratio)
        compute_start_linear_offsets(offset_bone_rotations_1, rot_diff, self.ratio)

        compute_end_linear_offsets(offset_bone_positions_2, pos_diff, self.ratio)
        compute_end_linear_offsets(offset_bone_rotations_2, rot_diff, self.ratio)

        # Apply offsets
        apply_positional_offsets(stitched_bone_positions_1, raw_bone_positions_1, offset_bone_positions_1)
        apply_rotational_offsets(stitched_bone_rotations_1, raw_bone_rotations_1, offset_bone_rotations_1)
        apply_positional_offsets(stitched_bone_positions_2, raw_bone_positions_2, offset_bone_positions_2)
        apply_rotational_offsets(stitched_bone_rotations_2, raw_bone_rotations_2, offset_bone_rotations_2)

        # Write stitched animations
        write_to_animation(obj, stitched_bone_positions_2, stitched_bone_rotations_2, num_frames_2, self.root_enum, self.stitch_root_x, self.stitch_root_y, self.stitch_root_z)
        obj.animation_data.action = bpy.data.actions.get(self.start_enum)
        write_to_animation(obj, stitched_bone_positions_1, stitched_bone_rotations_1, num_frames_1, self.root_enum, self.stitch_root_x, self.stitch_root_y, self.stitch_root_z)
        
        self.report({'INFO'}, f"Animations {self.start_enum} and {self.end_enum} stitched together")

        return {'FINISHED'}

class CenterAnimationOperator(bpy.types.Operator):
    bl_idname = "object.center_animation_operator"
    bl_label = "Center Animation"
    bl_description = "Make the root motion of the animation start at the center"

    action_enum: bpy.props.EnumProperty(
        name="Select Animation",
        description="Choose an animation to center",
        items=lambda self, context: get_actions_enum(context)
    )

    root_enum: bpy.props.EnumProperty(
        name="Select Root",
        description="Choose the root bone",
        items=lambda self, context: get_bones_enum(context)
    )

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
            self.report({'ERROR'}, "Selected object has no animation data")
            return {'CANCELLED'}

        if self.action_enum == 'NONE':
            self.report({'ERROR'}, "No animation selected")
            return {'CANCELLED'}

        obj.animation_data.action = bpy.data.actions.get(self.action_enum)

        center_animation_root(obj, self.root_enum, self.x, self.y, self.z)

        self.report({'INFO'}, f"Centered animation {self.action_enum} for {obj.name}")

        return {'FINISHED'}


# ==================== Helper functions ====================

def get_actions_enum(context):
        obj = context.object
        if obj and obj.type == 'ARMATURE' and obj.animation_data:
            actions = [(action.name, action.name, "") for action in bpy.data.actions]
            if actions:
                return actions
        return [('NONE', 'None', '')]

def get_bones_enum(context):
        obj = context.object
        if obj and obj.type == 'ARMATURE' and obj.animation_data:
            bones = [(bone.name, bone.name, "") for bone in obj.pose.bones]
            if bones:
                return bones
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
    pos_diff = compute_positional_difference(raw_bone_positions[0], raw_bone_positions[-1])
    rot_diff = compute_rotational_difference(raw_bone_rotations[0], raw_bone_rotations[-1])

    # Compute offsets
    compute_linear_offsets(offset_bone_positions, pos_diff, ratio)
    compute_linear_offsets(offset_bone_rotations, rot_diff, ratio)
    
    # Apply offsets
    apply_positional_offsets(looped_bone_positions, raw_bone_positions, offset_bone_positions)
    apply_rotational_offsets(looped_bone_rotations, raw_bone_rotations, offset_bone_rotations)

    # Write the looped animation back to Blender
    write_to_animation(obj, looped_bone_positions, looped_bone_rotations, num_frames, op.root_enum, op.loop_root_x, op.loop_root_y, op.loop_root_z)

def compute_positional_difference(a, b):
    pos_diff = []
    for j in range(len(a)):
        diff_pos = b[j] - a[j]
        pos_diff.append(diff_pos)
    return pos_diff

def compute_rotational_difference(a, b):
    rot_diff = []
    for j in range(len(a)):
        diff_rot = quat_to_scaled_angle_axis(a[j].rotation_difference(b[j]))
        rot_diff.append(diff_rot)
    return rot_diff

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

def compute_start_linear_offsets(offsets, diff, ratio):
    for i in range(len(offsets)):
        for j in range(len(offsets[i])):
            offsets[i][j] = lerp(0, 1 - ratio, i / (len(offsets) - 1)) * diff[j]

def compute_end_linear_offsets(offsets, diff, ratio):
    for i in range(len(offsets)):
        for j in range(len(offsets[i])):
            offsets[i][j] = lerp(ratio*-1, 0, i / (len(offsets) - 1)) * diff[j]

def apply_positional_offsets(looped_positions, raw_positions, offsets):
    for i in range(len(raw_positions)):
        for j in range(len(raw_positions[i])):
            looped_positions[i][j] = raw_positions[i][j] + offsets[i][j]

def apply_rotational_offsets(looped_rotations, raw_rotations, offsets):
        for i in range(len(raw_rotations)):
            for j in range(len(raw_rotations[i])):
                looped_rotations[i][j] = raw_rotations[i][j] @ Quaternion(offsets[i][j])

def write_to_animation(obj, positions, rotations, num_frames, root, alter_pos_x, alter_pos_y, alter_pos_z):
    action = obj.animation_data.action
    bones = obj.pose.bones
    
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
                    if bone_name == root:
                        if fcurve.array_index == 0 and not alter_pos_x:
                            continue
                        if fcurve.array_index == 1 and not alter_pos_y:
                            continue
                        if fcurve.array_index == 2 and not alter_pos_z:
                            continue

                    for keyframe in fcurve.keyframe_points:
                        frame = int(round(keyframe.co[0]))
                        if 0 <= frame < num_frames:
                            keyframe.co[1] = positions[frame][bone_idx][axis]

        if bone_name in fcurves_rotation:
            for axis, fcurve in enumerate(fcurves_rotation[bone_name]):
                if fcurve is not None:
                    for keyframe in fcurve.keyframe_points:
                        frame = int(round(keyframe.co[0]))
                        if 0 <= frame < num_frames:
                            keyframe.co[1] = rotations[frame][bone_idx][axis]

    for fcurves in [fcurves_location, fcurves_rotation]:
        for bone_fcurves in fcurves.values():
            for fcurve in bone_fcurves:
                if fcurve is not None:
                    fcurve.update()

    bpy.context.view_layer.update()

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def snap_keys_to_frames(action):
    for fcurve in action.fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.co[0] = round(keyframe.co[0])
        fcurve.update()

def center_animation_root(obj, root, center_x, center_y, center_z):
    action = obj.animation_data.action

    fcurves_location = []

    for fcurve in action.fcurves:
        if f'pose.bones["{root}"].location' in fcurve.data_path:
            fcurves_location.append(fcurve)
    
    x_offset = 0
    y_offset = 0
    z_offset = 0

    if center_x:
        x_offset = fcurves_location[0].keyframe_points[0].co[1]
        for keyframe in fcurves_location[0].keyframe_points:
            keyframe.co[1] -= x_offset
    if center_y:
        y_offset = fcurves_location[1].keyframe_points[0].co[1]
        for keyframe in fcurves_location[1].keyframe_points:
            keyframe.co[1] -= y_offset
    if center_z:
        z_offset = fcurves_location[2].keyframe_points[0].co[1]
        for keyframe in fcurves_location[2].keyframe_points:
            keyframe.co[1] -= z_offset

    for fcurve in fcurves_location:
        fcurve.update()
    
    bpy.context.view_layer.update()
