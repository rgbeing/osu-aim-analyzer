import math

from osrparse.utils import Key

def getKey(last, current):
    res = Key(0)
    hasFlag = lambda t, k: (t & k) > 0

    if (not hasFlag(last, Key.M1) and hasFlag(current, Key.M1) and not hasFlag(current, Key.K1)):
        res |= Key.M1
    if (not hasFlag(last, Key.M2) and hasFlag(current, Key.M2) and not hasFlag(current, Key.K2)):
        res |= Key.M2
    if (not hasFlag(last, Key.K1) and hasFlag(current, Key.K1)):
        res |= Key.K1 | Key.M1
    if (not hasFlag(last, Key.K2) and hasFlag(current, Key.K2)):
        res |= Key.K2 | Key.M2
    return res

def distance2D(x1, y1, x2, y2):
    return math.sqrt(math.pow((x1-x2), 2) + math.pow((y1-y2), 2))

def approachTime(ar):
    if (ar <= 5):
        return 1200 - 600 * (ar - 5) / 5
    else:
        return 1200 - 750 * (ar - 5) / 5
    
def vectorToAngle(x, y):
    r = math.sqrt(x*x + y*y)
    cos_theta = x / r
    theta = math.acos(cos_theta)
    if y < 0:
        theta *= -1
    
    return theta