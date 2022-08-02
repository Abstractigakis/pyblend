import bpy
import math
import os
import random
import bmesh
import random


def purge_orphans():
    if bpy.app.version >= (3, 0, 0):
        bpy.ops.outliner.orphans_purge(
            do_local_ids=True, do_linked_ids=True, do_recursive=True
        )
    else:
        # call purge_orphans() recursively until there are no more orphan data blocks to purge
        result = bpy.ops.outliner.orphans_purge()
        if result.pop() != "CANCELLED":
            purge_orphans()


def clean_scene():
    """
    Removing all of the objects, collection, materials, particles,
    textures, images, curves, meshes, actions, nodes, and worlds from the scene
    """
    if bpy.context.active_object and bpy.context.active_object.mode == "EDIT":
        bpy.ops.object.editmode_toggle()

    for obj in bpy.data.objects:
        obj.hide_set(False)
        obj.hide_select = False
        obj.hide_viewport = False

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    collection_names = [col.name for col in bpy.data.collections]
    for name in collection_names:
        bpy.data.collections.remove(bpy.data.collections[name])

    # in the case when you modify the world shader
    world_names = [world.name for world in bpy.data.worlds]
    for name in world_names:
        bpy.data.worlds.remove(bpy.data.worlds[name])
    # create a new world data block
    bpy.ops.world.new()
    bpy.context.scene.world = bpy.data.worlds["World"]

    purge_orphans()


def addCamera():
    bpy.ops.object.camera_add(
        enter_editmode=False,
        align='VIEW',
        location=(9.8, 21.02, 5.12),
        rotation=(math.radians(84), 0, math.radians(157)),
        scale=(1, 1, 1)
    )

    bpy.context.object.data.lens = 35


def setBg(r, g, b, a=1.0, strength=1.0):
    world = bpy.data.worlds["World"]
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs[0].default_value = r, g, b, a
    bg.inputs[1].default_value = a


def addLights():
    light_z = 15
    light_distance = 20
    light_power = 300
    for x in [-1, 1]:
        for y in [-1, 1]:
            this_z_rotation = 135 * x * y if y > 0 else -45 * x * y
            bpy.ops.object.light_add(
                type='SPOT',
                radius=5,
                align='WORLD',
                location=(x*light_distance, y*light_distance, light_z),
                rotation=(math.radians(60), 0, math.radians(this_z_rotation))
            )
            bpy.context.object.data.energy = light_power


def make_floor_mat():
    floor_mat = bpy.data.materials.new('floor')
    floor_mat.use_nodes = True
    nodes = floor_mat.node_tree.nodes

    for node in nodes:
        nodes.remove(node)

    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf_node = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf_node.inputs['Transmission'].default_value = 0.8
    bsdf_node.inputs['Transmission Roughness'].default_value = 0.123
    bsdf_node.inputs['IOR'].default_value = 1.45
    bsdf_node.inputs['Base Color'].default_value = 0, 0, 0, 1
    floor_mat.node_tree.links.new(bsdf_node.outputs[0], output.inputs[0])
    return floor_mat


def addGround():
    bpy.ops.mesh.primitive_plane_add(size=100, location=(0, 0, 0))
    bpy.context.active_object.data.materials.append(make_floor_mat())


def make_mats(path):
    mats = []
    for fname in os.listdir(path):
        if fname[-3:] != "png":
            continue
        mat = bpy.data.materials.new(fname)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes

        for node in nodes:
            nodes.remove(node)

        output = nodes.new('ShaderNodeOutputMaterial')
        bsdf_node = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf_node.inputs['Specular'].default_value = 0.5
        bsdf_node.inputs['Roughness'].default_value = 0.5
        bsdf_node.inputs['IOR'].default_value = 1.450
        bsdf_node.inputs['Emission Strength'].default_value = 3.8

        image_node = nodes.new(type='ShaderNodeTexImage')
        filepath = f'{path}/{fname}'
        bpy.ops.image.open(filepath=filepath)
        image_node.image = bpy.data.images[fname]
        uv = nodes.new(type="ShaderNodeUVMap")
        node_tree = mat.node_tree
        node_tree.links.new(uv.outputs[0], image_node.inputs[0])
        node_tree.links.new(
            image_node.outputs[0], bsdf_node.inputs['Base Color'])
        node_tree.links.new(
            image_node.outputs[0], bsdf_node.inputs['Emission'])
        node_tree.links.new(bsdf_node.outputs[0], output.inputs[0])
        mats.append(mat)
    return mats


def build_pyramid(x, y, z, blocks):
    if blocks >= 1:
        build_level(x, y, z, blocks)
        build_pyramid(x, y, z+1, blocks-2)


def build_level(x, y, z, blocks):
    build_row(x, y, z, blocks)
    for i in range(1, int(math.ceil(blocks/2.0))):
        row_size = blocks - (2*i)
        build_row(x, y+i, z, row_size)
        build_row(x, y-i, z, row_size)


def build_row(x, y, z, row_size):
    if row_size == 1:
        make_cube_with_material(1, x, y, z)
    elif row_size > 1:
        offset = int(math.ceil(row_size/2.0)) - 1.0
        for x_val in [x+offset, x-offset]:
            make_cube_with_material(1, x_val, y, z)


def make_cube_with_material(s, x, y, z):
    bpy.ops.mesh.primitive_cube_add(
        size=s, enter_editmode=False, align='WORLD', location=(x, y, z), rotation=(0, 0, 0), scale=(1, 1, 1))
    obj = bpy.context.active_object
    obj.data.materials.append(random.choice(mats))
    mesh = obj.data
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.reset()

    bm = bmesh.from_edit_mesh(mesh)
    bm.edges.ensure_lookup_table()
    for edge in bm.edges:
        edge.seam = True
    for face in bm.faces:
        face.select_set(False)
    for face in bm.faces:
        face.material_index = 0
        face.select_set(True)
        bmesh.update_edit_mesh(mesh)
        bpy.ops.uv.smart_project(angle_limit=90.0, island_margin=0.001)
        face.select_set(False)
    bpy.ops.object.mode_set(mode='OBJECT')


clean_scene()
addCamera()
setBg(0, 0, 0)
addGround()
random.seed(420)
PYRAMID_BASE_WIDTH = 13
ICON_PATH = "C:\\Users\\estra\\repos\\pyblend\\icons"
mats = make_mats(ICON_PATH)
build_pyramid(0, 0, 0.5, PYRAMID_BASE_WIDTH)
addLights()
