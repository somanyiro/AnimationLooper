bl_info = {
    "name": "Animation Looper",
    "blender": (4, 3, 0),
    "category": "Animation",
    "author": "Soma Nyiro",
    "version": (0, 2),
    "location": "View3D > Tool Shelf",
    "description": "A simple tool for creating looping animations from motion capture data",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
}

import bpy
from .animation_looper import *

class LooperPanel(bpy.types.Panel):
    bl_label = "Animation Looper"
    bl_idname = "OBJECT_PT_make_loop_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit"
 
    def draw(self, context):
        layout = self.layout

        layout.operator("object.loop_animation_operator")
        layout.operator("object.stitch_animations_operator")
        layout.operator("object.remove_root_motion_operator")
        layout.operator("object.snap_keys_to_frames_operator")
        layout.operator("object.center_animation_operator")
        layout.operator("object.change_root_bone_operator")
        layout.separator()
        layout.operator("object.play_animation", text="Play Animation", icon="PLAY")



def register():
    bpy.utils.register_class(LoopAnimationOperator)
    bpy.utils.register_class(LooperPanel)
    bpy.utils.register_class(RemoveRootMotionOperator)
    bpy.utils.register_class(SnapKeysToFramesOperator)
    bpy.utils.register_class(StitchAnimationsOperator)
    bpy.utils.register_class(CenterAnimationOperator)
    bpy.utils.register_class(ChangeRootBoneOperator)
    bpy.utils.register_class(PlayAnimationOperator)

def unregister():
    bpy.utils.unregister_class(LoopAnimationOperator)
    bpy.utils.unregister_class(LooperPanel)
    bpy.utils.unregister_class(RemoveRootMotionOperator)
    bpy.utils.unregister_class(SnapKeysToFramesOperator)
    bpy.utils.unregister_class(StitchAnimationsOperator)
    bpy.utils.unregister_class(CenterAnimationOperator)
    bpy.utils.unregister_class(ChangeRootBoneOperator)
    bpy.utils.unregister_class(PlayAnimationOperator)

#not sure this is needed here
if __name__ == "__main__":
    register()