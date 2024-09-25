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

class RemoveFrameOperator(bpy.types.Operator):
    bl_idname = "object.remove_frame_operator"
    bl_label = "Remove First Frame"

    def execute(self, context):
        obj = context.object  # Get the currently selected object
        
        if obj is None:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}
        
        if obj.animation_data is None or obj.animation_data.action is None:
            self.report({'WARNING'}, "No animation data on selected object")
            return {'CANCELLED'}
        
        action = obj.animation_data.action  # Access the animation action
        
        # Loop through the F-Curves to find the keyframes on the first frame (frame 1)
        for fcurve in action.fcurves:
            self.report({'INFO'}, f"Removing keyframe on frame 1 in {fcurve.data_path}")
            
            # Find and remove keyframe points at frame 1
            fcurve.keyframe_points.remove(
                next((kp for kp in fcurve.keyframe_points if kp.co[0] == 1), None)
            )
            
            # Update the F-Curve
            fcurve.update()
        
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
        layout.operator("object.remove_frame_operator")

# Registering the addon
def register():
    bpy.utils.register_class(MakeLoopOperator)
    bpy.utils.register_class(MakeLoopPanel)
    bpy.utils.register_class(RemoveFrameOperator)

# Unregistering the addon
def unregister():
    bpy.utils.unregister_class(MakeLoopOperator)
    bpy.utils.unregister_class(MakeLoopPanel)
    bpy.utils.unregister_class(RemoveFrameOperator)

# If the script is run directly, register the classes
if __name__ == "__main__":
    register()
