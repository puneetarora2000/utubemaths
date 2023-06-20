from flask import Flask, render_template, request
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz
from datetime import datetime, timedelta
app = Flask(__name__)

# Set up YouTube Data API credentials
api_key = "AIzaSyAXsOWrEWZ1VfK9ScymTIrXJu37R_lS_70"
api_service_name = "youtube"
api_version = "v3"


# Set up YouTube Data API client
youtube = build(api_service_name, api_version, developerKey=api_key)


def get_channel_id(channel_name):
    youtube = build("youtube", "v3", developerKey=api_key)

    search_response = youtube.search().list(
        part="snippet",
        q=channel_name,
        type="channel",
        maxResults=1
    ).execute()
    channel_ids = search_response["items"][0]["id"]["channelId"]

    return channel_ids


@app.route('/', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        channel_name = request.form['channel_id']
        channel_id = get_channel_id(channel_name)
        channel_details = get_channel_details(channel_id)

        if channel_details:
            video_df = get_video_details(channel_id)

            video_stats = perform_statistical_analysis(video_df)
            most_viewed_video = get_most_viewed_video(video_df)
            most_liked_video = get_most_liked_video(video_df)
            least_viewed_video = get_least_viewed_video(video_df)
            popular_videos_last_30_days = get_popular_videos_last_30_days(video_df)
            views_last_30_days_graph = create_views_last_30_days_graph(video_df)

            return render_template('dashboard.html',
                                   channel_name=channel_details['title'],
                                   subscriber_count=channel_details['subscriberCount'],
                                   total_views=channel_details['viewCount'],
                                   video_stats=video_stats,
                                   most_viewed_video=most_viewed_video,
                                   most_liked_video=most_liked_video,
                                   least_viewed_video=least_viewed_video,
                                   popular_videos_last_30_days=popular_videos_last_30_days,
                                   views_last_30_days_graph=views_last_30_days_graph)

    return render_template('form.html')


def get_channel_details(channel_id):
    try:
        response = youtube.channels().list(
            part="snippet,statistics",
            id=channel_id
        ).execute()

        channel = response['items'][0]
        channel_details = {
            'title': channel['snippet']['title'],
            'subscriberCount': channel['statistics']['subscriberCount'],
            'viewCount': channel['statistics']['viewCount']
        }

        return channel_details

    except HttpError as e:
        print("An error occurred:", e)


def get_video_details(channel_id):
    
    
    try:
        df = pd.read_csv(channel_id + ".csv")
    except FileNotFoundError:
        df = pd.DataFrame()  # Create an empty DataFrame if the file is not found

    if df.empty:
       print("CSV NOT FOUND")
    else:
        print("Loading from csv")
        return df
        
        
    
    try:
        print("Extracting Data from youtube api")
        response = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            maxResults=50,
            order="date"
        ).execute()

        video_data = []
        for item in response['items']:
            if 'videoId' in item['id']:
                video_id = item['id']['videoId']
                video_stats = youtube.videos().list(
                    part="snippet,statistics",
                    id=video_id
                ).execute()

                snippet = video_stats['items'][0]['snippet']
                stats = video_stats['items'][0]['statistics']
                snippet['views'] = stats['viewCount']
                snippet['likes'] = stats['likeCount']
                video_data.append(snippet)

        df = pd.DataFrame(video_data)
        df.to_csv(channel_id+".csv")
        
        
        return df

    except HttpError as e:
        print("An error occurred:", e)

def perform_statistical_analysis(video_df):
    
    video_stats = video_df.describe()
    return video_stats

def get_most_viewed_video(video_df):
    video_df['views'] = pd.to_numeric(video_df['views'], errors='coerce')
    most_viewed_video = video_df.loc[video_df['views'].idxmax()]
    return most_viewed_video


def get_most_liked_video(video_df):
    video_df['likes'] = pd.to_numeric(video_df['likes'], errors='coerce')

    most_liked_video = video_df.loc[video_df['likes'].idxmax()]
    return most_liked_video


def get_least_viewed_video(video_df):
    least_viewed_video = video_df.loc[video_df['views'].idxmin()]
    return least_viewed_video



def get_popular_videos(video_df):
    popular_videos = video_df[video_df['views'] > 1000]
    return popular_videos

def get_published_last_30_days(video_df):
    utc = pytz.UTC
    last_30_days = datetime.now() - timedelta(days=30)
    last_30_days = pd.to_datetime(last_30_days).replace(tzinfo=utc)
    video_df['publishedAt'] = pd.to_datetime(video_df['publishedAt'])
    recent_videos = video_df[video_df['publishedAt'] > last_30_days]
    return recent_videos

def get_popular_videos_last_30_days(video_df):
    popular_videos = get_popular_videos(video_df)
    popular_recent_videos = get_published_last_30_days(popular_videos)
    popular_recent_videos = popular_recent_videos.sort_values('views', ascending=False)
    
    return popular_recent_videos




def create_views_last_30_days_graph(video_df):
    utc = pytz.UTC
    last_30_days = datetime.now() - timedelta(days=30)
    last_30_days = last_30_days.replace(tzinfo=None)  # Remove timezone information
    last_30_days = utc.localize(last_30_days)  # Set the timezone to UTC
    video_df['publishedAt'] = pd.to_datetime(video_df['publishedAt'])   


    video_df_last_30_days = video_df[video_df['publishedAt'] > last_30_days]
    video_df_last_30_days['publishedAt'] = video_df_last_30_days['publishedAt'].dt.date
    video_df_last_30_days = video_df_last_30_days.sort_values(by='publishedAt')

    plt.figure(figsize=(10, 6))
    sns.lineplot(data=video_df_last_30_days, x='publishedAt', y='views')
    plt.xticks(rotation=90)
    plt.xlabel('Date')
    plt.ylabel('Views')
    plt.title('Video Views in Last 30 Days')
    plt.tight_layout()
    plt.savefig('static/views_last_30_days_graph.png')
    plt.close()

    return 'views_last_30_days_graph.png'


if __name__ == '__main__':
    app.run(debug=True)
