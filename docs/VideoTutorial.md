# Exporting Video

 A good option is mencoder. This is how it's used to create an .avi from all images within a folder:

``mencoder "mf://*.png" -mf fps=10 -o output.avi -ovc lavc -lavcopts vcodec=mpeg4``

On newer Macs, mencoder may not work.  One alternative is a powerful command-line program called ffmpeg (https://www.ffmpeg.org/). There may also be more user-friendly GUI options (such as QuickTime Pro). 

A generic problem in creating a video is that the frame rate must be chosen, which affects how you choose the "time frame size" in TimeManager.  Most videos play at approximately 30 frames per second.  Slower rates are acceptable, but will look choppier.  Here is an example calculation for animating a set of animal tracks:  
  1. Number of track-hours in the data set: 10,080  
  2. Desired video length: 3 minutes (180 seconds)  
  3. If the length of the time frame size was set to 1 hour in TimeManager, the video would have 10,080 frames.  Given the desired video length of 180 seconds that would come out to 10,080/180 = 56 frames/second, which would be too fast.  Instead, creating 1 frame per 2 track-hours results in a pretty normal 35 fps frame rate. Of course, the video length could also be altered.

Example ffmpeg command to create a video from individual .png frames:
``ffmpeg -f image2 -r 35 -i frame%04d.png -vcodec libx264 -vf fps=35 -pix_fmt yuv420p out.mp4``

What the ffmpeg flags mean:
* -f force the input or output filetype
* -r (rate): frame rate (Hz)
* -i (input): input file.  frame%04d.png means the name is formatted with 4 digits, as in "frame0000.png".  Check the filename format created by TimeManager; if you only had hundreds of frames, the filename numbering format might be "frame%03d".  The files have to be organized with padded zeros; otherwise you can use a "blob" naming option 
* -vcodec video codec.  libx264: x264 is a free software library and application for encoding video streams into the H.264/MPEG-4 AVC compression format.
* -vf fps=35 video filter(vf); frames per second (fps) = 35.  A filter is a processing step in ffmpeg parlance.
* -pix_fmt yuv420p (pixel format): YUV is a color space typically used as part of a color image pipeline, and 420p refers to the image resolution
* out.mp4 name of the output file

Other potentially useful ffmpeg flags:  
* -s (size): frame size.  WxH (width x height) is the default (keep output same as input)
* -fs (file size): limit the file size (expressed in bytes)

