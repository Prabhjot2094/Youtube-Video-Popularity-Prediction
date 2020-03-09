import os
import time
import subprocess
from pytube import YouTube

def get_file_name(path):
    #Get file name and remove extension
    filename = path.split('/')[-1]
    return filename.split('.')[0] 

def get_file_directory(path):
    #get the grandparent directory. 
    return '/'.join(path.split('/')[:-2])

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
        args = ["/Users/prabhjotsingh/OpenFace/build/bin/FaceLandmarkVidMulti", "-f", video_location, "-out_dir", output_path]
        
        proc = subprocess.run(args)
        #features = read_features(video_location)
        return proc.returncode

class ProcessVideos():
    '''
    Combined set of all videos that have to be processed
    '''
    def __init__(self, ids):
        
        self.videos = list()
        for video_id in ids:
            video_processed_status = Video(video_id)
            self.videos.append(video_processed_status)

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
        self.features_extracted_status = Openface().extract_features(self.video_location)
        print(f"Video feature extraction returned with status code {self.features_extracted_status}")
    
    def get_yt_video_data(self, video_id, location=None):
        url = "http://youtube.com/watch?v={}"
        yt = YouTube(url.format(video_id))
        
        audio_codec="opus"
        video_stream = audio_stream = None
        
        #Filter available streams to get the compatible ones. Adaptive : Audio, Video downloaded separately and merged after download; progressive : Audio, Video downloaded in same file
        adaptive_video_streams = yt.streams.filter(adaptive=True, type="video")
        adaptive_audio_streams = yt.streams.filter(type="audio", audio_codec=audio_codec)
        
        #Download the Audio and Video into a temporary file. Assuming there is only a single file at a given time for OpenFace processing
        video_location = adaptive_video_streams.asc()[0].download(output_path="temporary_downloads/raw_video", filename=f"video_{video_id}") #asc puts the highest quality video at the top 
        audio_location = adaptive_audio_streams.asc()[-1].download(output_path="temporary_downloads/raw_audio", filename=f"audio_{video_id}")#asc puts the highest bitrate at the bottom
        
        return video_location, audio_location
        #max_abr = 0
        #for stream in yt.streams.filter(type="audio", audio_codec=audio_codec):
        #    if bitrate_helper(stream.abr) > max_abr:
        #        audio_stream = stream
        

def main():
    #Read raw data
    #Fetch details of all videos
    video_ids = ['wV-NcNwXqcA']
    start = time.time()
    print(ProcessVideos(video_ids))
    print("Processing time = ", time.time()-start)


main()
