# PYthon SDF convertER

Given an image containing a shape, converts into an SDF texture

Please see (link) for godot shaders which 

By default, the app expects a black black shape on a white background,
and will output to an directory within the target directory named /sdf_out.

The *.csdf.png extension used indicates a color sdf image, and just makes it obvious
what we're dealing with

## Example usage

The script pysdfer.py stands on its own once its requirements are installed.
This means that on Windows, a .bat file pointing to the script can be created quite easily.

Processing an individual image, letting it be output to the default 'sdf_out' folder

```python3 -m pysdfer ./testimg/palm_black.png```

Processing an individual image, outputting to a specified folder:

```python3 -m pysdfer ./testimg/palm_black.png --path-out ./testimg_out```

Procesing an inkscape document, resulting in each layer output as its own sdf texture:

 ```python3 -m pysdfer --inklayers ./testimg/multi_layer.ink.svg --path-out ./testimg_out```

Processing a transparent image using a color-underlay:

```python3 -m pysdfer ./testimg/palm_black_a.png --path-out ./testimg_out --color-underlay white```

Processing a folder, letting it output to the default 'sdf_out' folder

```python3 -m pysdfer ./testimg```


Output of --help

```
usage: pysdfer.py [-h] [--path-out PATH_OUT] [--main-color MAIN_COLOR]
                  [--color-underlay COLOR_UNDERLAY] [--inklayers] [--atlas] [--processes PROCESSES]     
                  path_in

Makes SDF textures

positional arguments:
  path_in               The path for the file or directory to process. Will process each file in the    
                        directory. Must exist.

optional arguments:
  -h, --help            show this help message and exit
  --path-out PATH_OUT   Path for the destination file or folder. If the path-in is a folder, path-out   
                        must be a folder. Defaults to being an /sdf_out directory in the source dir
  --main-color MAIN_COLOR
                        The color that the resultant image will be. If none is provided, will default   
                        to 'white'
  --color-underlay COLOR_UNDERLAY
                        Color over which the source image will be placed before the sdf conversion. If  
                        none is provided, the image's alpha will simply be removed. If the conversion   
                        results in weirdness, try setting this to the opposite of the shape's color     
  --inklayers           If the image is an inkscape svg (or there are svgs in the folder), it will      
                        convert each layer as its own seperate sdf image. It will then use the color    
                        of (the most) shapes in the layer as that layer's main color unless another     
                        main color is explicitely provided
  --atlas               Takes a collection of images, and puts them into an atlas. The images
                        themselves should all be the same w:h ratio, and the atlas will be the same     
                        number of images wide as it is tall (filling the empty space with transparency  
  --processes PROCESSES
                        Sets the number of processes for the command to use. Defaults to 10.
```