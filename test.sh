#!/bin/bash

# python3 -m pysdfer ./testimg/tiger_rect.png
# python3 -m pysdfer ./testimg/palm_black.png --path-out ./testimg_out
# python3 -m pysdfer ./testimg/one_layer.ink.svg --path-out ./testimg_out/one_layer.ink.png # --main-color white
# python3 -m pysdfer ./testimg/one_layer.plain.svg --path-out ./testimg_out/one_layer.plain.png --main-color green
# ./pysdfer.py --inklayers --atlas ./testimg/multi_layer.ink.svg --path-out ./testimg_out
./pysdfer.py --inklayers --atlas ./testimg/shiptest.svg --path-out ./testimg_out --height 256
# python3 -m pysdfer ./testimg --inklayers
# python3 -m pysdfer ./testimg/palm_black_a.png --path-out ./testimg_out --color-underlay white
# python3 -m pysdfer ./testimg/palm_white_a.png --path-out ./testimg_out --color-underlay black
