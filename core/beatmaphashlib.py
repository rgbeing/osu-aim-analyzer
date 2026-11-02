import os
import datetime
import pickle
from hashlib import md5

class SongsFolderLibrary:
    def __init__(self, songsFolderPath=None, autoProcess=False):
        self.hashDict = {}
        self.songsFolderPath = songsFolderPath
        self.date = datetime.datetime.now()

        if songsFolderPath and autoProcess:
            self.initializeWholeDirectory(songsFolderPath)

    def setDateAsNow(self):
        self.date = datetime.datetime.now()

    def _resolve_lazer_files_dir(self, path):
        if not path:
            return None
        # Check if path is ~/.local/share/osu or ~/.local/share/osu/files or ~/.local/share/osu/Songs
        candidates = [
            path,
            os.path.join(path, "files"),
            os.path.join(os.path.dirname(path.rstrip("/")), "files")
        ]
        for c in candidates:
            if os.path.basename(c.rstrip("/")) == "files" and os.path.isdir(c):
                # Verify it looks like lazer hashed file store (contains hex subdirs like '0', '1', 'a', etc.)
                if os.path.isdir(os.path.join(c, "0")) and os.path.isdir(os.path.join(c, "a")):
                    return c
        return None

    def returnBeatmapsetList(self, update=False):
        if self.songsFolderPath:
            lazer_files = self._resolve_lazer_files_dir(self.songsFolderPath)
            if lazer_files:
                # Return the 16 top-level hex directories (0..f) so the progress bar works smoothly
                return [f.path for f in os.scandir(lazer_files) if f.is_dir()]
            if update:
                return [f.path for f in os.scandir(self.songsFolderPath)\
                        if f.is_dir() and os.path.getmtime(f.path) > self.date.timestamp()]
            else:
                return [f.path for f in os.scandir(self.songsFolderPath) if f.is_dir()]
        else:
            return None

    def _process_lazer_bucket(self, bucketPath, min_mtime=0):
        for sub in os.scandir(bucketPath):
            if not sub.is_dir():
                continue
            for f in os.scandir(sub.path):
                if not f.is_file():
                    continue
                try:
                    st = f.stat()
                    if min_mtime and st.st_mtime <= min_mtime:
                        continue
                    if st.st_size < 50 or st.st_size > 10_000_000:
                        continue
                    with open(f.path, 'rb') as fp:
                        head = fp.read(25)
                        if b'osu file format' in head:
                            fp.seek(0)
                            beatmap_md5 = md5(fp.read()).hexdigest()
                            self.hashDict[beatmap_md5] = f.path
                except Exception:
                    pass

    def processEachBeatmapset(self, beatmapFolderPath):
        lazer_files = self._resolve_lazer_files_dir(self.songsFolderPath)
        if lazer_files and os.path.dirname(beatmapFolderPath.rstrip("/")) == lazer_files.rstrip("/"):
            self._process_lazer_bucket(beatmapFolderPath)
            return

        beatmapPathList = [f.path for f in os.scandir(beatmapFolderPath) if f.name.endswith(".osu")]
        for beatmapPath in beatmapPathList:
            with open(beatmapPath, 'rb') as f:
                data = f.read()
                beatmap_md5 = md5(data).hexdigest()
                self.hashDict[beatmap_md5] = beatmapPath
    
    def initializeWholeDirectory(self, songsFolderPath):
        self.hashDict = {}
        self.songsFolderPath = songsFolderPath

        beatmapFolderPathList = self.returnBeatmapsetList(update=False) or []
        for beatmapFolderPath in beatmapFolderPathList:
            self.processEachBeatmapset(beatmapFolderPath)
        
    def search(self, beatmap_hash):
        if beatmap_hash in self.hashDict:
            return self.hashDict[beatmap_hash]
        else:
            return None
    
    def update(self, songsFolderPath=None):
        if songsFolderPath and songsFolderPath != self.songsFolderPath:
            self.initializeWholeDirectory(songsFolderPath)
        else:
            lazer_files = self._resolve_lazer_files_dir(self.songsFolderPath)
            if lazer_files:
                min_mtime = self.date.timestamp()
                for bucket in os.scandir(lazer_files):
                    if bucket.is_dir():
                        self._process_lazer_bucket(bucket.path, min_mtime=min_mtime)
            else:
                beatmapFolderPathList = [f.path for f in os.scandir(self.songsFolderPath)\
                                         if f.is_dir() and os.path.getmtime(f.path) > self.date.timestamp()]
                for beatmapFolderPath in beatmapFolderPathList:
                    self.processEachBeatmapset(beatmapFolderPath)

        self.setDateAsNow()
    
    def exportToCache(self, fileName='beatmaphashes.dat'):
        with open(fileName, 'wb') as file:
            pickle.dump(self, file)
