bl_info = {
    "name": "Animation Looper",
    "blender": (4, 22, 0),  # Blender version
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
    """Make the animaiton loop"""  # Tooltip for when hovering over the UI
    bl_idname = "object.make_loop_operator"  # Unique identifier for the operator
    bl_label = "Make Loop Operator"  # Label displayed on the button

    def execute(self, context):
        # Add your functionality here. We'll just print a message for now.
        self.report({'INFO'}, "Hello from the Simple Addon!")
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
        layout.operator("object.make_loop_operator")  # Adding the operator to the panel

# Registering the addon
def register():
    bpy.utils.register_class(MakeLoopOperator)
    bpy.utils.register_class(MakeLoopPanel)

# Unregistering the addon
def unregister():
    bpy.utils.unregister_class(MakeLoopOperator)
    bpy.utils.unregister_class(MakeLoopPanel)

# If the script is run directly, register the classes
if __name__ == "__main__":
    register()
