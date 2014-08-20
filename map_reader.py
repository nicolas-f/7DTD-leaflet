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
import png
from Tkinter import Tk, PhotoImage

##
# Convert X Y position to MAP file index


def index_from_xy(x, y):
    return (y & 65535) << 16 | (x & 65535)


class MapReader:
    tiles = {}

    def __init__(self):
        pass

    def import_file(self, map_file):
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
            curs.seek(524297)
            for i in xrange(num):
                # extract 16-bytes pixel then convert to RGB component
                chunk = [[[((rgb & 0x7C00) >> 10 << 3), ((rgb & 0x3E0) >> 5) << 3, (rgb & 0x1F) << 3]
                          for rgb in unpack("H", curs.read(2))][0] for c in xrange(256)]
                self.tiles[tiles_index[i]] = chunk


def create_image_from_tile(tile_data):
    tile_image = PhotoImage(width=16, height=16)
    rgb = [[tile_data[x * 16 + y] for x in range(16)] for y in range(16)]
    horizontal_line = " ".join(["{" + " ".join(["#%02x%02x%02x" % tuple(blockId) for blockId in row]) + "}"
                                for row in rgb])
    tile_image.put(horizontal_line)
    return tile_image


def create_tiles(player_map_path, tile_output_path, tile_level=8):
    """
    Read all .map files and create a leaflet tile folder
    @param player_map_path array of folder name where are stored map ex:C:\Users\UserName\Documents\7 Days To Die\Saves\
    Random Gen\lll\Player\76561197968197169.map
    @param tile_level number of tiles to extract around position 0,0 of map. It is in the form of 4^n tiles.It will
    extract a grid of 2**n tiles on each side. n=8 will give you an extraction of -128 +128 in X and Y tiles index.
    """
    master = Tk()
    reader = MapReader()
    # Read and merge all tiles in .map files
    for map_file in player_map_path:
        reader.import_file(map_file)
    # make zoom folder
    z_path = os.path.join(tile_output_path, str(tile_level / 2))
    if not os.path.exists(z_path):
        os.mkdir(z_path)
    # iterate on x
    for x in range(-(2**tile_level/2), (2**tile_level/2)):
        x_dir_make = False
        x_path = os.path.join(z_path, str(x + 2**tile_level/2))
        for y in range(-(2**tile_level/2), (2**tile_level/2)):
            tile_data = reader.tiles.get(index_from_xy(y, x), None)
            if tile_data is not None:
                tile_image = create_image_from_tile(tile_data)
                # Create Dirs if not exists
                if not x_dir_make:
                    if not os.path.exists(x_path):
                        os.mkdir(x_path)
                        x_dir_make = True
                png_path = os.path.join(x_path, str(y + 2**tile_level/2)+".gif")
                tile_image.write(png_path, "gif")

create_tiles(["C:\\Users\\CUMU\\Documents\\7 Days To Die\\Saves\\Random Gen\\lll\\Player\\76561197968197169.map"],
             "tiles")