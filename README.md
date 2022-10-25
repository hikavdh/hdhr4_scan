# hdhr4_scan
Shell for the hdhomerun_config program to scan for channels, to compare a fresh scan for changes since the last stored scan or to play a channel with mplayer.

Configuration is stored in ~/.hdhr/hdhr_scan.cfg

run hdhr4_scan.py --help for all options

See at https://www.silicondust.com/support/linux/ on how to download and compile the hdhomerun_config program. If you want to install on a non-graphical system and do not want the hdhomerun_config_gui program, only compile `libhdhomerun` as described in the README file. Next copy `libhdhomerun` to /usr/lib and `hdhomerun_config` to /opt/bin.

## 2022-10-25
Fixed a small python3 bug.
Added the possibility to play audio-only on a non-graphical system through ffmpeg and the mp3 player "mpg123". For instance to play radio stations on a Rpi without having to install X and gtk.
