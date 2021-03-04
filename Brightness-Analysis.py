#!/usr/bin/env python3

import os
from glob import glob
import itertools

import matplotlib.pyplot as plt
from PIL import Image, ImageOps


def plot(brightnesses, pieces, filename=None):
    plt.clf()
    brightnesses, pieces = zip(*sorted(zip(brightnesses, pieces)))
    plt.plot(pieces, brightnesses, marker='o')
    plt.xticks(rotation=45, ha='right')
    plt.ylim(0, 255)
    plt.xlabel('Chess Piece')
    plt.ylabel('Average Pixel Value')
    plt.tight_layout()
    plt.savefig(filename, dpi=300) if filename else None
    plt.show()

def replace_transparent(transparent, colour="WHITE"):
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


pieceset_dirs_base = 'Chess-Piece-Sets-Ready'
piecesets = [
    'cburnett',
    'merida',
    'icpieces',
    'cardinal',
    'newspaper',
    'classic',
    'outlined',
]
backgrounds = {
    'minmax': ('rgb(255, 255, 255)', 'rgb(0, 0, 0)'),
    'dark': ('rgb(169, 169, 169)', 'rgb(134, 134, 134)'),
    'light': ('rgb(220, 220, 220)', 'rgb(171, 171, 171)'),
}

colours = ['Black', 'White']
pieces = ['Bishop', 'King', 'Knight', 'Pawn', 'Queen', 'Rook']

pieceset_dirs = [os.path.join(pieceset_dirs_base, pieceset) for pieceset in piecesets]
for background_name, (white, black) in backgrounds.items():
    for pieceset_dir in pieceset_dirs:
        piece_paths = [os.path.join(pieceset_dir, f'{colour}-{piece}.png') for colour, piece in itertools.product(colours, pieces)]
        piece_images = [Image.open(path).convert('RGBA') for path in piece_paths]
        bbox = min_square_bbox(piece_images)
        piece_images = [ImageOps.grayscale(replace_transparent(piece.crop(bbox), colour=white)) for piece in piece_images] + \
                        [ImageOps.grayscale(replace_transparent(piece.crop(bbox), colour=black)) for piece in piece_images]
        brightnesses = [sum(piece.getdata()) / (piece.width * piece.height) for piece in piece_images]

        pieceset_name = os.path.basename(pieceset_dir)
        plt.scatter([background_name + '-' + pieceset_name for _ in range(len(brightnesses))], brightnesses, c='black')
plt.xticks(rotation=45, ha='right')
plt.ylim(0, 255)
plt.xlabel('Background & Chess Piece Set Combination')
plt.ylabel('Average Pixel Value')
plt.tight_layout()
plt.savefig('Brightness-Plot.png', dpi=300)
