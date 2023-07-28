import os
import datetime
import pickle
from hashlib import md5

class SongsFolderLibrary:
    def __init__(self, songsFolderPath=None):
        self.hashDict = {}
        self.songsFolderPath = songsFolderPath
        self.date = datetime.datetime.now()

        if songsFolderPath:
            self.initializeDirectory(songsFolderPath)
    
    def initializeDirectory(self, songsFolderPath):
        self.hashDict = {}
        self.songsFolderPath = songsFolderPath

        beatmapFolderPathList = [f.path for f in os.scandir(self.songsFolderPath) if f.is_dir()]
        for beatmapFolderPath in beatmapFolderPathList:
            beatmapPathList = [f.path for f in os.scandir(beatmapFolderPath) if f.name.endswith(".osu")]
            for beatmapPath in beatmapPathList:
                # thank you slider!
                with open(beatmapPath, 'rb') as f:
                    data = f.read()
                    beatmap_md5 = md5(data).hexdigest()
                    self.hashDict[beatmap_md5] = beatmapPath
        
    def search(self, beatmap_hash):
        if beatmap_hash in self.hashDict:
            return self.hashDict[beatmap_hash]
        else:
            return None
    
    def update(self, songsFolderPath=None):
        if songsFolderPath and songsFolderPath != self.songsFolderPath:
            self.initializeDirectory(songsFolderPath)
        else:
            beatmapFolderPathList = [f.path for f in os.scandir(self.songsFolderPath)\
                                     if f.is_dir() and os.path.getmtime(f.path) > self.date.timestamp()]
            for beatmapFolderPath in beatmapFolderPathList:
                beatmapPathList = [f.path for f in os.scandir(beatmapFolderPath) if f.name.endswith(".osu")]
                for beatmapPath in beatmapPathList:
                    with open(beatmapPath, 'rb') as f:
                        data = f.read()
                        beatmap_md5 = md5(data).hexdigest()
                        self.hashDict[beatmap_md5] = beatmapPath

        self.date = datetime.datetime.now()
    
    def exportToCache(self, fileName='beatmaphashes.dat'):
        with open(fileName, 'wb') as file:
            pickle.dump(self, file)

