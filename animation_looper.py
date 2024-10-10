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

    blendtime_start: bpy.props.FloatProperty(
        name="Blend Time Start",
        description="",
        default=0.5,
        min=0.0,
        max=1.0
    )

    blendtime_end: bpy.props.FloatProperty(
        name="Blend Time End",
        description="",
        default=0.5,
        min=0.0,
        max=1.0
    )

    dt = 1.0/60.0

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        # Get the selected object
        obj = context.object
        
        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "No armature selected")
            return {'CANCELLED'}
        
        # Ensure the object has animation data
        if obj.animation_data is None or obj.animation_data.action is None:
            self.report({'ERROR'}, "Selected object has no animation data")
            return {'CANCELLED'}

        snap_keys_to_frames(obj.animation_data.action)

        try:
            loop_animation(obj, self.ratio, self.dt, self)
            self.report({'INFO'}, f"Looped animation for {obj.name}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to loop animation: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}
    
def loop_animation(obj, ratio, dt, op):
    action = obj.animation_data.action
    
    # Assuming we're working with bone animations in an armature
    bones = obj.pose.bones
    num_frames = int(action.frame_range[1] - action.frame_range[0])+1
    
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
    #compute_linear_offsets(offset_bone_positions, pos_diff, ratio)
    #compute_linear_offsets(offset_bone_rotations, rot_diff, ratio)
    compute_linear_inertialize_offsets(offset_bone_positions, pos_diff, vel_diff, op.blendtime_start, op.blendtime_end, ratio, dt)
    compute_linear_inertialize_offsets(offset_bone_rotations, rot_diff, ang_diff, op.blendtime_start, op.blendtime_end, ratio, dt)


    # Apply offsets
    apply_positional_offsets(looped_bone_positions, raw_bone_positions, offset_bone_positions)
    apply_rotational_offsets(looped_bone_rotations, raw_bone_rotations, offset_bone_rotations)
    
    # Write the looped animation back to Blender
    
    # Dictionaries to hold the FCurves for location and rotation_quaternion for each bone
    fcurves_location = {bone.name: [] for bone in bones}
    fcurves_rotation = {bone.name: [] for bone in bones}

    # Locate existing FCurves for location and rotation_quaternion
    for fcurve in action.fcurves:
        for bone in bones:
            if f'pose.bones["{bone.name}"].location' in fcurve.data_path:
                fcurves_location[bone.name].append(fcurve)
            elif f'pose.bones["{bone.name}"].rotation_quaternion' in fcurve.data_path:
                fcurves_rotation[bone.name].append(fcurve)

        # Loop through each FCurve for location and rotation
    for bone_idx, bone in enumerate(bones):
        bone_name = bone.name
        
        # Process location fcurves
        if bone_name in fcurves_location:
            for axis, fcurve in enumerate(fcurves_location[bone_name]):  # X, Y, Z axes for location
                if fcurve is not None:
                    for keyframe in fcurve.keyframe_points:
                        frame = int(round(keyframe.co[0]))
                        if 0 <= frame < num_frames:
                            keyframe.co[1] = looped_bone_positions[frame][bone_idx][axis]

        # Process rotation fcurves
        if bone_name in fcurves_rotation:
            for axis, fcurve in enumerate(fcurves_rotation[bone_name]):  # W, X, Y, Z axes for rotation
                if fcurve is not None:
                    for keyframe in fcurve.keyframe_points:
                        frame = int(round(keyframe.co[0]))
                        if 0 <= frame < num_frames:
                            keyframe.co[1] = looped_bone_rotations[frame][bone_idx][axis]

    # Ensure FCurves are updated
    for fcurves in [fcurves_location, fcurves_rotation]:
        for bone_fcurves in fcurves.values():
            for fcurve in bone_fcurves:
                if fcurve is not None:
                    fcurve.update()
    
    # Update the scene so the changes are reflected
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
            #factor = ratio * (ratio - 1.0) * (i / (len(offsets) - 1))
            #offsets[i][j] = factor * diff[j]
            
            offsets[i][j] = lerp(ratio, ratio-1.0, i / (len(offsets) - 1)) * diff[j]

def compute_linear_inertialize_offsets(offsets, diff_pos, diff_vel, blendtime_start, blendtime_end, ratio, dt):
    assert 0.0 <= ratio <= 1.0, "Ratio must be between 0 and 1."
    assert blendtime_start >= 0.0, "Blendtime start must be non-negative."
    assert blendtime_end >= 0.0, "Blendtime end must be non-negative."
    
    rows = len(offsets)      # Number of frames (rows)
    cols = len(offsets[0])   # Number of joints/bones (cols)

    # Loop over every frame
    for i in range(rows):
        t = float(i) / (rows - 1)

        # Loop over every joint (or bone)
        for j in range(cols):
            # Initial linear offset (lerp)
            linear_offset = lerp(ratio, (ratio - 1.0), t) * diff_pos[j]

            # Velocity offset at the start
            velocity_offset_start = decayed_velocity_offset_cubic([ratio * diff_vel[j]], blendtime_start, i * dt)

            # Velocity offset at the end
            velocity_offset_end = decayed_velocity_offset_cubic([(1.0 - ratio) * diff_vel[j]], blendtime_end, (rows - 1 - i) * dt)

            # Compute the final offset for the joint
            offsets[i][j] = linear_offset + velocity_offset_start[0] + velocity_offset_end[0]

def decayed_velocity_offset_cubic(v, blendtime, dt, eps=1e-8):
    """Compute the decayed velocity offset using cubic decay."""
    t = clamp(dt / (blendtime + eps), 0, 1)

    c = [vi * blendtime for vi in v]
    b = [-2 * ci for ci in c]
    a = c
    
    return [a_i * t**3 + b_i * t**2 + c_i for a_i, b_i, c_i in zip(a, b, c)]

def clamp(value, min_val, max_val):
    return max(min(value, max_val), min_val)


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
                if fcurve.array_index == 0 and self.x:  # X-axis (location[0])
                    for keyframe in fcurve.keyframe_points:
                        keyframe.co[1] = 0  # Set the keyframe value (Y-coordinate) to 0

                elif fcurve.array_index == 1 and self.y:  # Z-axis (location[2])
                    for keyframe in fcurve.keyframe_points:
                        keyframe.co[1] = 0  # Set the keyframe value (Y-coordinate) to 0

                elif fcurve.array_index == 2 and self.z:  # Z-axis (location[2])
                    for keyframe in fcurve.keyframe_points:
                        keyframe.co[1] = 0  # Set the keyframe value (Y-coordinate) to 0
        
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
    bl_label = "Make Loop Panel"  # Panel label
    bl_idname = "OBJECT_PT_make_loop_panel"  # Unique identifier for the panel
    bl_space_type = 'VIEW_3D'  # Where this panel will appear
    bl_region_type = 'UI'  # The region of the interface
    bl_category = "Edit"  # The tab where it will appear

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
