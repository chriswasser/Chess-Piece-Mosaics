#!/usr/bin/env python3

from itertools import chain, product
from math import sqrt, floor, ceil
import os
from pathlib import Path

import gurobipy as grb
import numpy as np
from PIL import Image, ImageOps


# assume that blocks are all equally sized
def assemble(blocks, block_size):
    image = Image.new('L', size=(block_size * blocks.shape[0], block_size * blocks.shape[1]))
    for i in range(blocks.shape[0]):
        for j in range(blocks.shape[1]):
            image.paste(blocks[i, j], (i * block_size, j * block_size))
    return image


def factor_pairs(number):
    return [(x, number // x) for x in range(1, number + 1) if number % x == 0]


def replace_transparent(transparent, colour='WHITE'):
    nontransparent = Image.new('RGBA', transparent.size, colour)
    nontransparent.paste(transparent, (0, 0), transparent)
    return nontransparent.convert('RGB')


def min_bbox(images):
    minx1, minx2 = float('inf'), float('inf')
    maxx1, maxx2 = float('-inf'), float('-inf')
    for image in images:
        bbox = image.getbbox()
        minx1, minx2 = min(minx1, bbox[0]), min(minx2, bbox[1])
        maxx1, maxx2 = max(maxx1, bbox[2]), max(maxx2, bbox[3])
    return (minx1, minx2, maxx1, maxx2)

def min_square_bbox(images):
    bbox = min_bbox(images)
    x, y = min(bbox[0], bbox[1]), max(bbox[2], bbox[3])
    return (x, x, y, y)


########################################################################################################################
# customize mosaic
########################################################################################################################
target_path = 'Samples/Magnus-Carlsen-Original.jpg'
num_sets = 2847

pieceset_dir = 'Chess-Piece-Sets-Ready/cburnett'
background = {'Bright': 'rgb(169, 169, 169)', 'Dark': 'rgb(134, 134, 134)'}

num_pieces = 32
block_size = 1

########################################################################################################################
# determine the best number of block in each dimension based on the original image's aspect ratio
########################################################################################################################
num_blocks = num_sets * num_pieces
pairs = factor_pairs(num_blocks)
ratios = [width / height for width, height in pairs]

target_image = ImageOps.grayscale(replace_transparent(Image.open(target_path).convert('RGBA')))
target_ratio = target_image.width / target_image.height

min_diff, min_pair = float('inf'), (-1, -1)
for pair, ratio in zip(pairs, ratios):
    diff = abs(target_ratio - ratio)
    if diff < min_diff:
        min_diff, min_pair = diff, pair
num_blocks_width, num_blocks_height = min_pair

# high quality resampling to the required dimensionality
target_image = target_image.resize((num_blocks_width * block_size, num_blocks_height * block_size), resample=Image.LANCZOS, reducing_gap=3)
pixels = np.array(target_image).T


########################################################################################################################
# read image pieces for LP
########################################################################################################################
colours = ['Black', 'White']
pieces = ['Bishop', 'King', 'Knight', 'Pawn', 'Queen', 'Rook']

piece_images = {
    (colour, piece, shade): Image.open(os.path.join(pieceset_dir, f'{colour}-{piece}.png')).convert('RGBA')
    for colour, piece, shade in product(colours, pieces, background)
}
bbox = min_square_bbox(list(piece_images.values()))
piece_images = {
    (colour, piece, shade): ImageOps.grayscale(replace_transparent(piece_image.crop(bbox), colour=background[shade]))
    for (colour, piece, shade), piece_image in piece_images.items()
}
brightnesses = {
    (colour, piece, shade): sum(piece_image.getdata()) / (piece_image.width * piece_image.height)
    for (colour, piece, shade), piece_image in piece_images.items()
}

c = {}
for i in range(num_blocks_width):
    for j in range(num_blocks_height):
        brightness = np.sum(pixels[i*block_size:(i+1)*block_size, j*block_size:(j+1)*block_size]) / block_size ** 2
        for k in piece_images:
            c[i, j, k] = (brightnesses[k] - brightness) ** 2

# TODO: fix per set definition considering multiple background shades
def num_occurrences(colour, piece, shade, num_sets):
    if 'Pawn' == piece:
        return 4 * num_sets
    if 'Bishop' == piece or 'Knight' == piece or 'Rook' == piece:
        return 1 * num_sets
    if 'King' == piece:
        if shade == 'Bright':
            return floor(num_sets / 2)
        if shade == 'Dark':
            return ceil(num_sets / 2)
    if 'Queen' == piece:
        if shade == 'Bright':
            return ceil(num_sets / 2)
        if shade == 'Dark':
            return floor(num_sets / 2)

model = grb.Model('Chess-Piece-Mosaic')

# x[i,j,k] equals to 1 if the chess piece k is placed in block (i, j), otherwise x[i,j,k] equals to 0
x = {}
for i in range(num_blocks_width):
    for j in range(num_blocks_height):
        for k in piece_images:
            x[i, j, k] = model.addVar(obj=c[i, j, k], vtype=grb.GRB.BINARY, name=f'x_{i}_{j}_{k}')

# set type of optimization
model.ModelSense = grb.GRB.MINIMIZE

# exactly one piece per block
for i in range(num_blocks_width):
    for j in range(num_blocks_height):
        model.addConstr(grb.quicksum(x[i, j, k] for k in piece_images) == 1)

# exactly one piece per block
for k in piece_images:
    model.addConstr(grb.quicksum(x[i, j, k] for i in range(num_blocks_width) for j in range(num_blocks_height)) == num_occurrences(*k, num_sets))

model.update()
model.optimize()

########################################################################################################################
# write solution
########################################################################################################################
solution = np.empty(shape=(num_blocks_width, num_blocks_height), dtype=object)
for i in range(num_blocks_width):
    for j in range(num_blocks_height):
        for k in piece_images:
            if x[i, j, k].X:
                solution[i, j] = piece_images[k]
mosaic = assemble(solution, bbox[2] - bbox[0])

target_image.save('Target.png')
mosaic.save('Mosaic.png')
