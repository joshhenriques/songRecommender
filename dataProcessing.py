import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity  
from sklearn.metrics.pairwise import sigmoid_kernel
import numpy as np

numOfSongs = 50
popFactor = 0.5 # 0 - No popularity factor , higher the more popularity has effect

genreFactor = 1

def makeData(sp):

    i=0

    mt_complete = False

    mt_features = []

    genres = []

    #Only working w short term data for now
    while True:
        if mt_complete: break

        if not mt_complete: medium_term = sp.current_user_top_tracks(limit=20,offset = i*20,time_range="medium_term")['items']

        if len(medium_term) < 20: mt_complete = True

        for item in medium_term: 
            artistName = item['album']['artists'][0]['name'] 
            track = sp.search(artistName)['tracks']['items'][0]
            artist = sp.artist(track["artists"][0]["external_urls"]["spotify"])
            genres += artist['genres']
            mt_features += sp.audio_features(item['id'])

        i += 1
    
    from collections import Counter
    # genres.sort(key=Counter(genres).get, reverse=True)
    genreDict = {}
    for genre in set(genres):
        genreDict[genre.replace(' ', '-')] = genres.count(genre) / len(set(genres))

    mt_dataFrame = pd.DataFrame(mt_features)
    mt_dataFrame = mt_dataFrame.drop(mt_dataFrame.columns[14:], axis=1)  #Holds the data to reccomend song
    mt_dataFrame = mt_dataFrame.drop(mt_dataFrame.columns[11:13], axis=1) 

    songs = genRecommendations(mt_dataFrame, genreDict)
    # print(st_dataFrame)
    return songs

def genRecommendations(df, genreDict):

    #Organize CSV data to have same format as df
    spotify_df = pd.read_csv('dataset.csv')
    spotify_df = spotify_df.drop_duplicates(subset=['track_id'])
    #Drop songs that have genre that do not allign with users

    # print(genreDict)
    spotify_df = spotify_df[spotify_df['track_genre'].str.contains('|'.join(key for key in genreDict.keys()))]
    datasetGenres = spotify_df['track_genre']

    popularity = spotify_df['popularity']
    spotify_df = spotify_df.drop(spotify_df.columns[2:8], axis = 1)
    spotify_df = spotify_df.drop(spotify_df.columns[0], axis = 1)
    spotify_df = spotify_df.drop(spotify_df.columns[12:], axis = 1)
    spotify_df = spotify_df.rename(columns={'track_id' : 'uri'})


    feature_cols=['danceability','energy','key', 'loudness', 'mode','speechiness','acousticness',
                  'instrumentalness', 'liveness', 'valence','tempo']
    
    #Scale Data
    scaler = MinMaxScaler()
    df[feature_cols] = scaler.fit_transform(df[feature_cols])
    popularity = scaler.fit_transform(popularity.values.reshape(-1, 1))
    spotify_df[feature_cols] = scaler.fit_transform(spotify_df[feature_cols])

    weightedVector = genWeightedVector(df)

    # Create cosine model
    spotify_df['sim'] = popularity
    for index, row in spotify_df.iterrows():
        spotify_df.at[index, 'sim'] =  popFactor*spotify_df.at[index, 'sim'] + cosine_similarity(np.array(row[feature_cols]).reshape(1,-1), weightedVector.reshape(1,-1))

        try:
            spotify_df.at[index, 'sim'] = spotify_df.at[index, 'sim'] + genreDict[datasetGenres[index]] * genreFactor
        except:
            continue

    topSongs = spotify_df.sort_values('sim', ascending=False).head(numOfSongs)
    print(topSongs.head(2))
   
    return topSongs['uri'].tolist()

def genWeightedVector(df):

    feature_cols=['danceability','energy','key', 'loudness', 'mode','speechiness','acousticness',
                  'instrumentalness', 'liveness', 'valence','tempo']
    
    weightedVector = [0]*len(feature_cols)

    for i, row in df.iterrows():
        ind = 0
        for feature in feature_cols:
            weightedVector[ind] += row[feature] / len(df.index)
            ind+=1

    return np.array(weightedVector)
