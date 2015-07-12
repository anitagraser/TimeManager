import subprocess
import os
import glob
from collections import namedtuple
from ..logging import info, error
from ..os_util import *

IMAGEMAGICK="convert"
FFMPEG="ffmpeg"
DEFAULT_ANIMATION_NAME = "animation.gif"
DEFAULT_FRAME_PATTERN = "*.png"

def can_animate():
    return is_in_path(IMAGEMAGICK)

def is_in_path(exec_name):
    if get_os() == WINDOWS:
        return False
    try:
        ret = subprocess.check_call([exec_name,"-h"])
        return ret == 0
    except:
        return False

def make_animation(out_folder, delay_millis, frame_pattern=DEFAULT_FRAME_PATTERN):
    if not can_animate():
        error("Imagemagick is not in path")
        raise Exception("Imagemagick is not in path. Please install ImageMagick!")
    out_file = os.path.join(out_folder, DEFAULT_ANIMATION_NAME)
    all_frames = glob.glob(os.path.join(out_folder, frame_pattern))
    fps = 1000/delay_millis
    args = [IMAGEMAGICK,"-delay","1x"+str(fps)] + all_frames + [out_file]
    ret =  subprocess.check_call(args)
    if (ret != 0):
        msg = "Something went wrong creating the animated gif from frames"
        error(msg)
        raise Exception(msg)
    info("Exported {} frames to gif {} (call :{})".format(len(all_frames),out_file, args))

#ffmpeg -f image2 -r 1 -i frame%02d.png -vcodec libx264 -vf fps=25 -pix_fmt yuv420p out.mp4
#http://unix.stackexchange.com/questions/68770/converting-png-frames-to-video-at-1-fps

def make_video(out_folder, settings):
    # TODO in the future
    pass
    frames_glob = os.path.join(outFolder,"")
    subprocess.check_call(["ffmpeg","-f","image2","-i",frames_glob,out_file])

