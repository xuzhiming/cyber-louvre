import bpy, os
root = '/workspace/outputs/cyber_louvre'
bpy.ops.wm.open_mainfile(filepath=root + '/model.blend')
# remove helper lights/cameras not wanted in GLB
for o in list(bpy.data.objects):
    if o.type in ('LIGHT', 'CAMERA'): bpy.data.objects.remove(o)
bpy.ops.export_scene.gltf(filepath=root + '/model.glb', export_format='GLB', export_apply=True, export_materials='EXPORT',
    export_image_format='AUTO', export_yup=True, export_cameras=False, export_lights=False, export_extras=False)
print('exported', os.path.getsize(root + '/model.glb'))
