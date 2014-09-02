7DTD-leaflet
============

Merge 7DTD discovered map in html for www.ketchu-free-party.fr

The python script map_reader.py will extract dans merge all .map files of a random world.
The result is then saved into png files.

A javascript code (Leaflet) merge all this png files while browsing the big map.

How to use
=============

Install:

 * Python 2.7 https://www.python.org/downloads/
 * Pillow https://pillow.readthedocs.org/en/latest/
 
Run map_reader.py a gui will ask you the path of the .map folder.

A sub directory named tiles will be created.

Open index.html in your brower.

You can also use it in command line.

```bash
python map_reader.py -g "C:\Users\CUMU\Documents\7 Days To Die\Saves\Random Gen\ver91\Player"
```

Usage
=============

```
-g "C:\\Users..\" The folder that contain .map files
-t "tiles" The folder that will contain tiles (Optional)
-z 8 Zoom level 4-n. Number of tiles to extract around position 0,0 of map. It is in the form of 4^n tiles.It will extract a grid of 2^n*16 tiles on each side.(Optional)
```

Additonnal content
==============

You can also show where your players gone by editing an updating the "players/tracks.csv" file.

Lat long is the ingame coordinates.

The content of the file is only showed if you publish the website through a web server.
You can run simple_server.py to give access on http://localhost:8000 .

Remember that python files are under GPLv3 license and then you need to redistribute your modifications.
