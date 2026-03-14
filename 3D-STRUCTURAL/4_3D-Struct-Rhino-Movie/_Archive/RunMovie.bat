@echo off
cd /d C:\Users\am1\PycharmProjects\PostProcessor-SAFIR\timestepdata

ffmpeg -framerate 24 -i Frame_%%05d.bmp -r 24 -vf "pad=iw:ceil(ih/2)*2" -c:v libx264 -pix_fmt yuv420p RufusZone1.mp4
pause