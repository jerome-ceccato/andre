#!/usr/bin/env python3

import asyncio
import discord
import os, sys
import math
from PIL import Image

def create_image_composition(from_image_paths, output_path):
    images = [Image.open(f) for f in from_image_paths]

    nb_images = len(images)
    squares = int(math.ceil(math.sqrt(nb_images)))
    h_squares = int(math.ceil(nb_images / squares))

    margin_w = 10
    margin_h = 10

    max_w = max(image.size[0] for image in images)
    max_h = max(image.size[1] for image in images)

    width = squares * max_w + (squares + 1) * margin_w
    height = h_squares * max_h + (h_squares + 1) * margin_h

    result_image = Image.new(mode='RGBA', size=(width, height), color=(0,0,0,0))

    for i, image in enumerate(images):
        target_square_x = margin_w + (i % squares) * (max_w + margin_w)
        target_square_y = margin_h + int(i / squares) * (max_h + margin_h)

        bounds_offset_x = int((max_w - image.size[0]) / 2)
        bounds_offset_y = int((max_h - image.size[1]) / 2)

        content_offset = (target_square_x + bounds_offset_x, target_square_y + bounds_offset_y)

        result_image.paste(image, content_offset)

    result_image.save(output_path)
    return output_path
