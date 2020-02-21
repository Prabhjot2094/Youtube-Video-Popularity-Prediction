# -*- coding: utf-8 -*-

# Sample Python code for youtube.channels.list
# See instructions for running these code samples locally:
# https://developers.google.com/explorer-help/guides/code_samples#python

import os
import json
import pprint

pp = pprint.PrettyPrinter(indent=4)

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
youtube = None

def main():
    global youtube
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "data_retrieval/client_secret.json"

    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    credentials = flow.run_console()
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)

#Get playlist id
def get_channel_data(channel_identifier):
    #First request assuming channel_identifier is channel name
    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        forUsername="justforlaughscomedy"
    )
    response = request.execute()
    
    if not response['pageInfo']['totalResults']:
        #Second(final) request assuming channel_identifier is channel ID
        request = youtube.channels().list(
            part="snippet,contentDetails,statistics",
            id=channel_identifier
        )
        response = request.execute()
    
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
    request = youtube.playlists().list(
        part="snippet,contentDetails",
        channelId="UCxPmXKxJcDAhuYVHeFFyGTA",
        maxResults=25
    )
    response = request.execute()

    playlists = {playlist['snippet']['title']: playlist['id'] for playlist in response['items']}
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
    request = youtube.playlistItems().list(
        part="snippet,contentDetails",
        maxResults=25,
        playlistId=playlist_id
    )
    response = request.execute()

    video_ids = [{'video_id' : video['contentDetails']['videoId']} for video in response['items']]
    return video_ids

#Get video data
def get_video_data(video_id):
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=video_id
    )
    response = request.execute()
    
    retval = response['items'][0]['statistics']
    retval['video_id'] = video_id
    
    return retval

def get_data():
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

    channel_identifier = 'ChickComedy'
    playlist_name = ''
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
        all_playlists = get_all_playlists(channel_id)
        playlist_id = all_playlists[playlist_name]

    #Video_ids for all videos in the playlist
    aggregate_channel_data['playlist_id'] = playlist_id
    playlist_data = get_playlist_data(playlist_id)

    #print("video Data")
    aggregate_channel_data['videos'] = list()
    for video in playlist_data:
        #print(video)
        video_data = get_video_data(video['video_id'])
        aggregate_channel_data['videos'].append(video_data)
        #pp.pprint(video_data)
    
    pp.pprint(aggregate_channel_data)
    return aggregate_channel_data

if __name__ == "__main__":
    print("Test")
    main()
    get_data()
