import subprocess
import os
import glob

from ..tmlogging import info, error
from ..os_util import *
from ..conf import FRAME_FILENAME_PREFIX, FRAME_EXTENSION


IMAGEMAGICK = "convert"
FFMPEG = "ffmpeg"
DEFAULT_ANIMATION_NAME = "animation.gif"
DEFAULT_FRAME_PATTERN = "{}*.{}".format(FRAME_FILENAME_PREFIX, FRAME_EXTENSION)

file_dir = os.path.dirname(os.path.realpath(__file__))

def can_animate():
    return is_in_path(IMAGEMAGICK)

def can_export_video():
    return is_in_path(FFMPEG)


def is_in_path(exec_name):
    if get_os() == WINDOWS:
        return False
    try:
        ret = subprocess.check_call([exec_name, "-version"])
        return ret == 0
    except:
        return False

def clear_frames(out_folder, frame_pattern=DEFAULT_FRAME_PATTERN):
    all_frames = glob.glob(os.path.join(out_folder, frame_pattern))
    map(os.remove, all_frames)

def make_animation(out_folder, delay_millis, frame_pattern=DEFAULT_FRAME_PATTERN):
    if not can_animate():
        error("Imagemagick is not in path")
        raise Exception("Imagemagick is not in path. Please install ImageMagick!")
    out_file = os.path.join(out_folder, DEFAULT_ANIMATION_NAME)
    all_frames = glob.glob(os.path.join(out_folder, frame_pattern))
    if len(all_frames)==0:
        msg = "Couldn't find any frames with pattern {} in folder {} to animate".format(frame_pattern, out_folder)
        error(msg)
        raise Exception(msg)
    all_frames.sort()
    fps = 1000 / delay_millis
    args = [IMAGEMAGICK, "-delay", "1x" + str(fps)] + all_frames + [out_file]
    ret = subprocess.check_call(args)
    if (ret != 0):
        msg = "Something went wrong creating the animated gif from frames"
        error(msg)
        raise Exception(msg)
    info("Exported {} frames to gif {} (call :{})".format(len(all_frames), out_file, args))
    return out_file


# ffmpeg -f image2 -r 1 -i frame%02d.png -vcodec libx264 -vf fps=25 -pix_fmt yuv420p out.mp4
#http://unix.stackexchange.com/questions/68770/converting-png-frames-to-video-at-1-fps

def make_video(out_folder, digits):
    outfile = os.path.join(out_folder,"out.mp4")
    # something like frame%03d.png as expected by ffmpeg
    frame_pattern = os.path.join(out_folder,"{}%0{}d.{}".format(FRAME_FILENAME_PREFIX, digits ,FRAME_EXTENSION))
    # TODO: Make this configurable (when understanding how it works)
    video_script = os.path.join(file_dir,"video.sh")
    subprocess.check_call(["sh", video_script, frame_pattern, outfile])
    info("Exported video to {}".format(outfile))
    return outfile

