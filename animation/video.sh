set -x
ffmpeg -y -f image2 -r 2 -i $1 -vcodec libx264 -vf "fps=25,scale=-2:720" -pix_fmt yuv420p $2

