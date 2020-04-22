import json
import os
import time
import subprocess
from pytube import YouTube
import config
import csv
import cv2
import shutil
from multiprocessing import Pool, Manager, cpu_count, Process, Queue
#import speech_to_text as stt

REQUIRED_FPS = 3
SKIP_FRAMES = 60//REQUIRED_FPS+1

import time
import azure.cognitiveservices.speech as speechsdk

# Creates an instance of a speech config with specified subscription key and service region.
# Replace with your own subscription key and region identifier from here: https://aka.ms/speech/sdkregion

#speech_key, service_region = "d215959e99c24caeb2ee4e620016782f", "westus"
#speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
#speech_config.request_word_level_timestamps()

# Creates an audio configuration that points to an audio file.
# Replace with your own audio filename.
def speech_to_text(audio_filename, output_filename=None):
    print("Speech To Text conversion")
    if not output_filename:
        output_filename = audio_filename.split('.')[0]+f'_text.json'

    data = list()
    done = False

    audio_input = speechsdk.audio.AudioConfig(filename=audio_filename)
    # Creates a recognizer with the given settings
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

    print("Recognizing first result...")

    def stop_cb(evt):
        """callback that signals to stop continuous recognition upon receiving an event `evt`"""
        print('CLOSING on {}'.format(evt))
        nonlocal done, output_filename
        f = open(output_filename, 'w')
        f.write(json.dumps(data))
        f.close()
        done = True

    # Connect callbacks to the events fired by the speech recognizer
    def store_text(evt):
        nonlocal data, output_filename
        print(f"writing to {output_filename}")
        #f = open(output_filename, 'w')
        #f.write(evt.result.json)
        #f.close()
        data.append(evt.result.json)

    speech_recognizer.recognizing.connect(lambda evt: print('RECOGNIZING: {}'.format(evt.result.json)))
    speech_recognizer.recognized.connect(store_text)#lambda evt: print('RECOGNIZED: {}'.format(evt.result.json)))
    speech_recognizer.session_started.connect(lambda evt: print('SESSION STARTED: {}'.format(evt)))
    speech_recognizer.session_stopped.connect(lambda evt: print('SESSION STOPPED {}'.format(evt)))
    speech_recognizer.canceled.connect(lambda evt: print('CANCELED {}'.format(evt)))
    # stop continuous recognition on either session stopped or canceled events
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    # Start continuous speech recognition
    speech_recognizer.start_continuous_recognition()
    while not done:
        time.sleep(.5)

    return 0

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

def extract_video_features(video_location):
    '''
    Run openface on given video, read the extracted features, return the the extracted features
    '''
    output_path = get_file_directory(video_location) + '/processed_video/' + get_file_name(video_location)
    args = [config.OPENFACEPATH, "-fdir", video_location, "-out_dir", output_path]
    
    proc = subprocess.run(args)
    #features = read_features(video_location)
    return proc.returncode

def extract_audio_features(audio_location):
    output_path = 'processed_video/' + get_file_name(audio_location) + '_txt'
    return speech_to_text(audio_location, output_path)
    
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

def webm_to_wav(inp_filepath, out_filepath):
    args = ['ffmpeg', '-i', inp_filepath, '-ac', '1', '-f', 'wav', out_filepath]
    proc = subprocess.run(args)


'''
-10video/audio failed download
-11 Video Compression failed
-21 Audio transformation failed
'''
class Video():
    '''
    Represents a single video and formats them for feature extraction
    '''
    def __init__(self, video_id, process_video=False, process_audio=False):
        self.id = video_id
        self.video_location, self.audio_location = self.get_yt_video_data(video_id)
        self.features_extracted_status = 0
        
        if not self.video_location and not self.audio_location:
            self.features_extracted_status = -10
        else:
            if process_video:
                try:
                    self.frames_location = compress_video(self.video_location)
                except:
                    self.features_extracted_status = -11#Openface().extract_features(self.frames_location)
            if process_audio:
                #Convert audio
                try:
                    self.wav_audio_location = self.audio_location.split('.')[0]+'.wav'
                    webm_to_wav(self.audio_location, self.wav_audio_location)
                except:
                    self.features_extracted_status += -12

            #print(f"Video feature extraction for {video_id} returned with status code {self.features_extracted_status}")
    

    
    def get_yt_video_data(self, video_id, location=None):
        url = "http://youtube.com/watch?v={}"
        audio_codec="opus"
        video_stream = audio_stream = None
        
        video_location = audio_location = None
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

def extract_features_helper(video, process_video=False, process_audio=False):

    if process_video:
        #Store id for failed videos 
        extracted_status = extract_video_features(video.frames_location)
        #for status, video_id in zip(video_proc_obj.video_status, video_ids):
        if extracted_status!=0:
            errors_list.append([video.id, extracted_status, 'video'])
        else:
            #Delete the video files
            os.remove(video.video_location)
            shutil.rmtree(video.frames_location)

            processed_list.append(video.id)

    if process_audio:
        extracted_status = extract_audio_features(video.wav_audio_location)
        #for status, video_id in zip(video_proc_obj.video_status, video_ids):
        if extracted_status!=0:
            errors_list.append([video.id, extracted_status, 'audio'])
        else:
            #Delete the video files
            os.remove(video.wav_audio_location)
            os.remove(video.audio_location)

            processed_list.append(video.id)

    
    ###############################
    #Audio processing
    
    #Store id for failed audio files
    #for status, video_id in zip(video_proc_obj.audio_status, video_ids):
    #    if status!=0:
    #        errors_list.append([video_id, status, 'audio'])
    #    else:
    #        processed_list.append(video_id)
    #        #audios_failed_csv.writerow([video_id, status])

def process_videos_helper():
    while not video_ids.empty():
        video_id = video_ids.get()
        print("Helper", video_ids)
        video = Video(video_id, process_video=True)
        
        #Store id for failed videos
        status = video.features_extracted_status
        print(f"Status for {video_id} = {status}")
        if status!=0:
            errors_list.append([video_id, status, 'video'])
        else:
            downloaded_que.put(video)
        #break

            #videos_failed_csv.writerow([video_id, status])
    
        ###############################
        #Audio processing
        
        #Store id for failed audio files
        '''
        for status, video_id in zip(video_proc_obj.audio_status, video_ids):
            if status!=0:
                errors_list.append([video_id, status, 'audio'])
            else:
                processed_list.append(video_id)
                #audios_failed_csv.writerow([video_id, status])
        '''

def main():
    #return
    #global video_ids
    #Read raw data
    f = open('ids_left.json', 'r')
    processed_list.extend(json.load(f))
    f.close()

    #f = open('processed_txt_ids.json', 'r')
    #ids_to_ignore = json.load(f)
    #f.close()

    i = 0
    for _, _id in enumerate(processed_list):
        #if _id in ids_to_ignore:
        #    continue
        #if i==2000:
        #    break
        i+=1
        video_ids.put(_id)
        #print("adding id ", _id)
        #break
    #video_ids = list()
   
    '''
    f = open('Data/raw_data.csv')
    c = csv.reader(f)
    #Get rid of the header row
    next(c)
    x=0
    for i, row in enumerate(c):
        if row[12] in processed_list:
            continue
        video_ids.put(row[12])
        x+=1
        if x>=7:
            break
    f.close()
    '''
    #Fetch details of all videos
    #video_ids = video_ids[:1]+['ewfherher']#, 'wO0a2C6PqtY']
    start = time.time()
    
    #video_ids = video_ids[:5]
    #video_ids = [video_ids[3][:2]]
    #video_ids = [video_ids[0][:1], video_ids[0][1:]+[' ##################']]

    ###################################

    download_video_proc = Process(target=process_videos_helper)
    download_video_proc.start()
    time.sleep(10)
    
    openface_processes = list()
    MAX_PROCESSES = 20#cpu_count()-1

    while not video_ids.empty() or not downloaded_que.empty() or openface_processes:
        print("downloading ", video_ids, video_ids.empty(), downloaded_que.empty())
        time.sleep(2)
        openface_processes = [p for p in openface_processes if p.is_alive()]
        if not downloaded_que.empty():
            if len(openface_processes)>MAX_PROCESSES:
                print("MAX Procs running")
                continue
            print("Sarting new OpenFace proc")
            #Get running procs
            #If running procs<max, spawn, else continue
            video = downloaded_que.get()
            p = Process(target=extract_features_helper, args=(video, True, False,))
            p.start()
            openface_processes.append(p)
            print("Vid ID", video.id)
    #openface_procs = Process(target)

    ###################################

    openface_processes = [p for p in openface_processes if p.is_alive()]
    print("downloading ", video_ids, video_ids.empty(), downloaded_que.empty(), openface_processes)
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
video_ids = Queue()
errors_list = Manager().list()
processed_list = Manager().list()
downloaded_que = Queue()#Manager().Queue()
main()
