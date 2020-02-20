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
    
    if response['pageInfo']['totalResults']:
        return response
    
    #Second(final) request assuming channel_identifier is channel ID
    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        id=channel_identifier
    )

    response = request.execute()
    
    #If channel_identifier neither ID nor name, raise an Exception
    assert response['pageInfo']['totalResults'], Exception('Empty result')
    
    return response

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
        playlistId="UUddem5RlB3bQe99wyY49g0g"
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
    return response['items'][0]['statistics']

def get_data():
    '''
    channel_identifier  : ID or name
    playlist_name       : Name or blank
    '''
    
    channel_identifier = 'ChickComedy'
    playlist_name = ''
    #Get channel details for channel id and uploads playlist ID.
    try:
        channel_data = get_channel_data(channel_identifier)
    except:
        print(f"Unable to process {channel_identifier}")
        return False
    
    channel_id = channel_data['items'][0]['id']
    uploads_playlist_id = channel_data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    #Using playlist_id, extract all video IDs
    playlist_id = uploads_playlist_id if not playlist_name else playlist_name
    if playlist_id != uploads_playlist_id:
        all_playlists = get_all_playlists(channel_id)
        playlist_id = all_playlists[playlist_name]

    #Video_ids for all videos in the playlist
    playlist_data = get_playlist_data(playlist_id)

    print("video Data")
    for video in playlist_data:
        video_data = get_video_data(video['video_id'])
        pp.pprint(video_data)

if __name__ == "__main__":
    print("Test")
    main()
    process_csv()

    '''
    channel_data = get_channel_data('sdwd')
    channel_id = channel_data['items'][0]['id']

    playlist_id = channel_data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    print(f"Playlist id={playlist_id}")
    
    all_playlists = get_all_playlists(channel_id)
    print(f"All playlists")
    pp.pprint(all_playlists)

    playlist_data = get_playlist_data(playlist_id)
    
    print("Playlist Videos")
    pp.pprint(playlist_data)

    video_data = get_video_data(playlist_data[0]['video_id'])
    
    print("video Data")
    pp.pprint(video_data)
    #pp.pprint(response)
    '''
