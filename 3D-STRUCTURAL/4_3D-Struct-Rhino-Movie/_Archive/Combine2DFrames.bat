@echo off
cd /d C:\Users\am1\PycharmProjects\PostProcessor-SAFIR\timestepdata

ffmpeg -framerate 24 -i Persp_%%05d.bmp -r 24 -vf "pad=iw:ceil(ih/2)*2" -c:v libx264 -pix_fmt yuv420p Slab.mp4
pause