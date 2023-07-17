import sys, os
sys.path.append(os.path.dirname(__file__))

from osrparse import Replay
from osrparse.utils import Key
import osuparse

from ReplayFrame import ReplayFrame

from utilFunctions import *

def calculateHitPlace(replayPath, mapPath):
    ## Load a map
    beatmap = osuparse.beatmapparser.BeatmapParser()
    beatmap.parseFile(mapPath)
    beatmap.build_beatmap()
    hitObjects = beatmap.beatmap['hitObjects']

    # only for those mysterious things...
    firstObjectTime = hitObjects[0]['startTime']
    firstBPM = beatmap.beatmap['timingPoints'][0]['bpm']

    # Load a replay
    replay = Replay.from_path(replayPath)
    frames = []
    t = 0
    #t = max(0, int(firstObjectTime - 8 * 60000 / firstBPM)) # ??? mysterious
    for frame in replay.replay_data:
        t += frame.time_delta
        frames.append(ReplayFrame(frame, t))

    # debug purpose
    #for frame in frames:
    #    print("Time {}: Delta {}, ({}, {}), Key {}".format(frame.time, frame.time_delta, frame.x, frame.y, frame.keys))

    frames = sorted(frames)

    ## Retrieve mods info of the replay
    mods = replay.mods
    replayHR = bool(mods & (1 << 4) > 0)
    replayEZ = bool(mods & (1 << 1) > 0)

    ## Calculate OD and CS of the replay
    beatmapOD, beatmapCS, beatmapAR = map(
        float, (beatmap.beatmap['OverallDifficulty'], beatmap.beatmap['CircleSize'], beatmap.beatmap['ApproachRate'])
        )
    hitWindow, circleSize, approachRate = None, None, beatmapAR
    if replayHR:
        hitWindow = 200 - 10 * min(beatmapOD, 10) * 1.4
        circleSize = 54.4 - 4.48 * min(beatmapCS, 10) * 1.3
        approachRate *= 1.4
    elif replayEZ:
        hitWindow = 200 - 10 * beatmapOD / 2
        circleSize = 54.4 - 4.48 * beatmapCS / 2
        approachRate /= 2
    else:
        hitWindow = 200 - 10 * beatmapOD
        circleSize = 54.4 - 4.48 * beatmapCS
    
    beatmap.beatmap['replayApproachRate'] = approachRate
    beatmap.beatmap['replayCircleSize'] = circleSize

    # Reach a verdict on each note (except spinners)
    frameLastVerdicted = -1
    frameMaxTime = frames[-1].time
    hitFrames = []

    for obj in hitObjects:
        hitFlag, hitAttemptedFlag = False, False

        # if the replay is HR, flip the position of each object by x-axis
        if replayHR:
            obj['position'][1] = 384 - obj['position'][1]

        # spinners are passed
        if obj['object_name'] == 'spinner':
            hitFrames.append(None)
            obj['hitTime'] = None
            obj['hitPosition'] = None
            continue

        # calculate the hit window
        hitWindowStartTime = obj['startTime'] - hitWindow
        hitWindowEndTime = None
        if obj['object_name'] == 'slider':
            hitWindowEndTime = obj['end_time']
        else:
            hitWindowEndTime = obj['startTime'] + hitWindow

        # stop if there is no more frame
        if frameMaxTime < hitWindowStartTime:
            break

        # search after last object
        frameNo = frameLastVerdicted + 1

        # fast-forward until the hit window begins
        while frames[frameNo].time < hitWindowStartTime and frameNo < len(frames):
            frameNo += 1
        if frameNo == len(frames):
            break

        # main logic
        # There is a problem of stack leniency, but ??
        hitFrameNo = None
        while frames[frameNo].time <= hitWindowEndTime and frameNo < len(frames):
            thisFrame = frames[frameNo]
            lastKey = frames[frameNo-1].keys if frameNo >= 0 else Key(0)
            pressedKey = getKey(lastKey, thisFrame.keys)

            if pressedKey > 0:
                distancePressedTime = distance2D(obj['position'][0], obj['position'][1], thisFrame.x, thisFrame.y)
                if distancePressedTime <= circleSize:
                    hitFlag, hitAttemptedFlag = True, True
                    hitFrameNo = frameNo
                    frameLastVerdicted = frameNo
                    break
                elif distancePressedTime <= circleSize * 2:
                    if hitAttemptedFlag == False:
                        hitAttemptedFlag = True
                        hitFrameNo = frameNo
                        frameLastVerdicted = frameNo
                    # choose near one
                    else:
                        if distancePressedTime < distance2D(obj['position'][0], obj['position'][1], frames[hitFrameNo].x, frames[hitFrameNo].y):
                            hitFrameNo = frameNo
                            frameLastVerdicted = frameNo

            frameNo += 1
        
        if hitFlag == True or hitAttemptedFlag == True:
            hitFrames.append(hitFrameNo)
            obj['hitTime'] = frames[hitFrameNo].time
            obj['hitPosition'] = (frames[hitFrameNo].x, frames[hitFrameNo].y)
        else:
            hitFrames.append(None)
            obj['hitTime'] = None
            obj['hitPosition'] = None
    
    return beatmap.beatmap

