# 7DTD-leaflet

Merge 7DTD discovered map in html

The python script map_reader.py will extract dans merge all .map files of a random world.
The result is then saved into png files.

A javascript code (Leaflet) merge all this png files while browsing the big map.

7DTD forum post https://7daystodie.com/forums/showthread.php?14947-Export-discovered-map-to-png

## How to use

### From source

Install:

 * Python 2.7 https://www.python.org/downloads/
 * Pillow https://pillow.readthedocs.org/en/latest/

Run map_reader.py by double clicking on this file. A gui will ask you the path of the .map folder. (for me this is in C:\Users\cumu\AppData\Roaming\7DaysToDie\Saves\Random Gen\testalpha\Player)

### Using prebuilt binary

You will find windows binary in the releases. Place the .exe file into the extracted source file (along index.html file)
https://github.com/nicolas-f/7DTD-leaflet/releases

Then double click on the exe. A gui will ask you the path of the .map folder. (for me this is in C:\Users\cumu\AppData\Roaming\7DaysToDie\Saves\Random Gen\testalpha\Player)

### How to view the result

A sub directory named tiles will be created.

Open index.html in your browser (Firefox or Chrome).

Enjoy !

## Command line

You can also use it in command line.

```bash
python map_reader.py -g "C:\Users\CUMU\Documents\7 Days To Die\Saves\Random Gen\ver91\Player"
```

### Available parameters:

```
-g "C:\\Users..\" The folder that contain .map files
-t "tiles" The folder that will contain tiles (Optional)
-z 8 Zoom level 4-n. Number of tiles to extract around position 0,0 of map. It is in the form of 4^n tiles.It will extract a grid of 2^n*16 tiles on each side.(Optional)
-n Keep track of updates and write the last version of tiles. This will show players bases on map.
```

## Additonnal content

You can run simple_server.py with python to give access on http://localhost:8000 .

Remember that python files are under GPLv3 license and then you need to redistribute your modifications.
