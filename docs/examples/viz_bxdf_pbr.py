from dipy.data import get_fnames
from fury import actor, ui, window
from fury.data import read_viz_textures
from fury.io import load_polydata
from fury.utils import get_actor_from_polydata
from fury.shaders import add_shader_callback, load, shader_to_actor
from scipy.spatial import Delaunay


import math
import numpy as np
import os
import random
import vtk


def build_label(text, font_size=16, color=(1, 1, 1), bold=False, italic=False,
                shadow=False):
    label = ui.TextBlock2D()
    label.message = text
    label.font_size = font_size
    label.font_family = 'Arial'
    label.justification = 'left'
    label.bold = bold
    label.italic = italic
    label.shadow = shadow
    label.actor.GetTextProperty().SetBackgroundColor(0, 0, 0)
    label.actor.GetTextProperty().SetBackgroundOpacity(0.0)
    label.color = color
    return label


def change_slice_metallic(slider):
    global obj_actor
    obj_actor.GetProperty().SetMetallic(slider._value)


def change_slice_specular(slider):
    global obj_actor
    obj_actor.GetProperty().SetSpecular(slider._value)


def change_slice_specular_tint(slider):
    global obj_actor
    obj_actor.GetProperty().SetSpecularPower(slider._value)


def change_slice_roughness(slider):
    global obj_actor
    obj_actor.GetProperty().SetRoughness(slider._value)


def change_slice_sheen(slider):
    global sheen
    sheen = slider._value


def change_slice_sheen_tint(slider):
    global sheen_tint
    sheen_tint = slider._value


def change_slice_clearcoat(slider):
    global clearcoat
    clearcoat = slider._value


def change_slice_clearcoat_gloss(slider):
    global clearcoat_gloss
    clearcoat_gloss = slider._value


def get_cubemap(files_names):
    texture = vtk.vtkTexture()
    texture.CubeMapOn()
    for idx, fn in enumerate(files_names):
        if not os.path.isfile(fn):
            print('Nonexistent texture file:', fn)
            return texture
        else:
            # Read the images
            reader_factory = vtk.vtkImageReader2Factory()
            img_reader = reader_factory.CreateImageReader2(fn)
            img_reader.SetFileName(fn)

            flip = vtk.vtkImageFlip()
            flip.SetInputConnection(img_reader.GetOutputPort())
            flip.SetFilteredAxis(1)  # flip y axis
            texture.SetInputConnection(idx, flip.GetOutputPort(0))
    return texture


def obj_brain():
    brain_lh = get_fnames(name='fury_surface')
    polydata = load_polydata(brain_lh)
    return get_actor_from_polydata(polydata)


def obj_spheres(radii=2, theta=32, phi=32):
    centers = [[-5, 5, 0], [0, 5, 0], [5, 5, 0], [-5, 0, 0], [0, 0, 0],
               [5, 0, 0], [-5, -5, 0], [0, -5, 0], [5, -5, 0]]
    colors = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 1, 1], [1, 0, 1], [1, 1, 0],
              [0, 0, 0], [.5, .5, .5], [1, 1, 1]]
    return actor.sphere(centers, colors, radii=radii, theta=theta, phi=phi)


def obj_surface():
    size = 11
    vertices = list()
    for i in range(-size, size):
        for j in range(-size, size):
            fact1 = - math.sin(i) * math.cos(j)
            fact2 = - math.exp(abs(1 - math.sqrt(i ** 2 + j ** 2) / math.pi))
            z_coord = -abs(fact1 * fact2)
            vertices.append([i, j, z_coord])
    c_arr = np.random.rand(len(vertices), 3)
    random.shuffle(vertices)
    vertices = np.array(vertices)
    tri = Delaunay(vertices[:, [0, 1]])
    faces = tri.simplices
    c_loop = [None, c_arr]
    f_loop = [None, faces]
    s_loop = [None, "butterfly", "loop"]
    for smooth_type in s_loop:
        for face in f_loop:
            for color in c_loop:
                surface_actor = actor.surface(vertices, faces=face,
                                              colors=color, smooth=smooth_type)
    return surface_actor


def uniforms_callback(_caller, _event, calldata=None):
    global clearcoat, clearcoat_gloss, sheen, sheen_tint
    if calldata is not None:
        calldata.SetUniformf('sheen', sheen)
        calldata.SetUniformf('sheenTint', sheen_tint)
        calldata.SetUniformf('clearcoat', clearcoat)
        calldata.SetUniformf('clearcoatGloss', clearcoat_gloss)


def win_callback(obj, event):
    global panel, size
    if size != obj.GetSize():
        size_old = size
        size = obj.GetSize()
        size_change = [size[0] - size_old[0], 0]
        panel.re_align(size_change)


if __name__ == '__main__':
    global clearcoat, clearcoat_gloss, panel, sheen, sheen_tint, size

    #obj_actor = obj_brain()
    #obj_actor = obj_surface()
    obj_actor = obj_spheres()

    metallic = .0
    specular = .0
    specular_tint = .0
    roughness = .0
    sheen = .0
    sheen_tint = .0
    clearcoat = .0
    clearcoat_gloss = .0

    # TODO: Add opacity panel
    obj_actor.GetProperty().SetOpacity(.5)

    #specular_color = vtk.vtkNamedColors().GetColor3d('White')

    obj_actor.GetProperty().SetInterpolationToPBR()
    obj_actor.GetProperty().SetMetallic(metallic)
    obj_actor.GetProperty().SetRoughness(roughness)
    #obj_actor.GetProperty().SetSpecular(specular)
    #obj_actor.GetProperty().SetSpecularPower(specular_tint)
    #obj_actor.GetProperty().SetSpecularColor(specular_color)

    add_shader_callback(obj_actor, uniforms_callback)

    fs_dec_code = load('bxdf_dec.frag')
    fs_impl_code = load('bxdf_impl.frag')

    #shader_to_actor(obj_actor, 'vertex', debug=True)
    shader_to_actor(obj_actor, 'fragment', decl_code=fs_dec_code)
    shader_to_actor(obj_actor, 'fragment', impl_code=fs_impl_code,
                    block='light', debug=False)

    cubemap_fns = [read_viz_textures('skybox-px.jpg'),
                   read_viz_textures('skybox-nx.jpg'),
                   read_viz_textures('skybox-py.jpg'),
                   read_viz_textures('skybox-ny.jpg'),
                   read_viz_textures('skybox-pz.jpg'),
                   read_viz_textures('skybox-nz.jpg')]

    # Load the cube map
    cubemap = get_cubemap(cubemap_fns)

    # Load the skybox
    skybox = get_cubemap(cubemap_fns)
    skybox.InterpolateOn()
    skybox.RepeatOff()
    skybox.EdgeClampOn()

    skybox_actor = vtk.vtkSkybox()
    skybox_actor.SetTexture(skybox)

    scene = window.Scene()

    scene.UseImageBasedLightingOn()
    if vtk.vtkVersion.GetVTKMajorVersion() >= 9:
        scene.SetEnvironmentTexture(cubemap)
    else:
        scene.SetEnvironmentCubeMap(cubemap)

    scene.add(obj_actor)
    scene.add(skybox_actor)

    #window.show(scene)

    show_m = window.ShowManager(scene=scene, reset_camera=False,
                                order_transparent=True)
    show_m.initialize()

    panel = ui.Panel2D((320, 480), position=(-25, 5), color=(.25, .25, .25),
                       opacity=.75, align='right')

    slider_label_subsurface = build_label('Subsurface')
    slider_label_metallic = build_label('Metallic')
    slider_label_specular = build_label('Specular')
    slider_label_specular_tint = build_label('Specular Tint')
    slider_label_roughness = build_label('Roughness')
    slider_label_anisotropic = build_label('Anisotropic')
    slider_label_sheen = build_label('Sheen')
    slider_label_sheen_tint = build_label('Sheen Tint')
    slider_label_clearcoat = build_label('Clearcoat')
    slider_label_clearcoat_gloss = build_label('Clearcoat Gloss')

    label_pad_x = .02

    panel.add_element(slider_label_subsurface, (label_pad_x, .95))
    panel.add_element(slider_label_metallic, (label_pad_x, .85))
    panel.add_element(slider_label_specular, (label_pad_x, .75))
    panel.add_element(slider_label_specular_tint, (label_pad_x, .65))
    panel.add_element(slider_label_roughness, (label_pad_x, .55))
    panel.add_element(slider_label_anisotropic, (label_pad_x, .45))
    panel.add_element(slider_label_sheen, (label_pad_x, .35))
    panel.add_element(slider_label_sheen_tint, (label_pad_x, .25))
    panel.add_element(slider_label_clearcoat, (label_pad_x, .15))
    panel.add_element(slider_label_clearcoat_gloss, (label_pad_x, .05))

    length = 160
    text_template = '{value:.1f}'

    slider_slice_subsurface = ui.LineSlider2D(
        initial_value=0, max_value=1, length=length,
        text_template=text_template)
    slider_slice_metallic = ui.LineSlider2D(
        initial_value=metallic, max_value=1, length=length,
        text_template=text_template)
    slider_slice_specular = ui.LineSlider2D(
        initial_value=specular, max_value=1, length=length,
        text_template=text_template)
    slider_slice_specular_tint = ui.LineSlider2D(
        initial_value=specular_tint, max_value=1, length=length,
        text_template=text_template)
    slider_slice_roughness = ui.LineSlider2D(
        initial_value=roughness, max_value=1, length=length,
        text_template=text_template)
    slider_slice_anisotropic = ui.LineSlider2D(
        initial_value=0, max_value=1, length=length,
        text_template=text_template)
    slider_slice_sheen = ui.LineSlider2D(
        initial_value=sheen, max_value=1, length=length,
        text_template=text_template)
    slider_slice_sheen_tint = ui.LineSlider2D(
        initial_value=sheen_tint, max_value=1, length=length,
        text_template=text_template)
    slider_slice_clearcoat = ui.LineSlider2D(
        initial_value=clearcoat, max_value=1, length=length,
        text_template=text_template)
    slider_slice_clearcoat_gloss = ui.LineSlider2D(
        initial_value=clearcoat_gloss, max_value=1, length=length,
        text_template=text_template)

    slider_slice_metallic.on_change = change_slice_metallic
    slider_slice_specular.on_change = change_slice_specular
    slider_slice_specular_tint.on_change = change_slice_specular_tint
    slider_slice_roughness.on_change = change_slice_roughness
    slider_slice_sheen.on_change = change_slice_sheen
    slider_slice_sheen_tint.on_change = change_slice_sheen_tint
    slider_slice_clearcoat.on_change = change_slice_clearcoat
    slider_slice_clearcoat_gloss.on_change = change_slice_clearcoat_gloss

    slice_pad_x = .42

    panel.add_element(slider_slice_subsurface, (slice_pad_x, .95))
    panel.add_element(slider_slice_metallic, (slice_pad_x, .85))
    panel.add_element(slider_slice_specular, (slice_pad_x, .75))
    panel.add_element(slider_slice_specular_tint, (slice_pad_x, .65))
    panel.add_element(slider_slice_roughness, (slice_pad_x, .55))
    panel.add_element(slider_slice_anisotropic, (slice_pad_x, .45))
    panel.add_element(slider_slice_sheen, (slice_pad_x, .35))
    panel.add_element(slider_slice_sheen_tint, (slice_pad_x, .25))
    panel.add_element(slider_slice_clearcoat, (slice_pad_x, .15))
    panel.add_element(slider_slice_clearcoat_gloss, (slice_pad_x, .05))

    scene.add(panel)

    size = scene.GetSize()

    show_m.add_window_callback(win_callback)

    show_m.start()
