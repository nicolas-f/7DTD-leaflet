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
from __future__ import print_function

import io
import struct
import itertools
import getopt
import sys
import os
import time
import sqlite3
__version__ = "1.4.0-dev"

print("Welcome to 7DTD leaflet builder version " + __version__)

try:
    from PIL import Image, ImageOps
except ImportError:
    print("This program require:")
    print("Pillow https://pillow.readthedocs.org/en/latest/")
    exit(-1)

##
# Convert X Y position to MAP file index


def index_from_xy(x, y):
    return (y - 16) << 16 | (x & 65535)


class MapReader:
    db = None
    store_history = False
    tiles_file_path = {}
    known_tiles = set()
    new_tiles = 0

    def __init__(self, database_directory, store_history):
        self.db = sqlite3.connect(os.path.join(database_directory, 'tile_history.db'))
        self.db.text_factory = str
        self.store_history = store_history
        self.db.execute("CREATE TABLE IF NOT EXISTS TILES(POS int,HASH int, T TIMESTAMP, data CHAR(512),"
                        " PRIMARY KEY(POS,HASH))")
        self.db.execute("CREATE TABLE IF NOT EXISTS VERSION as select 1 version")
        # Read already known index
        for record in self.db.execute("SELECT DISTINCT POS FROM TILES"):
            self.known_tiles.add(record[0])

    def is_tile_stored(self, index):
        return index in self.known_tiles

    def do_insert_tile(self, index, tile_hash):
        if self.store_history:
            # Check if the tile is not already in the db
            rs = self.db.execute("SELECT COUNT(*) CPT FROM TILES WHERE POS=? AND HASH=?", [index, tile_hash])
            if rs.fetchone()[0] == 0:
                return True
            else:
                return False
        else:
            return True

    def insert_tile(self, index, data, file_date):
        tile_hash = hash(data)
        if self.do_insert_tile(index, tile_hash):
            self.db.execute("INSERT INTO TILES VALUES (?,?,?,?)", [index, tile_hash, file_date, data])
            self.known_tiles.add(index)
            return True
        else:
            return False

    def fetch_tile(self, index):
        if not self.is_tile_stored(index):
            return None
        if self.store_history:
            data = self.db.execute("SELECT data FROM TILES WHERE POS=? ORDER BY T DESC LIMIT 1", [index]).fetchone()
            if not data is None:
                return data[0]
            else:
                return None
        else:
            data = self.db.execute("SELECT data FROM TILES WHERE POS=? LIMIT 1", [index]).fetchone()
            if not data is None:
                return data[0]
            else:
                return None

    def import_file(self, map_file, index_only):
        file_date = os.stat(map_file).st_mtime
        with open(map_file, "rb") as curs:
            # Check beginning of file
            header_magic = curs.read(4).decode('ascii')
            if not header_magic.startswith("map"):
                print("Skip " + os.path.basename(map_file) + " wrong file header")
                return
            ## Read version
            version = struct.unpack("I", curs.read(4))[0]

            tiles_pos = 524297
            if version == 2:
                tiles_pos = 524300
            elif version == 3:
                # Credits to DorHans & Seraphin for support of version 3
                max_tiles_count = struct.unpack("I", curs.read(4))[0]
                tiles_pos = max_tiles_count * 4 + 16
            else:
                print("Warning old map version or unsupported: ", version)
                curs.seek(5)

            #######################
            # read index
            num = struct.unpack("I", curs.read(4))[0]

            # read tiles position
            tiles_index = [struct.unpack("i", curs.read(4))[0] for i in range(num)]
            #######################
            # read tiles pixels
            if not index_only:
                curs.seek(tiles_pos)
                for i in range(num):
                    if self.store_history or not self.is_tile_stored(tiles_index[i]):
                        # extract 16-bytes pixel 16*16 tile
                        tile_data = curs.read(512)
                        if len(tile_data) == 512:
                            if self.insert_tile(tiles_index[i], tile_data, file_date):
                                self.tiles_file_path[tiles_index[i]] = map_file
                                self.new_tiles += 1
                        else:
                            # Corrupted file
                            print("Skip " + os.path.basename(map_file) + " may be already used by another process")
                            break
                    else:
                        curs.seek(curs.tell() + 512)
            else:
                self.tiles = dict.fromkeys(tiles_index + self.tiles.keys())
        self.db.commit()


##
# Python equivalent for csharp BinaryReader.ReadString
# test with read7_bit_encoded_int(io.BytesIO(b'\x18BuffEntityUINotification\x00'))
def read_cs_string(curs):
    count = 0
    shift = 0
    byte_conversion = struct.Struct("B")
    while True:
        if shift == 5 * 7:
            raise IOError("Bad 7 bit encoded data")
        b = byte_conversion.unpack(curs.read(1))[0]
        count |= (b & 0x7F) << shift
        shift += 7
        if not (b & 0x80) != 0:
            break
    return curs.read(count).decode('ascii')


class TtpBuffDescriptor:
    def __init__(self, curs):
        self.buff_descriptor_version = struct.unpack("I", curs.read(4))[0]
        self.categoryFlags = struct.unpack("I", curs.read(4))[0]
        self.notificationClass = read_cs_string(curs)
        self.overrides = [read_cs_string(curs) for i in range(struct.unpack("I", curs.read(4))[0])]


class TtpBuffTimer:
    def __init__(self, curs):
        self.buff_timer_version = struct.unpack("I", curs.read(4))[0]
        self.buff_timer_class_id = struct.unpack("B", curs.read(1))[0]


class TtpStatModifier:
    def __init__(self, curs):
        self.stat_modifier_version = struct.unpack("I", curs.read(4))[0]
        self.enum_stat_modifier_class_id = struct.unpack("B", curs.read(1))[0]
        self.UID = struct.unpack("I", curs.read(4))[0]
        self.file_id = struct.unpack("H", curs.read(2))[0]
        self.buff_category_flags = struct.unpack("I", curs.read(4))[0]
        self.stack_count = struct.unpack("I", curs.read(4))[0]
        self.buff_timer = TtpBuffTimer(curs)


class TtpStat:
    def __init__(self, curs):
        self.stat_version = struct.unpack("I", curs.read(4))[0]
        self.value = struct.unpack("f", curs.read(4))[0]
        self.max_modifier = struct.unpack("f", curs.read(4))[0]
        self.value_modifier = struct.unpack("f", curs.read(4))[0]
        self.base_max = struct.unpack("f", curs.read(4))[0]
        self.original_max = struct.unpack("f", curs.read(4))[0]
        self.original_value = struct.unpack("f", curs.read(4))[0]
        self.unknown_g = struct.unpack("B", curs.read(1))[0]

        self.intstat_modifier_list_count = struct.unpack("I", curs.read(4))[0]
        self.stat_modifier_list = [TtpStatModifier(curs) for j in range(self.intstat_modifier_list_count)]


class TtpBuff:
    def __init__(self, curs):
        self.buffVersion = struct.unpack("H", curs.read(2))[0]
        self.buffClassId = struct.unpack("B", curs.read(1))[0]

        self.timer = TtpBuffTimer(curs)
        self.descriptor = TtpBuffDescriptor(curs)
        self.isOverriden = struct.unpack("B", curs.read(1))[0]

        self.stat_modifier_list_count = struct.unpack("B", curs.read(1))[0]
        self.statModifierList = [struct.unpack("H", curs.read(2))[0] for i in range(self.stat_modifier_list_count)]

        self.buff_modifier_list_count = struct.unpack("B", curs.read(1))[0]
        self.buffModifierList = [struct.unpack("H", curs.read(2))[0] for i in range(self.buff_modifier_list_count)]

        self.instigatorId = struct.unpack("I", curs.read(4))[0]


        # statModifierList = new
        # List < StatModifier > ();
        # for (int i = 0; i < statModifierListCount; i++) {
        # ushort key = reader.ReadUInt16();
        # StatModifier statModifier = idTable[key];
        # statModifierList.Add(statModifier);
        # }
        #
        # int
        # buffModiferListCount = reader.ReadByte();
        # buffModifierList = new
        # List < BuffModifier > ();
        # for (int j = 0; j < buffModiferListCount; j++) {
        # BuffModifier buffModifier = BuffModifier.Read(reader);
        # buffModifier.buff = this;
        # buffModifierList.Add(buffModifier);
        # }
        #
        # instigatorId = new
        # Value < int > (reader.ReadInt32());
class TtpReader:
    def __init__(self):
        """
            Read .ttp player point of interest.
            This source code is derived from
            https://github.com/Karlovsky120/7DaysProfileEditor/blob/Alpha16/7DaysSaveManipulator/source/PlayerData/PlayerDataFile.cs#L180
        """
        pass

    def load(self, file_path):
        with open(file_path, "rb") as curs:
            # Check beginning of file
            header_magic = curs.read(4).decode('ascii')
            if not header_magic.startswith("ttp"):
                print("Skip " + os.path.basename(file_path) + " wrong file header")
                return
            ## Read version
            version = struct.unpack("B", curs.read(1))[0]

            # Has been written for this ttp version
            if version != 35:
                print("Skip " + os.path.basename(file_path) + " not supported file version")
                return False
            # Read entity
            # EntityCreationData
            entity_version = struct.unpack("B", curs.read(1))[0]
            entity_class = struct.unpack("I", curs.read(4))[0]
            id = struct.unpack("f", curs.read(4))[0]
            lifetime = struct.unpack("i", curs.read(4))[0]
            player_pos = [struct.unpack("f", curs.read(4))[0],
                          struct.unpack("f", curs.read(4))[0],
                          struct.unpack("f", curs.read(4))[0]]
            player_rot = [struct.unpack("f", curs.read(4))[0],
                          struct.unpack("f", curs.read(4))[0],
                          struct.unpack("f", curs.read(4))[0]]

            on_ground = struct.unpack("B", curs.read(1))[0]

            body_damage_version = struct.unpack("I", curs.read(4))[0]

            left_upper_leg = struct.unpack("H", curs.read(2))[0]
            right_upper_leg = struct.unpack("H", curs.read(2))[0]
            left_upper_arm = struct.unpack("H", curs.read(2))[0]
            right_upper_arm = struct.unpack("H", curs.read(2))[0]
            chest = struct.unpack("H", curs.read(2))[0]
            head = struct.unpack("H", curs.read(2))[0]
            dismembered_left_upper_arm = struct.unpack("B", curs.read(1))[0]
            dismembered_right_upper_arm = struct.unpack("B", curs.read(1))[0]
            dismembered_head = struct.unpack("B", curs.read(1))[0]
            dismembered_right_upper_leg = struct.unpack("B", curs.read(1))[0]
            crippled_right_leg = struct.unpack("B", curs.read(1))[0]

            left_lower_leg = struct.unpack("H", curs.read(2))[0]
            right_lower_leg = struct.unpack("H", curs.read(2))[0]
            left_lower_arm = struct.unpack("H", curs.read(2))[0]
            right_lower_arm = struct.unpack("H", curs.read(2))[0]
            dismembered_left_lower_arm = struct.unpack("B", curs.read(1))[0]
            dismembered_right_lower_arm = struct.unpack("B", curs.read(1))[0]
            dismembered_left_lower_leg = struct.unpack("B", curs.read(1))[0]
            dismembered_right_lower_leg = struct.unpack("B", curs.read(1))[0]

            dismembered_left_upper_leg = struct.unpack("B", curs.read(1))[0]
            crippled_left_leg = struct.unpack("B", curs.read(1))[0]

            has_stat = struct.unpack("B", curs.read(1))[0]

            if has_stat:
                # EntityStats
                stats_version = struct.unpack("I", curs.read(4))[0]
                buffCategoryFlags = struct.unpack("I", curs.read(4))[0]
                immunities = [struct.unpack("I", curs.read(4))[0] for i in range(struct.unpack("I", curs.read(4))[0])]
                health = TtpStat(curs)
                stamina = TtpStat(curs)
                sickness = TtpStat(curs)
                gassiness = TtpStat(curs)
                speed_modifier = TtpStat(curs)
                wellness = TtpStat(curs)
                core_temp = TtpStat(curs)
                food = TtpStat(curs)
                water = TtpStat(curs)
                waterLevel = struct.unpack("f", curs.read(4))[0]
                # Buff
                buffs = [TtpBuff(curs) for i in range(struct.unpack("I", curs.read(4))[0])]

def create_tiles(player_map_path, tile_output_path, tile_level, store_history):
    """
     Call base tile and intermediate zoom tiles
    """
    if not os.path.exists(tile_output_path):
        os.mkdir(tile_output_path)
    create_base_tiles(player_map_path, tile_output_path, tile_level, store_history)
    create_low_zoom_tiles(tile_output_path, tile_level)


def create_base_tiles(player_map_path, tile_output_path, tile_level, store_history):
    """
    Read all .map files and create a leaflet tile folder
    @param player_map_path array of folder name where are stored map
    @param tile_level number of tiles to extract around position 0,0 of map. It is in the form of 4^n tiles.It will
    extract a grid of 2**n tiles on each side. n=8 will give you an extraction of -128 +128 in X and Y tiles index.
    """
    reader = MapReader(tile_output_path, store_history)
    # Read and merge all tiles in .map files
    lastprint = 0
    for i, map_file in enumerate(player_map_path):
        if time.time() - lastprint > 1:
            print("Read map file ", os.path.basename(map_file), i + 1, "/", len(player_map_path))
            lastprint = time.time()
        try:
            reader.import_file(map_file, False)
        except struct.error as e:
            print("Skip " + os.path.basename(map_file) + " may be already used by another process", e)
        except OSError as e:
            print("Skip " + os.path.basename(map_file) + " may be already used by another process", e)

    # make zoom folder
    z_path = os.path.join(tile_output_path, str(tile_level))
    if not os.path.exists(z_path):
        os.mkdir(z_path)
    # compute min-max X Y
    big_tile_range = 2**tile_level
    tile_range = big_tile_range*16
    # iterate on x
    minmax_tile = [(tile_range, tile_range),(-tile_range, -tile_range)]
    used_tiles = 0
    for x in range(2**tile_level):
        if time.time() - lastprint > 1:
            print("Write tile X:", x + 1, " of ", 2 ** tile_level)
            lastprint = time.time()
        x_dir_make = False
        x_path = os.path.join(z_path, str(x - big_tile_range // 2))
        for y in range(2**tile_level):
            # Fetch 256 tiles
            big_tile = None
            # Combine two for loop into one
            for tx, ty in itertools.product(range(16), range(16)):
                world_txy = (x * 16 + tx - tile_range // 2, y * 16 + ty - tile_range // 2)
                tile_data = reader.fetch_tile(index_from_xy(world_txy[0], world_txy[1]))
                if not tile_data is None:
                    used_tiles += 1
                    minmax_tile = [(min(minmax_tile[0][0], world_txy[0]), min(minmax_tile[0][1], world_txy[1])),
                                   (max(minmax_tile[1][0], world_txy[0]), max(minmax_tile[1][1], world_txy[1]))]
                    # Add this tile to big tile
                    # Create empty big tile if not exists
                    if big_tile is None:
                        big_tile = Image.new("RGBA", (256, 256))
                    # convert image string into pil image
                    try:
                        tile_im = Image.frombuffer('RGB', (16, 16), tile_data, 'raw', 'BGR;15', 0, 1)
                        # Push this tile into the big one
                        big_tile.paste(tile_im, (tx * 16, ty * 16))
                    except ValueError:
                        print("The following file is corrupted, skip it:\n" +
                              reader.tiles_file_path.get(index_from_xy(world_txy[0], world_txy[1])))
            # All 16pix tiles of this big tile has been copied into big tile
            # Time to save big tile
            if not big_tile is None:
                # Create Dirs if not exists
                if not x_dir_make:
                    if not os.path.exists(x_path):
                        os.mkdir(x_path)
                        x_dir_make = True
                png_path = os.path.join(x_path, str((big_tile_range - y) - big_tile_range // 2)+".png")
                big_tile = ImageOps.flip(big_tile)
                big_tile.save(png_path, "png")
    print("Min max tiles minx:", minmax_tile[0][0], " maxx:", minmax_tile[1][0],
          "miny:", minmax_tile[0][1], " maxy: ", minmax_tile[1][1])
    print("Tiles used / total read", used_tiles, " / ", reader.new_tiles)


def create_low_zoom_tiles(tile_output_path, tile_level_native):
    """
        Merge 4 tiles of 256x256 into a big 512x512 tile then resize to 256x256
    """
    lastprint = 0
    for tile_level in range(tile_level_native, 0, -1):
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
            if time.time() - lastprint > 1:
                print("Zoom level ", tile_level - 1, ", ", len(tiles_to_process), " tiles left")
                lastprint = time.time()
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
            lower_zoom_image = Image.new("RGBA", (512, 512))
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
            x_lower_path = os.path.join(z_lower_path, str(((orig_tile[0] + (2 ** tile_level) // 2) // 2)
                                                          - (2 ** (tile_level - 1)) // 2))
            if not os.path.exists(x_lower_path):
                os.mkdir(x_lower_path)
            lower_zoom_image.save(os.path.join(x_lower_path, str(((orig_tile[1] + (2 ** tile_level) // 2) // 2)
                                                                 - (2 ** (tile_level - 1)) // 2) + ".png"))


def read_folder(path):
    map_files = [os.path.join(path, file_name) for file_name in os.listdir(path) if file_name.endswith(".map")]
    map_files.sort(key=lambda file_path: -os.stat(file_path).st_mtime)
    return map_files


def usage():
    print("This program extract and merge map tiles of all players.Then write it in a folder with verious zoom"
          " levels. In order to hide player bases, this program keep only the oldest version of each tile by default.")
    print("Usage:")
    print(" -g \"C:\\Users..\":\t The folder that contain .map files")
    print(" -t \"tiles\":\t\t The folder that will contain tiles (Optional)")
    print(" -z 8:\t\t\t\t Zoom level 4-n. Number of tiles to extract around position 0,0 of map."
          " It is in the form of 4^n tiles.It will extract a grid of 2^n*16 tiles on each side.(Optional)")
    print(
        "-n :\t\t\t\t Keep track of updates and write the last version of tiles. This will show players bases on "
        "map.(Optional)")


def main():
    game_player_path = None
    tile_path = "tiles"
    tile_zoom = 8
    store_history = False
    # parse command line options
    try:
        for opt, value in getopt.getopt(sys.argv[1:], "g:t:z:n")[0]:
            if opt == "-g":
                game_player_path = value
            elif opt == "-t":
                tile_path = value
            elif opt == "-z":
                tile_zoom = int(value)
            elif opt == "-n":
                store_history = True
                print("Store all version of tiles, may take huge disk space")
    except getopt.error as msg:
        usage()
        exit(-1)
    if game_player_path is None:
        # Show gui to select tile folder
        try:
            import tkFileDialog
            from Tkinter import Tk
            root = Tk()
            root.withdraw()
            opts = {"initialdir": os.path.join(os.getenv("appdata"), "7DaysToDie", "Saves"),
                    "title": "Choose player path that contain .map files"}
            game_player_path = tkFileDialog.askdirectory(**opts)
        except ImportError:
            # Headless environment
            usage()
            exit(-1)
    if len(game_player_path) == 0:
        print("You must define the .map game path")
        exit(-1)
    map_files = read_folder(game_player_path)
    if len(map_files) == 0:
        print("No .map files found in ", game_player_path)
        exit(-1)
    create_tiles(map_files, tile_path, tile_zoom, store_history)

#if __name__ == "__main__":
#    main()

reader = TtpReader()

reader.load(r"C:\Users\cumu\AppData\Roaming\7DaysToDie\Saves\Random Gen\testalpha\Player\76561197968197169.ttp")
