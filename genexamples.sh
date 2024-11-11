#!/usr/bin/env bash


rm -rf ./examples/sdf_out/
./pysdfer.py ./examples/tiger_rect.png
./pysdfer.py ./examples/palm_black.png
./pysdfer.py ./examples/palm_black_a.png --color-underlay white
./pysdfer.py ./examples/palm_white_a.png --color-underlay black
./pysdfer.py ./examples/one_layer.ink.svg 
./pysdfer.py ./examples/one_layer.plain.svg --main-color green
./pysdfer.py --inklayers --atlas ./examples/multi_layer.ink.svg 
./pysdfer.py --inklayers --atlas ./examples/shiptest.svg --height 256 # --main-color white
./pysdfer.py ./examples --inklayers --path-out ./examples/sdf_out/bulk_inklayers

