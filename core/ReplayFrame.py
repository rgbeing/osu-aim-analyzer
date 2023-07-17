from osrparse.utils import ReplayEventOsu

class ReplayFrame(ReplayEventOsu):
    time : int

    def __init__(self, replayObj, time):
        if replayObj is not None:
            for k, v in replayObj.__dict__.items():
                setattr(self, k, v)
            self.time = time

    def __repr__(self):
        return "TimeReplayEventOsu(time={}, time_delta={}, x={}, y={}, keys={})".format(
            self.time, self.time_delta, self.x, self.y, self.keys.__repr__()
        )
    
    def __eq__(self, other):
        return self.time == other.time
    
    def __lt__(self, other):
        return self. time < other.time
