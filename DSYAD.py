import pandas as pd
#import seaborn as sns
#import matplotlib.pyplot as plt
from googleapiclient.discovery import build
from flask import Flask, render_template, request
from googleapiclient.errors import HttpError

# Made class 'YouTubeAnalyticsApp' which contains all the methods that are extracting the channel details.
class YouTubeAnalyticsApp:
    def __init__(self, api_key, youtube):
        self.api_key = api_key
        self.youtube = youtube

    def get_channel_id(self, channel_username):
        '''Function to get channel id.'''
        try:
            search_response = self.youtube.search().list(
                                        part='snippet',
                                        maxResults=1,
                                        q=channel_username,
                                        type='channel'
            ).execute()
            
            channel_id = search_response['items'][0]['id']['channelId']
            
            return channel_id
        
        except HttpError as e:
            error_message = f'An error occured: {e}'
            return error_message
        
    def get_playlist_id(self, channel_id):
        '''Function to get playlist id.'''
        try:
            search_response = self.youtube.channels().list(
                                part='snippet,contentDetails,statistics',
                                id=channel_id).execute()
            
            playlist_id = search_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

            return playlist_id
        
        except HttpError as e:
            error_message = f'An error occured: {e}'
            return error_message


    def get_video_ids(self, playlist_id):
        '''Function to get all the video ids of the channel.'''
        try:
            search_response = self.youtube.playlistItems().list(
                            part='contentDetails',
                            playlistId=playlist_id,
                            maxResults=50).execute()


            video_ids = []
            for i in range(len(search_response['items'])):
                video_ids.append(search_response['items'][i]['contentDetails']['videoId'])
                
            next_page_token = search_response.get('nextPageToken')
            more_pages = True
            
            while more_pages:
                if next_page_token is None:
                    more_pages = False
                    
                else:
                    search_response = self.youtube.playlistItems().list(
                                            part='contentDetails',
                                            playlistId=playlist_id,
                                            maxResults=50,
                                            pageToken=next_page_token).execute()
                    
                    for i in range(len(search_response['items'])):
                        video_ids.append(search_response['items'][i]['contentDetails']['videoId'])
                        
                    next_page_token = search_response.get('nextPageToken')
            
            return video_ids
        
        except HttpError as e:
            error_message = f'An error occured: {e}'
            return error_message
        
    def get_video_details(self, video_ids):
        '''Function to get all videos detail in a dictionary format.''' 
        try:
            all_data = []
            for i in range(0, len(video_ids), 50):
            
                search_response = self.youtube.videos().list(
                                        part='snippet, contentDetails, statistics',
                                        id=','.join(video_ids[i:i+50])).execute()
                
                for video in search_response['items']:
                    data = dict(Published_date = video['snippet']['publishedAt'],
                                Title = video['snippet']['title'],
                                Duration = video['contentDetails']['duration'],
                                Views = video['statistics']['viewCount'],
                                Likes = video['statistics']['likeCount'],
                                Comments = video['statistics'].get('commentCount', 0)
                            )
                
                    all_data.append(data)
            
            return all_data
        
        except HttpError as e:
            error_message = f'An error occured: {e}'
            return error_message

    def get_most_liked_video(self, video_data):
        '''Function to get the most liked video of all time.'''
        try:
            most_liked_video = video_data[video_data['Likes'] == max(video_data['Likes'])]['Title'].iloc[0]
            url = video_data[video_data['Likes'] == max(video_data['Likes'])]['video_url'].iloc[0]
            num_likes = video_data[video_data['Likes'] == max(video_data['Likes'])]['Likes'].iloc[0]

            return most_liked_video, url, num_likes
        
        except HttpError as e:
            error_message = f'An error occured: {e}'
            return error_message
        
    def get_most_viewed_video(self, video_data):
        '''Function to get the most viewed video of all time.'''
        try:
            most_viewed_video = video_data[video_data['Views'] == max(video_data['Views'])]['Title'].iloc[0]
            url = video_data[video_data['Views'] == max(video_data['Views'])]['video_url'].iloc[0]
            num_views = video_data[video_data['Views'] == max(video_data['Views'])]['Views'].iloc[0]

            return most_viewed_video, url, num_views
        
        except HttpError as e:
            error_message = f'An error occured: {e}'
            return error_message
        
    def get_channel_stats(self, video_data):
        '''Function to get the analytics overview and engagement metrics of the channel.'''
        try:
            Total_likes = video_data['Likes'].sum()
            Total_views = video_data['Views'].sum()
            Total_comments = video_data['Comments'].sum()
            Average_likes = int(round(video_data['Likes'].mean(), 0))
            Average_views = int(round(video_data['Views'].mean(), 0))
            Average_comments = int(round(video_data['Comments'].mean(), 0))
            Likes_2_views_ratio = round(Total_likes/Total_views, 5)
            Comments_2_views_ratio = round(Total_comments/Total_views, 5)

            return Total_likes, Total_views, Total_comments, Average_likes, Average_views, Average_comments,\
                     Likes_2_views_ratio, Comments_2_views_ratio
        
        except HttpError as e:
            error_message = f'An error occured: {e}'
            return error_message



# Flask app     
app = Flask(__name__)

# Api key
api_key = 'AIzaSyD2_qXdRGbT5D6tq-X-ZkRXIi7y_2jp5tM'
# Build the youtube service
youtube = build('youtube', 'v3', developerKey=api_key)
# Object to call the class 'YouTubeAnalyticsApp'
youtube_channel_stats = YouTubeAnalyticsApp(api_key, youtube)

# Route for home page
@app.route('/', methods=['GET', 'POST'])
def home_page():
    return render_template('index.html')

# Route for result page
@app.route('/youtube_analytics', methods=['POST'])
def youtube_dashboard():
    if request.method == 'POST':
        global channel_username
        channel_username = request.form.get('channel_username')

        channel_id = youtube_channel_stats.get_channel_id(channel_username)
        playlist_id = youtube_channel_stats.get_playlist_id(channel_id)
        video_ids = youtube_channel_stats.get_video_ids(playlist_id)
        videos_detail = youtube_channel_stats.get_video_details(video_ids)

        video_data = pd.DataFrame(videos_detail)
        video_data['Comments'] = pd.to_numeric(video_data['Comments'])
        video_data['Likes'] = pd.to_numeric(video_data['Likes'])
        video_data['Views'] = pd.to_numeric(video_data['Views'])
        video_url = ['https://www.youtube.com/watch?v=' + video_id for video_id in video_ids]
        video_data['video_url'] = video_url

        most_liked_video, url_most_liked, num_likes = youtube_channel_stats.get_most_liked_video(video_data)
        most_viewed_video, url_most_viewed, num_views = youtube_channel_stats.get_most_viewed_video(video_data)
        Total_likes, Total_views, Total_comments, Average_likes, Average_views, Average_comments,Likes_2_views_ratio, Comments_2_views_ratio = \
                                                                                            youtube_channel_stats.get_channel_stats(video_data)

        return render_template('results.html', most_liked_video=most_liked_video, url_most_liked=url_most_liked, num_likes=num_likes,
                               most_viewed_video=most_viewed_video, url_most_viewed=url_most_viewed, num_views=num_views,
                               Total_likes=Total_likes, Total_views=Total_views, Total_comments=Total_comments,
                               Average_likes=Average_likes, Average_views=Average_views,
                               Average_comments=Average_comments, Likes_2_views_ratio=Likes_2_views_ratio,
                               Comments_2_views_ratio=Comments_2_views_ratio)
    
    return render_template('results.html')

# Run flask app
if __name__ == '__main__':
    app.run(debug=True)