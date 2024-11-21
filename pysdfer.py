#!/usr/bin/env python3

from cmath import sqrt
from math import ceil
from multiprocessing.dummy import Array
from pathlib import Path
import re
from typing import Collection, Dict, Any
from wand.image import Image, CHANNELS
from wand.image import COMPOSITE_OPERATORS
from wand.color import Color
from wand.api import library
from wand.exceptions import CorruptImageError, BlobError
import os
import argparse
from xml.dom import minidom
import io
import re
from statistics import mode
from multiprocessing import Pool
import subprocess
import numpy as np
import tempfile
from functools import reduce
from contextlib import contextmanager
import time
import random
import shutil
import tomllib
import sys
import alive_progress
import xxhash
import json

def tmp_file_name():
    return f"./sdftmp/{time.time()+random.random()}.png"

def tmp_file(mode="wb"):
    return open(tmp_file_name(), mode)

def tmp_png(image):
    tmpfile = tmp_file()
    tmpfile.write(image.make_blob("png"))
    tmpfile.flush()
    # print("pngtmp is ", tmpfile.name)
    return tmpfile


def __sv_img(tup: tuple):
    tup[0].save(filename=tup[1])

def save_images(images, args):
    # with Pool(args.processes) as p:
        # p.map(__sv_img, images)
    for (i,p) in images:
        shutil.move(i,p)
    # [i.save(filename=p) for (i,p) in images]

def neo_save_images(output_list):
    # print("output list:", output_list)
    [shutil.move(tmppath, topath) for (tmppath, topath, args) in output_list]

def neo_make_save_root(path_in: Path, path_out: Path, inklayers: bool, atlas: bool = False):
    save_root = path_out.resolve() if path_out else None
    save_filename = (path_in.name + ".atlas.csdf.png") if atlas else path_in.stem+".csdf.png"
    if save_root == None:
        save_root = path_in.parent / 'sdf_out' 
        os.makedirs(save_root, exist_ok=True)
    if inklayers and (not atlas):
        save_root = save_root / path_in.stem
        os.makedirs(save_root, exist_ok=True)
    elif save_root.suffix != '.png':
       save_root = save_root / save_filename
    # print("save root for", path_in, "is", save_root)
    return save_root

def make_path(path_in: Path, path_out: Path, inklayers: bool, atlas: bool = False):
    # If the input param is none, we want to make one
    if path_out == None:
        # if the input is a file, we want the output to be a png file
        if path_in.is_file():
            path_out = path_in.parent / 'sdf_out' / (path_in.stem+(".atlas" if atlas else "")+".csdf.png")
        else:
            # but if the input is a directory, we want the dir to be seperated
            # (as though a dir path were passed in)
            path_out = path_in / 'sdf_out'
    # If the input is a file, and the output is a directory or doesn't exist
    if path_in.is_file() and path_out.suffix != '.png':
        # print("inklayers is ", inklayers)
        # If we want to process this as an inkscape doc, seperating layers...
        if inklayers :
             # ... we want to make an output folder, into which the layers can go
            tmppath = path_out / (path_in.stem+"/")
            if tmppath.stem != path_in.stem:
                path_out = path_out / (path_in.stem+"/")
                # print("path out is ", path_out)
                os.makedirs(path_out, exist_ok=True)
        # Otherwise if the path doesn't have a suffix (a poor way to detect
        # a file path that doesn't exist, but it's what we've got)...
        elif path_out.suffix != '.png':
            # We want to take a dir path and make it into a file path
            path_out = path_out / (path_in.stem+".csdf.png")
    elif not path_out.exists():
        # if the path seems to be a dir path, we want to makedir slightly
        # differently
        if path_out.suffix == '':
            os.makedirs(path_out, exist_ok=True)
        else:
            os.makedirs(path_out.parent, exist_ok=True)
        # args.path_out.mkdir(parents=True, exist_ok=True)
    return path_out

def do_image(image: Image, main_color: Color, under_color: Color = None, out_height: int = 128, keep_aspect: bool = False, kernel_size=10, kernel_scale=100):

    padding = int(kernel_size*6/(kernel_scale/100))

    image_ar = image.width/image.height

    under_color = Color(str(under_color))

    # print("doing image, ", image)
    # image.alpha_channel = 'extract'
    # image.negate()
    if under_color:
        backimage = Image(width=image.width, height=image.height, background=under_color)
        backimage.composite(image)
        image = backimage
    else:
        under_color = Color('transparent')
        # print('under color is now ', under_color)
    
    inset_height = max(image.width, image.height)+padding
    inset_width = inset_height
    if keep_aspect:
        inset_height = image.height + padding
        inset_width = int(inset_height * image_ar)
        pass
    inset = Image(height=inset_height, width=inset_width, background=under_color)
    inset.gravity = 'center'
    inset.composite(image)
    image = inset

    image.type = 'grayscale'
    image.level(.98, .99)

    outer = image.clone()
    #outer.resize(ceil(outer.width*4), ceil(outer.height*4))
    outer.morphology(method="distance", kernel=f'euclidean:{kernel_size},{kernel_scale}', iterations=1)
    #outer.auto_level()
    #outer.level(.0, 1.5)

    inner = image.clone()
    inner.negate()
    inner.morphology(method="distance", kernel=f'euclidean:{kernel_size},{kernel_scale}', iterations=1)
    inner.level(.50, -.50)

    outer.compose = 'plus'
    outer.composite(inner, operator="plus")

    outer.level(.45, .55)
    outer.negate()
    outer.alpha_channel = "copy"
    
    
    if not main_color:
        main_color = Color('white')
    the_black = Image(width=outer.width, height=outer.height, background=main_color)
    #the_black.colorize(color=Color('white'), alpha=Color('black'))
    # print(the_black)


    the_black.composite(outer, operator='copy_alpha')
    out_width = out_height
    if keep_aspect:
        out_width = int(out_height / image_ar)
        pass
    the_black.resize(out_height, out_width)
    #the_black.resize(128, 128)
    return the_black

def pad_list_with(l: list, amt: int, genfiller):
    l = l.copy()
    c = len(l)
    num_to_fill = amt - c
    for i in range(num_to_fill):
        l.append(genfiller())
    return l

def split_list(l: list, sublist_len: int):
    return [l[i:i+sublist_len] for i in range(0, len(l), sublist_len)]

def img_row_reduce(a: Image, b: Image):
    a.sequence.append(b)
    a.concat()
    return a
    pass

def img_stack_reduce(a: Image, b: Image):
    a.sequence.append(b)
    a.concat(True)
    return a

def make_image_row(ilist: list):
    col = reduce(img_row_reduce, ilist)
    # print(ilist)
    return 1
    pass


def make_atlas(sdf_images: list, is_in_process: bool = True, pool_count=10):
    # print('sdf images are: ', sdf_images)
    imcount = len(sdf_images)
    next_up_sqrt = ceil(sqrt(imcount).real)
    new_img_1 = Image(height=sdf_images[0].height, width=sdf_images[0].width, background=Color('transparent'))
    genfiller = lambda: new_img_1.clone()
    padded_list = pad_list_with(sdf_images, next_up_sqrt*next_up_sqrt, genfiller)
    s_list = split_list(padded_list, next_up_sqrt)
    atlas = reduce(img_stack_reduce, [reduce(img_row_reduce, x) for x in s_list])
    # print("atlas is :", atlas)
    return atlas

def remove_newlines(s: str):
    return ' '.join([x.strip() for x in s.splitlines()])
    # print(strValue)

def break_up_inkscape_layers(filepath: Path, args):
    with filepath.open() as svg_file:
        newlineless = remove_newlines(svg_file.read())
        svg = minidom.parseString(newlineless)
        svgroot = svg.getElementsByTagName('svg')[0]
        # print(svgroot)
        layers = svg.getElementsByTagName('g')
        # print(layers)
        layer_docs = []
        for layer in layers:
            svgroot.removeChild(layer)
        for layer in layers:
            new_svg = svg.cloneNode(deep=True)
            new_root = new_svg.getElementsByTagName('svg')[0]
            new_root.appendChild(layer)
            #new_svg.append_child(layer)
            layer_docs.append(new_svg)
        return layer_docs

def remove_single_character_text_nodes(childrens):
    col = []
    for child in childrens:
        if child.nodeType == minidom.Node.TEXT_NODE:
            if child.data != ' ': 
                col.append(child)
        else:
            col.append(child)
    return col

def get_style_from_shape(shapenode):
    style = shapenode.getAttribute('style')
    style_sep = style.split(';')
    return {k:v for (k,v) in [x.split(':') for x in style.split(';')]}

def set_styles_on_shape(shapenode, styledict):
    s = ';'.join([f'{desc}:{dat}' for (desc, dat) in styledict.items()])
    shapenode.setAttribute('style', s)

def convert_svg_layer_to_png(layer):
    with tempfile.NamedTemporaryFile(suffix=".svg") as svgtmp:
        pngtmp = tmp_file("xb")
        svgtmp.write(bytes(layer, 'utf-8'))
        svgtmp.flush()
        # Imagemagick cannot correctly talk with Inkscape sometimes, so 
        # we do this bit ourselves
        subres = subprocess.run(
                ['inkscape',
                 svgtmp.name,
                 f'--export-filename={pngtmp.name}',
                 '--export-dpi=96',
                 '--export-background=rgb(100%, 100%, 100%)',
                 '--export-background-opacity=0'])
        # print(subres)
        # To ensure that the image is read before the tmp file 
        # goes away, we read it in and stuff it as a blob into 
        # a new image
        pngtmp.seek(0, os.SEEK_END)
        #b = bytes(pngtmp.read())
        pngsize = pngtmp.tell()
        pngtmp.seek(0)
        if pngsize == 0:
            # If the file had nothing in it, it means that 
            # Inkscape messed up. We'll have it do it until it 
            # gets it right
            return convert_svg_layer_to_png(layer)
        else:
            # print("png tmp: ", pngtmp)
            #img = Image(blob=b, format="PNG")
            return pngtmp

def xmlstr_to_sdf(a):
    print("converting", a['save_root'], "layer", a['label'])
    pngtmp = convert_svg_layer_to_png(a['layer'])
    # print("returned png tmp: ", pngtmp)
    img = Image(filename=pngtmp.name, format="png")
    sdf_img = do_image(img, a['shapecolor'], Color(str(a['color_underlay'])), a['height'], a['keep_aspect'], kernel_size=a['kernel_size'], kernel_scale=a['kernel_scale'])
    path: Path = a['save_root'] / f"{a['label'] or 'image'}.csdf.png"
    # print("the save_root is ", a['save_root'])
    # print('and path is ', path)
    sdftmp = tmp_png(sdf_img)
    print("Done with", a['save_root'], "layer", a['label'])
    return (sdftmp.name, path)
    #(sdf_img.make_blob(format="png"), path)
    #sdf_img.save(filename=path)

#def handle_inklayers(filepath: Path, args, blob_at_end, is_in_process):
def handle_inklayers(filepath: Path, args, is_in_process):
    # We want to get each inksacpe layer on its own
    layer_docs = break_up_inkscape_layers(filepath, args)
    layers_xml = []
    save_root = args.path_out
    print("file", filepath, "is going to have each layer converted separately")
    for layer in layer_docs:
        # We just get the first g child, as there should only be one
        l_element = layer.getElementsByTagName('g')[0]
        #save_root = make_path(filepath, args.path_out, True)
        # We only want to operate on a layer that has content
        if l_element.hasChildNodes():
            # normalize removes a nice number of bs nodes
            l_element.normalize()
            ch = l_element.childNodes
            # normalize doesn't remove all of them, however
            ch = remove_single_character_text_nodes(ch)
            # We get the main output color...
            shapecolor = args.main_color
            # print("--------- shapecolor is ", shapecolor)
            # and then get the most common fill color if none is provided.
            # Yes this means that there will be black shapes
            if not shapecolor:
                colcol = []
                for shape in ch:
                    pass
                    s = get_style_from_shape(shape)
                    col = s['fill']
                    colcol.append(col)
                    #s['fill'] = '#000000'
                    #set_styles_on_shape(shape, s)
                shapecolor = mode(colcol)
            else:
                shapecolor = str(shapecolor)
            layer_data = {
                'layer': layer.toxml(), 
                # 'img': Image(blob=bytes(layer.toxml(), 'utf-8')).make_blob('png'),
                'label': str(l_element.getAttribute('inkscape:label')),
                'shapecolor': shapecolor,
                # 'args': args,
                'color_underlay': str(args.color_underlay),
                'height': args.height,
                'keep_aspect': args.keep_aspect,
                'save_root': args.path_out,
                'kernel_size': args.kernel_size,
                'kernel_scale': args.kernel_scale
                }            
            layers_xml.append(layer_data)
            #img = Image(blob=bytes(layer.toxml(), 'utf-8'))
            #print(img)
    # print(layers_xml)
    images_out = []
    if is_in_process:
        images_out = [(x, y, args) for [x,y] in [xmlstr_to_sdf(x) for x in layers_xml]]
    else:
        with Pool(args.processes) as p:
            with alive_progress.alive_bar(len(layers_xml)) as bar:
                for (x,y) in p.imap(xmlstr_to_sdf, layers_xml):
                    bar()
                    images_out += [[x,y,args]]

    if args.atlas:
        # print("AAAAA save_root: ", save_root, " stem: ", filepath.stem, " parent: ", save_root.parent, " name: ", save_root.name )
        print("Making atlas for", save_root.name)
        master_path = save_root
        if save_root.suffix != ".png":
            master_path = save_root / (filepath.stem + '.atlas.csdf.png')
        images = [Image(filename=x) for [x,y, _args] in images_out]
        atlas_images_out = [[make_atlas(images, is_in_process), master_path]]
        images_out = [(tmp_png(x).name, y, args) for [x,y] in atlas_images_out]
        print("Atlas made for", save_root.name)

    return images_out

#def handle_file(filepath: Path, args, blob_at_end = False, is_in_process = False):
def handle_file(filepath: Path, args, is_in_process = False):
    # If we want to handle this file as an inkscape doc, saving each layer,
    # we defer to the function for that
    out = []
    if args.inklayers: 
        if filepath.suffix == '.svg':
            out = handle_inklayers(filepath, args, is_in_process)
            #if blob_at_end:
            #    out = [(x.make_blob('png'), y) for [x,y] in out]
            #    # out = [('inklayer', y) for [x,y] in out]
        return out
    # Otherwise we simply process the image
    else:
        # Process the image
        # print('get the img')
        img = do_image(Image(filename=filepath), args.main_color, args.color_underlay, args.height, args.keep_aspect, kernel_size=args.kernel_size, kernel_scale=args.kernel_scale)
        # print('get the path')
        path = args.path_out
        # print('path made is ', path)
        # print('and return')
        out = [(tmp_png(img).name, path, args)]
        # out = [('single image', path)]
        # save(filename=args.path_out)
    return out
    pass

def handle_file_for_process(args):
    print("Processing", args.path_in)
    return handle_file(args.path_in, args, True)
    print("Finished with", args.path_in)

format_suffixes = ['.svg', '.png', '.jpg', '.jpeg', '.gif', '.bmp']

def is_path_supported_image(path: Path, args):
    tmp_suffixes = []
    if args.inklayers:
        tmp_suffixes = ['.svg']
    elif args.no_svg:
        tmp_suffixes = [x for x in format_suffixes if x != '.svg']
    return path.is_file and path.suffix in tmp_suffixes

def handle_dir(args):
    path_in = args.path_in.resolve(True)
    # print(args.path_out)
    output = []
    id = [[x, args, True, True] for x in path_in.iterdir() if is_path_supported_image(x, args)]
    # print("file ids are", id)
    # if args.inklayers:
    #     id = [x for x in id if x[1].suffix == '.svg']
    # elif args.no_svg:
    #     id = [x for x in id if x[1].suffix != '.svg']
    with Pool(args.processes) as p:
        sm = p.starmap(handle_file, id)
        # [print('x, y', x, y) for [x, y] in sum(sm, [])]
        # return []
        return [(x, y) for (x, y) in sum(sm, [])]
    return output

def get_image_process_fns(args):
    path_in = args.path_in.resolve(True)
    # print(args.path_out)
    output = []
    id = [[x, args, True, True] for x in path_in.iterdir() if is_path_supported_image(x, args)]


override_memo: dict[Path, Dict[str, Any]] = {}

def get_overrides_from_file(path_in) -> dict[str, Any]:
    isdir = path_in.is_dir()
    respath = path_in.resolve(strict=True)
    dirpath = respath if isdir else respath.parent

    configpath = dirpath / "csdf.toml"
    if configpath in override_memo:
        return override_memo.get(configpath, {})
    elif configpath.exists():
        with open(configpath, 'rb') as f:
            overrides = tomllib.load(f)
            if "path_out" in overrides:
                pathout = Path(overrides['path_out'])
                newpath = dirpath / pathout
                overrides['path_out'] = newpath.resolve()
            override_memo[configpath] = overrides
            return overrides
    else:
        return {}

def process_validate_args(args):

    # print("   Doing", args)

    args.path_out = neo_make_save_root(args.path_in, args.path_out, args.inklayers, args.atlas)

    if args.inklayers and args.no_svg:
        return (False, "You cannot use both --inklayers and --no_svg")

    if args.path_in.is_dir() and args.path_out.is_file():
        return (False, "If path-in is a directory, path-out must also be a directory")

    if args.path_in.is_dir() and args.path_in.is_file():
        return (False, "If path-in is a directory, path-out must also be a directory")


    return (True, args)



def do_sdf_routine(args):
    imgs_out = []

    args.path_out = make_path(args.path_in, args.path_out, args.inklayers, args.atlas)

    # print("   Doing", args)

    if args.inklayers and args.no_svg:
        raise Exception("You cannot use both --inklayers and --no_svg")

    if args.path_in.is_dir() and args.path_out.is_file():
        raise Exception("If path-in is a directory, path-out must also be a directory")

    if args.path_in.is_dir() and args.path_in.is_file():
        raise Exception("If path-in is a directory, path-out must also be a directory")

    try:
        os.mkdir("./sdftmp")
    except FileExistsError:
        pass
    
    if args.path_in.is_dir():
        imgs_out += handle_dir(args)
    else:
        imgs_out += handle_file(args.path_in, args)
       
    save_images(imgs_out, args)


def make_arg_parser():
    parser = argparse.ArgumentParser(description='Makes SDF textures. See README.MD for usage examples.')
    parser.add_argument(
        'path_in', type=Path, help=
"""The path for the file or directory to process.
Will process each file in the directory. Must exist.""")
    parser.add_argument(
        '--path-out', type=Path, required=False, help=
"""Path for the destination file or folder.
If the path-in is a folder or --inklayers is used, path-out must be a folder.
Defaults to being an /sdf_out directory in the source dir""")
    parser.add_argument(
        '--main-color', type=Color, required=False, help=
"""The color that the resultant image will be. If none is provided, will default to 'white'""")
    parser.add_argument(
        '--color-underlay', type=str, required=False, default='white', help=
"""Color over which the source image will be placed before the sdf conversion.
Defaults to 'white'. To keep transparency, use --color-underlay transparent.
If the conversion results in weirdness, try setting this to the opposite of the shape's color""")
    parser.add_argument(
        '--inklayers', action="store_true", help=
"""If the image is an inkscape svg (or there are svgs in the folder), it will convert each layer
as its own seperate sdf image. It will then use the color of (the most) shapes in the layer
as that layer's main color unless another main color is explicitely provided. Use of this command
means that non-svg files will not be processed if a directory path is given. Has no effect if
the path is to a png file. Cannot be used with --no-svg""")
    parser.add_argument('--no-svg', action="store_true", help=
"""CURRENTLY BROKEN! Skips over any svg images in the folder. Has no effect if the path is to an svg
file. Cannot be used with --inklayers""")
    parser.add_argument(
        '--atlas', action="store_true", help=
"""Takes a collection of images, and puts them into an atlas. The images themselves should all be
the same w:h ratio, and the atlas will be the same number of images wide as it is tall 
(filling the empty space with transparency). If --inklayers is enabled, then one atlas will be made for each
inkscape document, rather then one that includes all of the images in the folder""")
    parser.add_argument(
        '--processes', type=int, required=False, default=None, help=
"""Sets the number of processes for the command to use. Defaults to the number of cores in the CPU.""")
    parser.add_argument(
        '--height', type=int, required=False, default=128, help=
"""The height dimension of the individual sdf image."""
    )
    parser.add_argument(
        '--keep-aspect', action="store_true", help=
"""Normally, the script coerces the output into a square. This makes the script not do that."""
    )
    parser.add_argument(
        '--kernel-size', type=int, required=False, default=15, help=
"""The size of the kernel that searches for distance from the edge."""
    )
    parser.add_argument(
        '--kernel-scale', type=int, required=False, default=100, help=
"""The amount that the kernel is scaled up or down while being applied."""
    )
    parser.add_argument(
        '--no-recursive', action="store_true", help=
"""Only process the files in the immediate directory, and do not process images in subdirectories"""
    )
    parser.add_argument(
        '--idempotent', action="store_true", help=
"""Records the hashes of source image files ('.csdf_idempotent_stash.json' in path-out), and when running again only converts files that have changed. Only has an effect when called on a directory."""
    )
    return parser

def make_relative_path_key(rootpath: Path, keypath: Path) -> str:
    relpath = keypath.resolve().relative_to(rootpath.resolve())
    return relpath.__str__()

def hashit(rootpath: Path, hashcollector: dict[str, dict[str, Any]], path: Path):
    rpath = make_relative_path_key(rootpath, path)
    if rpath in hashcollector.keys():
        return hashcollector[rpath]
    entire_file = path.read_bytes()
    hash64 = xxhash.xxh64(entire_file).hexdigest()
    hashcollector[rpath] = {'hash': hash64} # mutates, non-returned
    return hash64

def get_idempotent_stash(args):
    current_dir = args.path_in
    if current_dir.is_file():
        current_dir = current_dir.parent()
    idempotent_stash_path = current_dir / ".csdf_idempotent_stash.json"
    if idempotent_stash_path.exists():
        return json.loads(idempotent_stash_path.read_text())
    else:
        return {}

def stow_idempotent_stash(args, stash):
    current_dir = args.path_in
    if current_dir.is_file():
        current_dir = current_dir.parent() 
    idempotent_stash_path = current_dir / ".csdf_idempotent_stash.json"
    idempotent_stash_path.write_text(json.dumps(stash))

def has_hash_changed(rootpath: Path, path: Path, hashcollector: dict[str, dict[str, Any]], old_stash: dict[str, dict[str, Any]]) -> bool:
    rpath = make_relative_path_key(rootpath, path)
    if rpath in old_stash.keys():
        oldhash = old_stash[rpath]['hash']
        newhash = hashcollector[rpath]['hash']
        return oldhash != newhash
    else:
        return True

def get_every_img_path(dirpath, no_recursive=False):
    dirwalk = [x for x in os.walk(dirpath.resolve(True))]
    if no_recursive:
        dirwalk = [dirwalk[0]]
    initialvec = [z for z in [[(get_overrides_from_file(Path(x[0])), Path(x[0])/f) for f in x[2] if Path(f).suffix in format_suffixes] for x in dirwalk] for z in z]
    return [x for x in initialvec if not 'sdf_out' in [y.name for y in x[1].parents]]

def overriden_args(overrides, filepath):
    parser = make_arg_parser()
    parser.set_defaults(**overrides)
    args = parser.parse_args()
    args.path_in = filepath
    return args
    

def neo_exec():
    print("Pysdfer is starting")
    files_out = []
    # print("It's go time")
    tmpparser = make_arg_parser()
    tmpargs = tmpparser.parse_args()
    rpath = tmpargs.path_in.resolve(strict=True)
    overrides = get_overrides_from_file(tmpargs.path_in)
    parser = make_arg_parser()
    parser.set_defaults(**overrides)
    args = parser.parse_args()
    validsuccess = process_validate_args(args)
    hash_collector: dict[str, dict[str, Any]] = {}
    if not validsuccess[0]:
        raise Exception(validsuccess[1])
    print("Program running with the following initial flags:", args)
    # print("called with args:", args)
    try:
        os.mkdir("./sdftmp")
    except FileExistsError:
        pass
    
    #def handle_file(filepath: Path, args, blob_at_end = False, is_in_process = False):
    if rpath.is_dir():
        print("The path in is a directory, so we will scan for files...")
        every_image_path = get_every_img_path(rpath, args.no_recursive)
        argslist: list[argparse.Namespace] = [_args for (success, _args) in [process_validate_args(overriden_args(overrides, filepath)) for (overrides, filepath) in every_image_path] if success]
        if args.idempotent:
            print("Idempotent mode engaged. Gathering file hashes.")
            old_idempotent_stash = get_idempotent_stash(args) # linter gives me grief if it's not here
            [hashit(args.path_in, hash_collector, _args.path_in) for _args in argslist]
            print("File hashes gathered. Comparing old file hashes.")
            argslist = [_args for _args in argslist if has_hash_changed(args.path_in, _args.path_in, hash_collector, old_idempotent_stash)]
            print("File hashes compared.")
            if len(argslist) == 0:
                print("There are no changed files. Exiting program. Goodbye.")
                # We don't need to save another stash if there are no changed files.
        if len(argslist) == 1:
            _args = argslist[0]
            print("One file found:", _args.path_in.name) 
            files_out += handle_file(_args.path_in, _args)
        else:
            print("Multiple files found.")
            wrapped_argslist = [[_args] for _args in argslist]
            with alive_progress.alive_bar(len(argslist)) as bar:
                with Pool(args.processes) as p:
                    for result in p.imap(handle_file_for_process, argslist):
                        files_out += result
                        bar()
                    #res = p.starmap_async(handle_file_for_process, wrapped_argslist, callback=callback)
                    #res.wait()
                    #sm = res.get()
                    # [print('x, y', x, y) for [x, y] in sum(sm, [])]
                    # return []
                    #files_out += [(tmpname, path, args) for [tmpname, path, args] in sum(sm, [])]
    else:
        files_out += handle_file(rpath, args)

    print("Program converted all images. Saving now.")
    neo_save_images(files_out)
    # print("deleting the tmp dir")
    print("Images saved.")
    shutil.rmtree("./sdftmp", ignore_errors=True)
    if args.idempotent:
        print("Saving updated file hashes")
        stow_idempotent_stash(args, hash_collector)
    print("Program completed successfully. Goodbye.")



def exec():
    # print("pysdfer is starting")


    tmpparser = make_arg_parser()
    tmpargs = tmpparser.parse_args()
    rpath = tmpargs.path_in.resolve(strict=True)
    overrides = get_overrides_from_file(tmpargs.path_in)
    parser = make_arg_parser()
    parser.set_defaults(**overrides)
    args = parser.parse_args()
    # print("called with args:", args)
    # we do the root, and then do subdirs if the proper
    # 
    if args.recursive and rpath.is_dir():
        # print("walking directory tree")
        paths = os.walk(rpath)
        aspaths = [Path(p[0]) for p in paths]
        aspaths.pop(0)
        for subpath in aspaths:
            if subpath.name == 'sdf_out' or 'sdf_out' in [a.name for a in subpath.parents]:
                continue
            overrides = get_overrides_from_file(subpath)
            if overrides.get('skip-recursive') == True:
                continue
            parser = make_arg_parser()
            parser.set_defaults(**overrides)
            args = parser.parse_args()
            args.path_in = subpath
            try:
                do_sdf_routine(args)
            except Exception as e:
                pass
                # print("Encountered an exception doing", subpath)
                # print(e)
                # print("Moving on to the next one")
    else:
        do_sdf_routine(args)
    # print("deleting the tmp dir")
    shutil.rmtree("./sdftmp", ignore_errors=True)


if __name__ == "__main__":
    neo_exec()
