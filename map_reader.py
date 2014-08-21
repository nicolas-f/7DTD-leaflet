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
from PIL import Image

##
# Convert X Y position to MAP file index


def index_from_xy(x, y):
    return (y & 65535) << 16 | (x & 65535)


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
                print "New tiles :", new_tiles
            else:
                self.tiles = dict.fromkeys(tiles_index + self.tiles.keys())


def write_tile(tile_data, png_path):
    tile_im = Image.frombuffer('RGB', (16, 16), tile_data, 'raw', 'RGB', 0, 1)
    tile_im.save(png_path)
def create_tiles(player_map_path, tile_output_path, tile_level=7):
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
    # keys = reader.tiles.keys()
    # index_tiles = {}
    # for x in range(-(tile_range/2), (tile_range/2)):
    #     for y in range(-(tile_range/2), (tile_range/2)):
    #         index_tiles[index_from_xy(x, y)] = (x, y)
    # xmin = tile_range
    # ymin = tile_range
    # xmax = -1
    # ymax = -tile_range
    # xkeys = [index_tiles.get(key, (None, None))[0] for key in keys if key in index_tiles]
    # ykeys = [index_tiles.get(key, (None, None))[1] for key in keys if key in index_tiles]
    # print "Map bounds :", -(tile_range/2),"x", tile_range/2
    # print "Minx:", min(xkeys)," maxx:", max(xkeys)
    # print "Miny:", min(ykeys)," maxy:", max(ykeys)
    # iterate on x
    for x in range(2**tile_level):
        print "Write tile X:", x + 1, " of ", 2**tile_level
        x_dir_make = False
        x_path = os.path.join(z_path, str(x))
        for y in range(2**tile_level):
            # Fetch 256 tiles
            pass
    #     x_dir_make = False
    #     x_path = os.path.join(z_path, str(x + 2**tile_level/2))
    #     for y in range(-(2**tile_level/2), (2**tile_level/2)):
    #         tile_data = reader.tiles.get(index_from_xy(x,(2**tile_level/2) - y), None)
    #         if tile_data is not None:
    #             # Create Dirs if not exists
    #             if not x_dir_make:
    #                 if not os.path.exists(x_path):
    #                     os.mkdir(x_path)
    #                     x_dir_make = True
    #             png_path = os.path.join(x_path, str(y + 2**tile_level/2)+".png")
    #             write_tile(tile_data, png_path)


def read_folder(path):
    map_files = [os.path.join(path, file_name) for file_name in os.listdir(path) if file_name.endswith(".map")]
    map_files.sort(key=lambda file_path: -os.stat(file_path).st_mtime)
    return map_files
create_tiles(read_folder("E:\\github\\Player"),
             "tiles")
