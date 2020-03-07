# -*- coding: utf-8 -*-

# Sample Python code for youtube.channels.list
# See instructions for running these code samples locally:
# https://developers.google.com/explorer-help/guides/code_samples#python

import os
import json
import pprint
import csv
import random

pp = pprint.PrettyPrinter(indent=4)

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
youtube = None

def get_credentials():
    names = os.listdir('data_retrieval/client_secret/')
    random.shuffle(names)
    for name in names:
        if 'json' not in name:
            continue
        yield name
credential_files = get_credentials()

def main():
    global youtube
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"

    try:
        client_secrets_file = 'data_retrieval/client_secret/'+next(credential_files)#"data_retrieval/client_secret_9.json"
        print(f"Using {client_secrets_file}")
    except Exception as e:
        print("Quotas for all credentials exhausted")
        raise(e)

    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    credentials = flow.run_console()
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)

#Restart function if quota gets exhausted
#TODO : Handle partial data
def restart_on_quota_exhaustion(fxn):

    def inner(*args, **kwargs):
        try:
            return fxn(*args, **kwargs)
        except Exception as e:
            print("Restart ",str(e), kwargs)
            main()
            return fxn(*args, **kwargs)

    return inner

@restart_on_quota_exhaustion
def execute_yt_call(api, params):
    print(api, params)
    if api=='channels':
        request = youtube.channels().list(**params)
    elif api=='playlists':
        request = youtube.playlists().list(**params)
    elif api=='playlist_items':
        request = youtube.playlistItems().list(**params)
    elif api=='video':
        request = youtube.videos().list(**params)
    else:
        raise NotImplementedError()

    response = request.execute()
    return response

#Get playlist id
def get_channel_data(channel_identifier):
    #First request assuming channel_identifier is channel name
    response =   execute_yt_call("channels",
                                {
                                    'part':"snippet,contentDetails,statistics",
                                    'forUsername':channel_identifier
                                })
    if not response['pageInfo']['totalResults']:
        #Second(final) request assuming channel_identifier is channel ID
        response = execute_yt_call("channels", 
                                {
                                    'part':"snippet,contentDetails,statistics",
                                    'id':channel_identifier
                                })
    
    #If channel_identifier neither ID nor name, raise an Exception
    assert response['pageInfo']['totalResults'], Exception('Empty result')
    
    retval = dict()
    retval['channel_id'] = response['items'][0]['id']
    retval['uploads_playlist_id'] = response['items'][0]['contentDetails']['relatedPlaylists']['uploads'] 
    retval['channel_stats'] = response['items'][0]['statistics']
    retval['title'] = response['items'][0]['snippet']['title']
    retval['published_at'] = response['items'][0]['snippet']['publishedAt']
    
    return retval

#For a given channel get all playlist_name and corresponding ids
def get_all_playlists(channel_id):
    response = execute_yt_call("playlists", 
            {
                'part':"snippet",
                'maxResults':50,
                'channelId':channel_id
                })

    playlist_names = {playlist['snippet']['title'].lower().replace(' ', ''): playlist['id'] for playlist in response['items']}
    playlist_ids = {playlist['id'].lower().replace(' ', ''): playlist['id'] for playlist in response['items']}
    playlists = {**playlist_ids, **playlist_names}

    while 'nextPageToken' in response:
        pageToken = response['nextPageToken']
        response = execute_yt_call("playlists", 
                {
                    'part':"snippet",
                    'maxResults':50,
                    'pageToken':pageToken,
                    'channelId':channel_id
                    })

        playlist_names = {playlist['snippet']['title'].lower().replace(' ', ''): playlist['id'] for playlist in response['items']}
        playlist_ids = {playlist['id'].lower().replace(' ', ''): playlist['id'] for playlist in response['items']}
        playlists.update(playlist_names)
        playlists.update(playlist_ids)

    pp.pprint(playlists)
    return playlists

#Get playlist data
def get_playlist_data(playlist_id):
    '''
    PARAMS
    playlist_id

    RETURN
    {
    id: video_id
    }

    '''
    response = execute_yt_call("playlist_items", 
            {
                'part':"contentDetails",
                'maxResults':50,
                'playlistId':playlist_id
                })

    total_videos = response['pageInfo']['totalResults']
    video_ids = [{'video_id' : video['contentDetails']['videoId']} for video in response['items']]
    
    total = 50
    while 'nextPageToken' in response:
        pageToken = response['nextPageToken']
        response = execute_yt_call("playlist_items", 
                {
                    'part':"contentDetails",
                    'maxResults':50,
                    'pageToken':pageToken,
                    'playlistId':playlist_id
                    })
        video_ids.extend([{'video_id' : video['contentDetails']['videoId']} for video in response['items']])
        total+=50
    
    return video_ids

#Get video data
def get_video_data(video_id):
    response = execute_yt_call('video', 
            {
                'part':"snippet,statistics",
                'id':video_id
                })

    retval = response['items'][0]['statistics']
    
    videoReleaseDate = response['items'][0]['snippet']['publishedAt']

    retval['id'] = video_id
    retval['published_date'] = videoReleaseDate

    return retval

def get_data(channel_identifier, playlist_name):
    '''
    channel_identifier  : ID or name
    playlist_name       : Name or blank

    RETURN
    aggregate_channel_data
    {
        channel_id:
        playlist_id:
    }
    '''
    
    #To store all data for this channel. To be returned at the end.
    aggregate_channel_data = dict()

    #Get channel details for channel id and uploads playlist ID.
    try:
        channel_data = get_channel_data(channel_identifier)
    except:
        print(f"Unable to process {channel_identifier}")
        return False
    
    channel_id = channel_data['channel_id']
    aggregate_channel_data.update(channel_data)
    
    uploads_playlist_id = channel_data['uploads_playlist_id']
    
    #Using playlist_id, extract all video IDs
    playlist_id = uploads_playlist_id if not playlist_name else playlist_name
    if playlist_id != uploads_playlist_id:
        #Standardize playlist name/id
        playlist_name = playlist_name.lower().replace(' ','')
        all_playlists = get_all_playlists(channel_id)
        playlist_id = all_playlists[playlist_name]

    #Video_ids for all videos in the playlist
    aggregate_channel_data['playlist_id'] = playlist_id
    playlist_data = get_playlist_data(playlist_id)

    aggregate_channel_data['videos'] = list()
    for video in playlist_data:
        try:
            video_data = get_video_data(video['video_id'])
        except:
            continue
        aggregate_channel_data['videos'].append(video_data)
    
    pp.pprint(aggregate_channel_data)
    return aggregate_channel_data

def get_channel_from_playlist(playlist_id):
    response = execute_yt_call("playlists", 
            {
                'part':"snippet",
                'maxResults':50,
                'id':playlist_id
                })

    try:
        channel_id = response['items'][0]['snippet']['channelId']
        return channel_id
    except Exception as e:
        print(f"Exception in getting channel from playlist {e}")
        return False
    
def process_channel_list():
    #Read from csv
    f = open('/users/prabhjotsingh/Downloads/comedy_sheet.csv', 'r')
    csv_reader = csv.reader(f)

    headers = next(csv_reader)
    file_data = [{col:val for col,val in zip(headers, row)} for row in csv_reader]
    
    f.close()

    #Aggregate data for all channels
    final_data = list()
    for i, row in enumerate(file_data[48:], 48):
        print(f"Current Item : {i}")
        try:
            #If playlist name/id in channel data, get the actual channel id
            print("Getting channel from playlist")
            channel_id = get_channel_from_playlist(row['ID'])
            print(f"Got channel from playlist {channel_id}")

            if channel_id:
                row['Playlist ID'] = row['ID']
                row['ID'] = channel_id

            #Handle the case where all playlists have to be downloaded
            if row['Playlist ID'] == "all playlists":
                playlists = get_all_playlists(row['ID'])
            else:#Use current playlist
                playlists = {row['Playlist ID']: row['Playlist ID']}
            
            playlist_ids_seen = set()
            for playlist_name ,playlist_id in playlists.items():
                if playlist_id in playlist_ids_seen:
                    continue
                playlist_ids_seen.add(playlist_id)
                #channel_data = get_data(row['ID'], row['Playlist ID'])
                channel_data = get_data(row['ID'], playlist_id)
                if not channel_data:
                    continue
                final_data.append(channel_data)
        except Exception as e:
            print(str(e))
            break

    #Write to csv
    headers = ['title', 'published_at', 'subscriberCount', 'videoCount', 'viewCount', 'video_published_date', 'video_commentCount', 'video_viewCount', 'video_likeCount', 'video_dislikeCount', 'video_favoriteCount', 'video_id']
    channel_stats_to_store = ['subscriberCount', 'videoCount', 'viewCount']
    f = open('raw_data_additional_3.csv', 'w')
    csv_writer = csv.writer(f)

    csv_writer.writerow(headers)
    for channel in final_data:
        row = dict()
        row['published_at'] = channel['published_at']
        row['title'] = channel['title']
        for name in channel_stats_to_store:
            row[name] = channel['channel_stats'][name]
        
        for video in channel['videos']:
            try:
                for key, val in video.items():
                    row['video_'+key] = val
                csv_writer.writerow([row[col] for col in headers])
            except:
                pp.pprint(video)
                print("Exception while trying to write video")

    f.close()

if __name__ == "__main__":
    print("Test")
    main()
    process_channel_list()
    #get_data()
