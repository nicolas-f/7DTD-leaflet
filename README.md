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
 
Edit map_reader.py and update the path of the .map folder.

Run map_reader.py

Open index.html in your brower.

Additonnal content
==============

You can also show where your players gone by editing an updating the "players/tracks.csv" file.

Currently it use the lat/long coordinates, you have to translate coordinates.

The content of the file is only showed if you publish the website through a web server.
You can run simple_server.py to give access on http://localhost:8000 .

Remember that python files are under GPLv3 license and then you need to redistribute your modifications.
