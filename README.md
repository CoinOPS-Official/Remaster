# Remaster
Remaster will help you keep emulators and frontend media at an similar loudness level.

Without remaster, frontend media sound levels will be all over the place (because media sources widely vary,  can be youtube, home recorded gameplay, etc..), and emulated game loudness will also be all over the place (because 80's games did not treat sound like modern game consoles).

### With Remaster you can:
* Batch normalize all of your frontend's media to a specified loudness level (default: -24dB)
* Generate .ini files from recorded gameplay footage that specify how much to boost game volume

### Requirements
* Python 3.8 and above

### Installation
[Grab the latest wheel](https://github.com/CoinOPS-Official/Remaster/releases)

Install the wheel:
```
python -m pip install remaster-0.1.0-py3-none-any.whl
```

### Usage
Batch normalize all files under a directory recursively.
```
from remaster import batch_remaster
batch_remaster(r'C:\CoinOPS\collections\Arcades\medium_artwork\video', target_db=-24)
```

Create Mame .ini files from reference media (sound or movie) under a specified folder
```
from remaster import batch_mame_ini
batch_mame_ini(r'C:\__reference__', target_db=-24)
```

Get the loudness difference between a reference media and the target loudness
```
from remaster import Media
media = Media(r'C:\__reference__\super_mario_galaxy_gameplay.wav', target_db=-24)

# prints a sound adjustment value needed so emulator loudness matches frontend
print(media.difference()) # will return some float value
print(media.difference(rounded=True)) # same but as a rounded integer (for Mame)
```

