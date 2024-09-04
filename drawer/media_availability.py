
# %%
# Import necessary modules

import os
import glob
import subprocess
import requests
import time
import platform


# hard-coded location of non-portable code (outside of this repository)
if platform.system() == "Windows":
    #ci_url_sh_path = '../localcode/secret/ci_url/ci_url.sh'
    ci_url_sh_path = '/mnt/c/Users/owen_king/localcode/secret/ci_url/ci_url.sh'
else:
    ci_url_sh_path = '/home/owen/GBH/localcode/secret/ci_url/ci_url.sh'

# confirm ci_url is accessible via bash (which is what will call it).
command = "[ -f " + ci_url_sh_path + " ] && echo exists || echo missing "
ci_url_exists = subprocess.run([ 'bash', '-c', command ], capture_output=True, text=True)
result = ci_url_exists.stdout.strip()
if result != "exists":
    raise FileNotFoundError("Path to ci_url does not exist: " + ci_url_sh_path)

temp_suffix = ".PARTIAL"

# %%
def extract_filename_ci_url(url:str, ci_id:str) -> str:

    #print("URL: <", url, ">") # DIAG

    start_index = url.find("cpb-aacip")
    if start_index == -1:
        print("Warning: SonyCi URL does not include 'cpb-aacip'.")
        
        # can't find filename by looking for the GUID;
        # rely on assumptions about the strucutre of the URL
        start_index = url.find(ci_id) + 33
        if start_index == -1:
            print("Failure: Media filename not found in SonyCi URL.")
            print("URL: <" + url + ">") 
            return None;

    end_index = url.find("?", start_index) 
    if end_index == -1:
        end_index = url.find("&", start_index) 
    if end_index == -1:
        print("Failure: Could not find the end of the filename in the URL.")
        print("URL: <" + url + ">") 
        return None;

    filename = url[start_index:end_index]
    return(filename)

# %%
def remove_media(file_path:str) -> bool:

    # Remove the file
    try:
        os.remove(file_path)
        #print(f"{file_path} has been deleted.")
    except FileNotFoundError:
        print(f"The file {file_path} does not exist.")
    except PermissionError:
        print(f"Permission denied: unable to delete {file_path}.")
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")
    else:
        return True


# %%
def check_avail(guid:str, media_dir_path:str) -> str:
    """
    Takes a guid, checks whether a media file matches that guid.  
    Returns the filename for the first such file there, if such a file is found, 
    else returns None
    """
    global temp_suffix
    available = glob.glob("*", root_dir=media_dir_path)
    matches = [fn for fn in available if (guid[10:] in fn) and (temp_suffix not in fn)]

    if len(matches) > 1:
        print("Warning: More than one media file matches guid. " +
              guid + ". Using the first one")

    if len(matches) > 0:
        return matches[0];
    else:
        return None;

# %%

def make_avail(guid:str, ci_id:str, media_dir_path:str, overwrite:bool = True) -> str:
    """
    Retrieves the media file for guid to the directory
    Returns the filename of the media file if found
    Else returns None
    """
    global ci_url_sh_path

    print("About to get Ci URL for Ci ID:", ci_id) # DIAG

    retries = 2
    for attempt in range(retries+1):
        ci_url_result = subprocess.run([ 'bash', 
                                        ci_url_sh_path, 
                                        ci_id ], 
                                       capture_output=True, text=True)

        # Remove whitespace and quotation marks (which I've notice in output)
        ci_url = ci_url_result.stdout.strip().replace('"', '')
        if ci_url == "null":
            if attempt == retries:
                print("Failure: `ci_url.sh` returned no URL for " + ci_id)
                return None
            else:
                print("Warning: `ci_url.sh` returned no URL for " + ci_id)
                delay = 5
                print("Pausing for", delay, "seconds...")
                time.sleep(delay)
                print("Trying again.")
        else:
            break

    # Received the URL
    # Do a little checking; then go get the file
    filename = extract_filename_ci_url(ci_url, ci_id)

    if filename is None:
        print("Failure: No valid filename returned in SonyCi URL")
        return None
    elif filename[-4:].lower() not in [".mp3", ".mp4"]:
        # We assume all valid media files have MP3 or MP4 extensions
        print("Failure: Media filename", filename, "does not have valid extension.")
        return None

    # sanity check comparison between guid and filename
    if filename[10:18] != guid[10:18]:
        print("Warning: `ci_url.sh` for guid " + guid + " returned " + filename)

    filepath = media_dir_path + "/" + filename


    # Going to download and save the file from the web using the Ci URL
    print("Will save", filename, "to:")
    print(filepath)

    #print(ci_url)  # DIAG
    #curl_result = subprocess.run(['curl', ci_url, '--output', filepath])

    # # Write the whole file once the entire thing has been received
    # # (not using this method anymore; replacement below)
    # response = requests.get(ci_url)
    # if response.status_code == 200:
    #     with open(filepath, 'wb') as file:
    #         file.write(response.content)
    # else:
    #     print("Download attempt failed.  Status code: ", response.status_code)
    
    # Since files can be large (up to 700MB) better to write it to disk as we go.
    bytes_limit = 1000000000 # ~1000MB  # Things are weird if we're receiving more than that

    success = False
    with requests.get(ci_url, stream=True) as response:
        if response.status_code == 200:
            global temp_suffix
            tempfilepath = filepath + temp_suffix
            with open(tempfilepath, 'wb') as file:
                # Iterate over the response in chunks
                bytes_saved = 0
                try:
                    for chunk in response.iter_content(chunk_size=8388608): 
                        if chunk:  # filter out zero bye keep-alive chunks
                            file.write(chunk)
                            bytes_saved += len(chunk)
                        if bytes_saved >= bytes_limit:
                            print("Warning: Received more than limit of", bytes_limit, "bytes.")
                            print("Stopping the download.  File may be truncated.")
                            break
                    print("Downloading finished.", bytes_saved, "bytes saved.")
                    success = True
                except Exception as e:
                    print("Download unsuccessful:", e)
            if success:
                if os.path.exists(filepath):
                    print("Warning:  File exists at", filepath)
                    print("Leaving existing file in place.")
                else:
                    os.rename(tempfilepath, filepath)
        else:
            print("Download attempt failed.  Status code: ", response.status_code)

    if success:
        return filename
    else:
        return None

