
"""
Provides helper functions for using data extracted from MMIF files
"""

# %% 
# Import statements
import math
import sys
import os
import av


# %% 
# Define time prettification helper functions
def tconv( msec: int, frac: bool = True ) -> str:
    """ Converts time in integer milliseconds to a nice string
    """
    imin = math.floor(msec / 60000)
    isec = math.floor( (msec - imin * 60000) / 1000)
    imsec = math.floor( (msec - (imin * 60000 + isec * 1000)) )

    tstr = str(imin).zfill(2) + ":" + str(isec).zfill(2) 
    if frac:
        tstr += "." + str(imsec).zfill(3)
   
    return( tstr )


# %%
# Define still extraction function
def extract_stills(video_path:str, 
            time_points,
            fname:str = "mediaitem",
            dest_path:str = "",
            filetype_ext:str="jpg",
            verbose:bool=True):
    """Performs extraction of stills from the video 
    `video_path` is the path to the video file to be extracted
    `time_points` is a list of integers representign the frames to be extracted in ms
    `fname` is a string used in the naming of the output files (and output dir, if not specified)
    `dest_path` is the path to an existing directory to put the stills in

    Returns an ordered pair of the filename and the full path to the last image extracted.

    Output filename format:
    F_L_T_A.ext
    F: the base filename for the video extracted
    L: the length of the video (ms)
    T: the specified target time (ms) for the frame
    S: the actual time (ms) for the frame

    """

    if dest_path == "":
        basename = "stills_" + fname 
        stills_dir = "./" + basename + "/"
        if not os.path.exists(stills_dir):
            print("Creating directory:", stills_dir)
            os.mkdir(stills_dir)
        else:
            print("Warning: Stills directory exists.  Existing stills may be overwritten.")
    else:
        stills_dir = dest_path + "/"
        if not os.path.exists(stills_dir):
            raise Exception("Destination directory is undefined.")

    # Print explanatory messages.
    if verbose: print("Using video from", video_path)

    # Initialize counters for iteration
    image_list = []
    stills_count = 0
    fcount = 0

    # remove duplicates in time_points
    num_call_points = len(time_points)
    time_points = list(set(time_points))
    num_act_points = len(time_points)
    if (num_call_points > num_act_points):
        print("Warning: Some specified time points were duplicates; they will be ignored.")

    # since we're iterating through the video in order, 
    # we need to get the stills in order of appearance
    # We also want to remove duplicates
    time_points.sort()
    # next_target_time = time_points[stills_count]

    # find the first video stream
    container = av.open(video_path)
    video_stream = next((s for s in container.streams if s.type == 'video'), None)
    if video_stream is None:
        raise Exception("No video stream found in {}".format(vfilename) ) 

    # get technical stats on the video stream; assumes FPS is constant
    fps = video_stream.average_rate.numerator / video_stream.average_rate.denominator
    
    # calculate duration in ms
    length = int((video_stream.frames / fps) * 1000)

    if time_points[-1] > length :
        print("Warning: Some specified time points are beyond video length and will not be extracted.")


    # going to loop through every frame in the video stream, starting at the beginning 
    target_time = time_points[stills_count]
    for frame in container.decode(video_stream):

        # prevent this from running longer than necessary
        if ( stills_count >= len(time_points) ):
            break

        # calculate the time of the frame
        ftime = int(frame.time * 1000)   

        # Grab the first still after the target time index 
        """
        if ( ftime >= target_time ):
            ifilename =  f'{fname}_{length:08}_{target_time:08}_{ftime:08}' + "." + filetype_ext
            ipathname = stills_dir + ifilename
            frame.to_image().save(ipathname)
            image_list.append(ifilename)
            stills_count += 1
        """
        # Grab the still for each target mentioned (even if it's the same still)
        while ( ftime >= target_time ):
            ifilename =  f'{fname}_{length:08}_{target_time:08}_{ftime:08}' + "." + filetype_ext
            ipathname = stills_dir + ifilename
            frame.to_image().save(ipathname)
            image_list.append(ifilename)
            stills_count += 1
            if ( stills_count >= len(time_points) ):
                break
            else:
                target_time = time_points[stills_count]

        fcount += 1
    
    if verbose: print("Extracted", stills_count, "stills out of", fcount, "video frames checked.") 

    container.close()

    # return the path to the last image extracted
    if ipathname:
        return (ifilename, ipathname)
    else:
        return ("", "")


