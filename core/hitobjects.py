from enum import Enum

class SliderType(Enum):
    Linear = 0
    Bezier = 1
    Circle = 2
    Catmull = 3

class HitObjects:
    pass

class Note(HitObjects):
    def __init__(self, parsedObj):
        self.time : int = parsedObj["startTime"]
        self.posX : int = parsedObj["position"][0]
        self.posY : int = parsedObj["position"][1]
        self.hit : bool = False
        self.hitX : int = None
        self.hitY : int = None

class Slider(HitObjects):
    def __init__(self, parsedObj):
        self.time : int = parsedObj["startTime"]
        self.type : SliderType = None
        self.posX : int = parsedObj["position"][0]
        self.posY : int = parsedObj["position"][1]
        self.repeatCount : int = parsedObj["repeatCount"]
        self.endTime : int = parsedObj["end_time"]
        self.endX : int = parsedObj["end_position"][0]
        self.endY : int = parsedObj["end_position"][1]
        self.adjustedEndX : int = None
        self.adjustedEndY : int = None
        self.points : list = parsedObj["points"]