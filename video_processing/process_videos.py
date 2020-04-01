import json
import os
import time
import subprocess
from pytube import YouTube
import config
import csv
import cv2
import shutil
from multiprocessing import Pool, Manager, cpu_count

REQUIRED_FPS = 3
SKIP_FRAMES = 60//REQUIRED_FPS+1

def get_file_name(path):
    #Get file name and remove extension
    filename = path.split('/')[-1]
    return filename.split('.')[0] 

def get_file_directory(path):
    #get the grandparent directory. 
    return '/'.join(path.split('/')[:-2])

def compress_video(video_location):
    '''
    Extract every nth frame and store in the output dir

    returns the directory of the frames
    '''
    _dir = get_file_directory(video_location)
    file_name = get_file_name(video_location)
    output_dir = _dir+'/'+file_name
    
    os.mkdir(output_dir)
    
    vidObj = cv2.VideoCapture(video_location)
    success = 1
    frame = 1
    i = 31
    success, img = vidObj.read()
    while success:
        while success and i<=SKIP_FRAMES:
            success, img = vidObj.read()
            i += 1
        i = 0
        if success:
            cv2.imwrite(f'{output_dir}/frame_{frame}.jpg', img)
        
        frame+=1
    return output_dir 

class Openface():
    '''
    Extract facial features of a given video
    '''
    @classmethod
    def extract_features(self, video_location):
        '''
        Run openface on given video, read the extracted features, return the the extracted features
        '''
        output_path = get_file_directory(video_location) + '/processed_video/' + get_file_name(video_location)
        args = [config.OPENFACEPATH, "-fdir", video_location, "-out_dir", output_path]
        
        proc = subprocess.run(args)
        #features = read_features(video_location)
        return proc.returncode

class ProcessVideos():
    '''
    Combined set of all videos that have to be processed
    '''
    def __init__(self, ids):
        
        self.video_status= list()
        self.audio_status = list()
        for video_id in ids:
            video = Video(video_id)
            self.video_status.append(video.features_extracted_status)
        
        ########################
        #Process audio below this and update the status


def bitrate_helper(abr):
    '''
    convert string bitrate to integer

    160kbps -> 160
    Assumption : All bitrates are in kbps
    '''
    num = 0

    loc = 0
    while loc<len(abr) and abr[loc].isdigit():
        num = num*10+int(abr[loc])
        loc+=1

    return num

class Video():
    '''
    Represents a single video and features associated with it
    '''
    def __init__(self, video_id):
        self.video_location, self.audio_location = self.get_yt_video_data(video_id)
        if not self.video_location and not self.audio_location:
            self.features_extracted_status = -10
        else:
            self.frames_location = compress_video(self.video_location)
            self.features_extracted_status = Openface().extract_features(self.frames_location)
            print(f"Video feature extraction for {video_id} returned with status code {self.features_extracted_status}")
    
            #Delete the video files
            os.remove(self.video_location)
            os.remove(self.audio_location)
            shutil.rmtree(self.frames_location)


    
    def get_yt_video_data(self, video_id, location=None):
        url = "http://youtube.com/watch?v={}"
        audio_codec="opus"
        video_stream = audio_stream = None
        
        while 1:
            try:
                yt = YouTube(url.format(video_id))
                print(url.format(video_id))
                
                #Filter available streams to get the compatible ones. Adaptive : Audio, Video downloaded separately and merged after download; progressive : Audio, Video downloaded in same file
                adaptive_video_streams = yt.streams.filter(adaptive=True, type="video")
                adaptive_audio_streams = yt.streams.filter(type="audio", audio_codec=audio_codec)
                
                #Download the Audio and Video into a temporary file. Assuming there is only a single file at a given time for OpenFace processing
                #TODO Ensure the asc function works as expected for all videos. The sorting assumption is made based on the output for 4-5 test videos.
                video_location = adaptive_video_streams.asc()[0].download(output_path="temporary_downloads/raw_video", filename=f"video_{video_id}") #asc puts the highest quality video at the top 
                audio_location = adaptive_audio_streams.asc()[-1].download(output_path="temporary_downloads/raw_audio", filename=f"audio_{video_id}")#asc puts the highest bitrate at the bottom
            except Exception as e:
                if '429' in str(e):
                    time.sleep(10)
                    continue
                print(f"unable to process video {video_id}, error {e}")
                return 0, 0
            break
        
        return video_location, audio_location
        #max_abr = 0
        #for stream in yt.streams.filter(type="audio", audio_codec=audio_codec):
        #    if bitrate_helper(stream.abr) > max_abr:
        #        audio_stream = stream
        

def print_error(e):
    print(e)

def process_videos_helper(video_ids):
    video_proc_obj = ProcessVideos(video_ids)
    #Store id for failed videos 
    for status, video_id in zip(video_proc_obj.video_status, video_ids):
        if status!=0:
            errors_list.append([video_id, status, 'video'])
        else:
            processed_list.append(video_id)
            #videos_failed_csv.writerow([video_id, status])
    
    ###############################
    #Audio processing
    
    #Store id for failed audio files
    for status, video_id in zip(video_proc_obj.audio_status, video_ids):
        if status!=0:
            errors_list.append([video_id, status, 'audio'])
        else:
            processed_list.append(video_id)
            #audios_failed_csv.writerow([video_id, status])


def main():
    #Read raw data
    f = open('processed_video_ids.json', 'r')
    processed_list.extend(json.load(f))
    f.close()

    video_ids = list()
    
    f = open('Data/raw_data.csv')
    c = csv.reader(f)
    #Get rid of the header row
    next(c)
    for i, row in enumerate(c):
        if i%100==0: #create sets of 100 ids which'll be distributed to the spawned processes
            video_ids.append(list())
        if row[12] in processed_list:
            continue
        video_ids[-1].append(row[12])
    f.close()
    
    #Fetch details of all videos
    #video_ids = video_ids[:1]+['ewfherher']#, 'wO0a2C6PqtY']
    start = time.time()
    
    #video_ids = [video_ids[3][:2]]
    #video_ids = [video_ids[0][:1], video_ids[0][1:]+[' ##################']]

    NUM_WORKERS = cpu_count()*2
    
    p = Pool(processes=NUM_WORKERS)
    p.map_async(process_videos_helper, video_ids, error_callback=print_error)
    p.close()
    p.join()
    
    print("Processing time = ", time.time()-start)
    print("Saving processed video ids and Terminating program !!!")
    f = open('processed_video_ids.json', 'w')
    json.dump(list(processed_list), f)
    f.close()
    
    errors = open('Errors/processing_errors.csv', 'a')
    errors_csv = csv.writer(errors)
    for row in errors_list:
        errors_csv.writerow(row)
    errors.close()

#Objects shared between processes
errors_list = Manager().list()
processed_list = Manager().list()
main()
