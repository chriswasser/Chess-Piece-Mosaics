#!/usr/bin/env python3

from itertools import chain
from math import sqrt
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


def replace_transparent(transparent, colour="WHITE"):
    nontransparent = Image.new("RGBA", transparent.size, colour)
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


piece_dir = 'Chess-Pieces'
image_path = 'Images/iSchach-Logo.png'
num_sets = 2000
num_pieces = 32
block_size = 1

num_blocks = num_sets * num_pieces
pairs = factor_pairs(num_blocks)
ratios = [width / height for width, height in pairs]

target = ImageOps.grayscale(replace_transparent(Image.open(image_path).convert('RGBA')))
target_ratio = target.width / target.height

min_diff, min_pair = float('inf'), (-1, -1)
for pair, ratio in zip(pairs, ratios):
    diff = abs(target_ratio - ratio)
    if diff < min_diff:
        min_diff, min_pair = diff, pair
num_blocks_width, num_blocks_height = min_pair

width, height = num_blocks_width * block_size, num_blocks_height * block_size
target = target.resize((width, height), resample=Image.LANCZOS, reducing_gap=3)
pixels = np.array(target).T

piece_paths = [
    os.path.join(piece_dir, 'Black-Bishop.png'),
    os.path.join(piece_dir, 'Black-King.png'),
    os.path.join(piece_dir, 'Black-Knight.png'),
    os.path.join(piece_dir, 'Black-Pawn.png'),
    os.path.join(piece_dir, 'Black-Queen.png'),
    os.path.join(piece_dir, 'Black-Rook.png'),
    os.path.join(piece_dir, 'White-Bishop.png'),
    os.path.join(piece_dir, 'White-King.png'),
    os.path.join(piece_dir, 'White-Knight.png'),
    os.path.join(piece_dir, 'White-Pawn.png'),
    os.path.join(piece_dir, 'White-Queen.png'),
    os.path.join(piece_dir, 'White-Rook.png'),
]
pieces = [Image.open(path) for path in piece_paths]
bbox = min_square_bbox(pieces)
pieces = [ImageOps.grayscale(piece.crop(bbox)) for piece in pieces]
brightnesses = [sum(piece.getdata()) / (piece.width * piece.height) for piece in pieces]

c = {}
for i in range(num_blocks_width):
    for j in range(num_blocks_height):
        brightness = np.sum(pixels[i*block_size:(i+1)*block_size, j*block_size:(j+1)*block_size]) / block_size ** 2
        for k in range(len(pieces)):
            c[i, j, k] = (brightnesses[k] - brightness) ** 2

per_set = {}
for k, piece_path in enumerate(piece_paths):
    if 'Pawn' in piece_path:
        per_set[k] = 8
    if 'Bishop' in piece_path or 'Knight' in piece_path or 'Rook' in piece_path:
        per_set[k] = 2
    if 'King' in piece_path or 'Queen' in piece_path:
        per_set[k] = 1

model = grb.Model('Chess-Piece-Mosaic')

# x[i,j,k] equals to 1 if the chess piece k is placed in block (i, j), otherwise x[i,j,k] equals to 0
x = {}
for i in range(num_blocks_width):
    for j in range(num_blocks_height):
        for k in range(len(pieces)):
            x[i, j, k] = model.addVar(obj=c[i, j, k], vtype=grb.GRB.BINARY, name=f'x_{i}_{j}_{k}')

# set type of optimization
model.ModelSense = grb.GRB.MINIMIZE

# exactly one piece per block
for i in range(num_blocks_width):
    for j in range(num_blocks_height):
        model.addConstr(grb.quicksum(x[i, j, k] for k in range(len(pieces))) == 1)

# exactly one piece per block
for k in range(len(pieces)):
    model.addConstr(grb.quicksum(x[i, j, k] for i in range(num_blocks_width) for j in range(num_blocks_height)) == num_sets * per_set[k])

model.update()
model.optimize()


solution = np.empty(shape=(num_blocks_width, num_blocks_height), dtype=object)
for i in range(num_blocks_width):
    for j in range(num_blocks_height):
        for k in range(len(pieces)):
            if x[i, j, k].X:
                solution[i, j] = pieces[k]
mosaic = assemble(solution, pieces[0].width)

target.save('Target.png')
mosaic.save('Mosaic.png')
