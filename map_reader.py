#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of 7dtd-prefabs.
#
# 7dtd-prefabs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# 7dtd-prefabs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with 7dtd-prefabs. If not, see <http://www.gnu.org/licenses/>.
# Source code hosted at https://github.com/nicolas-f/7dtd-prefabs
# @author Nicolas Fortin github@nettrader.fr https://github.com/nicolas-f
# @author Nicolas Grimaud ketchu13@hotmail.com

from struct import unpack
import os
# Need Pillow https://pillow.readthedocs.org/en/latest/
from PIL import Image, ImageOps
import itertools

##
# Convert X Y position to MAP file index


def index_from_xy(x, y):
    return y << 16 | (x & 65535)


class MapReader:
    tiles = {}

    def __init__(self):
        pass
    def import_file(self, map_file, index_only, skip_existing=True):
        with open(map_file, "rb") as curs:
            # Check beginning of file
            if not curs.read(4) == "map\0":
                raise Exception("Wrong file header.")
            curs.read(1)
            #######################
            # read index
            num = unpack("I", curs.read(4))[0]
            print "Tiles :", num
            # read tiles position
            tiles_index = [unpack("i", curs.read(4))[0] for i in xrange(num)]
            #######################
            # read tiles pixels
            new_tiles = 0
            if not index_only:
                curs.seek(524297)
                for i in xrange(num):
                    if not skip_existing or tiles_index[i] not in self.tiles:
                        #extract 16-bytes pixel then convert to RGB component
                        chunk = [[[((rgb & 0x7C00) >> 10 << 3), ((rgb & 0x3E0) >> 5) << 3, (rgb & 0x1F) << 3]
                                 for rgb in unpack("H", curs.read(2))][0] for c in xrange(256)]
                        #flatten pixels and convert to char
                        chunk = "".join([chr(band) for pixel in chunk for band in pixel])
                        self.tiles[tiles_index[i]] = chunk
                        new_tiles += 1
                    else:
                        curs.seek(curs.tell() + 512)
                print "New tiles :", new_tiles
            else:
                self.tiles = dict.fromkeys(tiles_index + self.tiles.keys())

def create_tiles(player_map_path, tile_output_path, tile_level=8):
    """
     Call base tile and intermediate zoom tiles
    """
    create_base_tiles(player_map_path, tile_output_path, tile_level)
    create_low_zoom_tiles(tile_output_path, tile_level)

def create_base_tiles(player_map_path, tile_output_path, tile_level):
    """
    Read all .map files and create a leaflet tile folder
    @param player_map_path array of folder name where are stored map ex:C:\Users\UserName\Documents\7 Days To Die\Saves\
    Random Gen\lll\Player\76561197968197169.map
    @param tile_level number of tiles to extract around position 0,0 of map. It is in the form of 4^n tiles.It will
    extract a grid of 2**n tiles on each side. n=8 will give you an extraction of -128 +128 in X and Y tiles index.
    """
    reader = MapReader()
    # Read and merge all tiles in .map files
    for i, map_file in enumerate(player_map_path):
        print "Read map file ", i + 1, "/", len(player_map_path)
        reader.import_file(map_file, False)
    # make zoom folder
    z_path = os.path.join(tile_output_path, str(tile_level))
    if not os.path.exists(z_path):
        os.mkdir(z_path)
    #compute min-max X Y
    tile_range = 2**tile_level*16
    # iterate on x
    minmax_tile = [(tile_range, tile_range),(-tile_range, -tile_range)]
    used_tiles = 0
    for x in range(2**tile_level):
        print "Write tile X:", x + 1, " of ", 2**tile_level
        x_dir_make = False
        x_path = os.path.join(z_path, str(x))
        for y in range(2**tile_level):
            # Fetch 256 tiles
            big_tile = None
            # Combine two for loop into one
            for tx, ty in itertools.product(range(16), range(16)):
                world_txy = (x * 16 + tx - tile_range / 2, y * 16 + ty - tile_range / 2)
                tile_data = reader.tiles.get(index_from_xy(world_txy[0], world_txy[1]))
                if not tile_data is None:
                    used_tiles += 1
                    minmax_tile = [(min(minmax_tile[0][0], world_txy[0]), min(minmax_tile[0][1], world_txy[1])),
                                   (max(minmax_tile[1][0], world_txy[0]), max(minmax_tile[1][1], world_txy[1]))]
                    # Add this tile to big tile
                    # Create empty big tile if not exists
                    if big_tile is None:
                        big_tile = Image.new("RGB", (256, 256))
                    # convert image string into pil image
                    tile_im = Image.frombuffer('RGB', (16, 16), tile_data, 'raw', 'RGB', 0, 1)
                    # Push this tile into the big one
                    big_tile.paste(tile_im, (tx * 16, ty * 16))
            # All 16pix tiles of this big tile has been copied into big tile
            # Time to save big tile
            if not big_tile is None:
                # Create Dirs if not exists
                if not x_dir_make:
                    if not os.path.exists(x_path):
                        os.mkdir(x_path)
                        x_dir_make = True
                png_path = os.path.join(x_path, str(2**tile_level - y)+".png")
                big_tile = ImageOps.flip(big_tile)
                big_tile.save(png_path, "png")
    print "Min max tiles minx:", minmax_tile[0][0], " maxx:", minmax_tile[1][0],\
          "miny:", minmax_tile[0][1], " maxy: ", minmax_tile[1][1]
    print "Tiles used / total read", used_tiles, " / ", len(reader.tiles)


def create_low_zoom_tiles(tile_output_path, tile_level):
    """
        Merge 4 tiles of 256x256 into a big 512x512 tile then resize to 256x256
    """
    z_path = os.path.join(tile_output_path, str(tile_level))
    z_lower_path = os.path.join(tile_output_path, str(tile_level - 1))
    if not os.path.exists(z_lower_path):
        os.mkdir(z_lower_path)
    # list all X folders, convert to int then sort ascending
    tiles_to_process = set()
    x_paths = map(lambda x: int(x), os.listdir(z_path))
    for x_path in sorted(x_paths):
        for y_path in map(lambda y: int(y[:-4]), os.listdir(os.path.join(z_path, str(x_path)))):
            tiles_to_process.add((x_path, y_path))
    while len(tiles_to_process) > 0:
        tile_to_process = next(iter(tiles_to_process))
        # compute id of origin tile
        orig_tile = (tile_to_process[0] - tile_to_process[0] % 2, tile_to_process[1] - tile_to_process[1] % 2)
        # compute the index of the 4 tiles
        tiles = [orig_tile, #bottom left
                 (orig_tile[0] + 1, orig_tile[1]), #bottom right
                 (orig_tile[0], orig_tile[1] + 1), #top left
                 (orig_tile[0] + 1, orig_tile[1] + 1)] #top right
        tiles_paste_pos = [(0, 0), (256, 0), (0, 256), (256, 256)]
        # Remove tiles from processing
        missing_tiles = set()
        for tile_index in tiles:
            if tile_index in tiles_to_process:
                tiles_to_process.remove(tile_index)
            else:
                missing_tiles.add(tile_index)
        lower_zoom_image = Image.new("RGB", (512, 512))
        for tile_index, paste_pos in zip(*[tiles, tiles_paste_pos]):
            if tile_index not in missing_tiles:
                # Compute path
                tile_index_path = os.path.join(z_path, str(tile_index[0]), str(tile_index[1])+".png")
                tile_im = Image.open(tile_index_path)
                # Paste in big image
                lower_zoom_image.paste(tile_im, paste_pos)
        # Dezoom the big tile
        lower_zoom_image = lower_zoom_image.resize((256, 256), Image.BICUBIC)
        # Save in lower zoom folder
        x_lower_path = os.path.join(z_lower_path, str(orig_tile[0] / 2))
        if not os.path.exists(x_lower_path):
            os.mkdir(x_lower_path)
        lower_zoom_image.save(os.path.join(x_lower_path, str(orig_tile[1] / 2)+".png"))
def read_folder(path):
    if not os.path.exists(path):
        os.mkdir(path)
    map_files = [os.path.join(path, file_name) for file_name in os.listdir(path) if file_name.endswith(".map")]
    map_files.sort(key=lambda file_path: -os.stat(file_path).st_mtime)
    return map_files
#create_tiles(read_folder("E:\\github\\Player"),
#             "tiles")
create_low_zoom_tiles("tiles", 8)