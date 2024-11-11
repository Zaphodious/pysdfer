#!/usr/bin/env bash


rm -rf ./examples/sdf_out/
./pysdfer.py ./examples/Goethe.jpg
./pysdfer.py ./examples/one_layer.ink.svg 
./pysdfer.py ./examples/one_layer.plain.svg --main-color green
./pysdfer.py --inklayers --atlas ./examples/multi_layer.ink.svg 
./pysdfer.py --inklayers --atlas ./examples/shiptest.svg --height 256
./pysdfer.py ./examples --inklayers --path-out ./examples/sdf_out/bulk_inklayers

