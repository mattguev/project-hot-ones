import pandas as pd
import plotly.express as px
from dataclasses import asdict
import matplotlib.pyplot as plt
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections import Counter
from models import *


"""
SETUP
"""
# spotipy wraps the official spotify api providing simple python functions.
# Replace these two variables with the client_id and client_secret generated from https://developer.spotify.com/dashboard/applications
CLIENT_ID = 'b954974542b5454382e7652a757aa3f1'
CLIENT_SECRET = '316ee5af24be426f9786c892d346d8e7'

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID,
                                                           client_secret=CLIENT_SECRET))

"""
PART 1: Getting the Top 100 Data!
"""

def getPlaylist(id: str) -> List[Track]:
    '''
    Given a playlist ID, returns a list of Track objects corresponding to the songs on the playlist. See
    models.py for the definition of dataclasses Track, Artist, and AudioFeatures.
    Audio features of each track will populate the audiofeatures list.
    Genre(s) of each artist will populate the artists in the artist list.
    '''

    # fetch tracks data from spotify given a playlist id
    playlistdata = sp.playlist(id)
    tracks = playlistdata['tracks']['items']

    # fetch audio features based on the data stored in the playlist result
    track_ids = [t['track']['id'] for t in tracks]  # build a list of track_ids from the tracks
    audio_features = sp.audio_features(track_ids)
    audio_info = {}  # Audio features list might not be in the same order as the track list
    for af in audio_features:
        audio_info[af['id']] = AudioFeatures(af['danceability'],
                                             af['energy'],
                                             af['key'],
                                             af['loudness'],
                                             af['mode'],
                                             af['speechiness'],
                                             af['acousticness'],
                                             af['instrumentalness'],
                                             af['liveness'],
                                             af['valence'],
                                             af['tempo'],
                                             af['duration_ms'],
                                             af['time_signature'],
                                             af['id'])

    # prepare artist dictionary
    artist_messy = []
    for t in tracks:
        for i in t['track']['artists']:
            artist_messy.append(i['id'])
    artist_ids = list(set(artist_messy)) # make a list of unique artist ids from tracks list x
    artists = {}
    for k in range(1 + len(artist_ids) // 50):  # can only request info on 50 artists at a time
        artists_response = sp.artists(artist_ids[k * 50:min((k + 1) * 50, len(artist_ids))]) # iteratively requests 50 items or the remainder of artist_ids (e.g. 0-50, 50-100 or artist_ids[-1])
        for a in artists_response['artists']:
            artists[a['id']] = Artist(a['id'],
                                      a['name'],
                                      a['genres'])  # create the Artist for each id (see audio_info, above) x

    # populate track dataclass
    trackList = [Track(id=t['track']['id'],
                       name=t['track']['name'],
                       artists=[artists[i['id']] for i in t['track']['artists']],
                       audio_features=audio_info[t['track']['id']])
                                                    for t in tracks]
    return (trackList)

''' Function for calling Billboard Hot 100. Can write
additional functions like "top Canadian hits!".'''

def getHot100() -> List[Track]:
    # Billboard hot 100 Playlist ID URI
    hot_100_id = "6UeSakyzhiEt4NB3UAd6NQ"
    return (getPlaylist(hot_100_id))

"""
Part 2: The Helper Functions
"""

def getGenres(t: Track) -> List[str]:
    '''
    Takes in a Track and produce a list of unique genres that the artists of this track belong to
    '''
    genre_list = []
    for a in t.artists:
        for g in a.genres:
            genre_list.append(g)
    return list(set(genre_list))

def doesGenreContains(t: Track, genre: str) -> bool:
    '''
    Checks if the genres of a track contains the key string specified
    For example, if a Track's unique genres are ['pop', 'country pop', 'dance pop']
    doesGenreContains(t, 'dance') == True
    doesGenreContains(t, 'pop') == True
    doesGenreContains(t, 'hip hop') == False
    '''
    in_genre = False
    for i in getGenres(t):
        if genre in i:
            in_genre = True
    return in_genre

def getTrackDataFrame(tracks: List[Track]) -> pd.DataFrame:
    '''
    Prepare dataframe for a list of tracks
    audio-features: 'danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness',
                    'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo',
                    'duration_ms', 'time_signature', 'id',
    track & artist: 'track_name', 'artist_ids', 'artist_names', 'genres',
                    'is_pop', 'is_rap', 'is_dance', 'is_country'
    '''
    # populate records
    records = []
    for t in tracks:
        to_add = asdict(t.audio_features)  # converts an audio_features object to a key-value pair
        to_add["track_name"] = t.name
        to_add["artist_ids"] = list(map(lambda a: a.id, t.artists))
        to_add["artist_names"] = list(map(lambda a: a.name, t.artists))
        to_add["genres"] = getGenres(t)
        to_add["is_pop"] = doesGenreContains(t, "pop")
        to_add["is_rap"] = doesGenreContains(t, "rap")
        to_add["is_dance"] = doesGenreContains(t, "dance")
        to_add["is_country"] = doesGenreContains(t, "country")

        records.append(to_add)

    # create dataframe from records
    df = pd.DataFrame.from_records(records)
    return (df)

# The most popular artist of the week

def artist_with_most_tracks(tracks: List[Track]) -> (Artist, int):
    '''
    List of tracks -> (artist, number of tracks the artist has)
    This function finds the artist with most number of tracks on the list
    If there is a tie, return any of the artists
    '''
    arts = {}
    artists = {}
    for t in tracks:
        for a in t.artists:
            if a.id in arts:
                arts[a.id] += 1
            else:
                artists[a.id] = a
                arts[a.id] = 1

    tally = Counter(arts)
    return (artists[tally.most_common(1)[0][0]], tally.most_common(1)[0][1])

"""
Part 3: Visualizing the Data
"""

# 3.1 scatter plot of dancability-speechiness with markers colored by genre: is_rap
def danceability_plot(tracks: List[Track]):
    df = getTrackDataFrame(tracks)
    ax = plt.gca()
    grouped = df.groupby('is_rap')
    colors = {True: 'blue', False: 'red'}
    for key, group in grouped:
        group.plot(ax=ax, kind='scatter', x='danceability', y='speechiness', color=colors[key], label=key)
    plt.xlabel('Danceability')
    plt.ylabel('Speechiness')
    plt.legend(title="Genre: Is Rap")
    plt.show()

# 3.2 scatter plot
# Question: how accurate is the stereotype of popular country songs as acoustic, lyrically-driven pieces compared to other genres?
def country_plot(tracks: List[Track]):
    df = getTrackDataFrame(tracks)
    ax1 = plt.gca()
    grouped = df.groupby('is_country')
    colors = {True: 'blue', False: 'red'}
    for key, group in grouped:
        group.plot(ax=ax1, kind='scatter', x='acousticness', y='speechiness', color=colors[key], label=key)
    plt.xlabel('Acousticness')
    plt.ylabel('Speechiness')
    plt.legend(title="Genre: Is Country")
    plt.show()

# Answer: Popular country music seems to be no more "acoustic" than other popular genres. It is also notably less "speechy" or lyrically dense compared to other genres.
# This suggests that the common stereotype does not hold true for today's popular country music.

# 3.3 Plotting an interactive chart of trajectories for number ones over the last year
def interact_plot():
    '''
    CODE FOR PRODUCING hotones.csv

    import billboard
    import datetime as dt

    today = dt.date.today()

    # Billboard API queries for saturdays
    dayspostsat = (today.weekday() + 2) % 7 # today.weekday() outputs Monday = 0 and Sunday = 6
    lastSat = today - dt.timedelta(days=dayspostsat)
    one_week = dt.timedelta(days=7)

    chartlist = [] # list of dictionaries

    for k in range(52):
        chart = billboard.ChartData('hot-100', date=lastSat)
        for x in chart.entries:
            d = dict()
            d['date'] = str(lastSat)
            d['title'] = x.title
            d['artist'] = x.artist
            d['rank'] = x.rank
            d['peakPos'] = x.peakPos
            d['lastPos'] = x.lastPos
            d['isNew'] = x.isNew
            d['weeks'] = x.weeks
            chartlist.append(d)
        lastSat = lastSat - one_week

    df = pd.DataFrame(chartlist)  # variable df is a dataframe
    df.to_csv('hot_ones.csv', index=False)
    '''

    df = pd.read_csv('hotones.csv')

    # project out the song names for the rows whose rank is 1,
    ones = df[df['rank'] == 1]['title']
    onesarts = df[df['rank'] == 1]['artist']

    # project out the rows whose titles are in the list produced above
    onespath = df[(df['title'].isin(ones)) & (df['artist'].isin(onesarts))]
                        # isin() queries dataframe values for their existence in other dataframes

    # creates an interactive web page for the data, which charts the path of all songs that were ever number 1 over the last year.
    fig = px.line(onespath, x="date", y="rank", color="title", hover_data=["artist"])
    fig.update_traces(mode="markers+lines")
    fig.update_yaxes(autorange="reversed")

    fig.show()

# Primary function call for all visualizations and analyses
def main():
    top100Tracks = getHot100()
    df = getTrackDataFrame(top100Tracks)
    artist, num_track = artist_with_most_tracks(top100Tracks)
    print("%s has the most number of tracks on this week's Hot 100 at a whopping %d tracks!" % (artist.name, num_track))
    danceability_plot(getHot100())
    country_plot(getHot100())
    interact_plot()

main()
