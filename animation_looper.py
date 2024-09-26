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

# Define a simple operator (action)
class MakeLoopOperator(bpy.types.Operator):
    bl_idname = "object.make_loop_operator"  # Unique identifier for the operator
    bl_label = "Make Loop"  # Label displayed on the button

    def execute(self, context):
        # Add your functionality here. We'll just print a message for now.
        self.report({'INFO'}, "Hello from animation looper!")
        return {'FINISHED'}

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
    
# Define a Panel (UI element)
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

# Registering the addon
def register():
    bpy.utils.register_class(MakeLoopOperator)
    bpy.utils.register_class(MakeLoopPanel)
    bpy.utils.register_class(RemoveRootMotionOperator)

# Unregistering the addon
def unregister():
    bpy.utils.unregister_class(MakeLoopOperator)
    bpy.utils.unregister_class(MakeLoopPanel)
    bpy.utils.unregister_class(RemoveRootMotionOperator)

# If the script is run directly, register the classes
if __name__ == "__main__":
    register()
