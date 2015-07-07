import subprocess
import os
import glob
from collections import namedtuple
from ..logging import info, error

IMAGEMAGICK="convert"
FFMPEG="ffmpeg"
DEFAULT_ANIMATION_NAME = "animation.gif"
DEFAULT_FRAME_PATTERN = "*.png"

def is_in_path(exec_name):
    try:
        ret = subprocess.check_call([exec_name,"-h"])
        return ret == 0
    except:
        return False

def make_animation(out_folder, delay_millis, frame_pattern=DEFAULT_FRAME_PATTERN):
    if not is_in_path(IMAGEMAGICK):
        error("Imagemagick is not in path")
        # FIXME exception is not thrown *within* qgis here
        raise Exception("Imagemagick is not in path")
    # Would this work in windozer?
    # or should i actually make the animation myself?
    out_file = os.path.join(out_folder, DEFAULT_ANIMATION_NAME)
    all_frames = glob.glob(os.path.join(out_folder, frame_pattern))
    delay_hundrendths = delay_millis/10
    ret =  subprocess.check_call([IMAGEMAGICK,"-delay",str(delay_hundrendths)] + all_frames + [out_file])
    if (ret != 0):
        msg = "Something went wrong creating the animated gif from frames"
        error(msg)
        raise Exception(msg)
    info("Exported {} frames to gif {}".format(len(all_frames),out_file))

#ffmpeg -f image2 -r 1 -i frame%02d.png -vcodec libx264 -vf fps=25 -pix_fmt yuv420p out.mp4
#http://unix.stackexchange.com/questions/68770/converting-png-frames-to-video-at-1-fps

def make_video(out_folder, settings):
    # TODO in the future
    pass
    frames_glob = os.path.join(outFolder,"")
    subprocess.check_call(["ffmpeg","-f","image2","-i",frames_glob,out_file])

