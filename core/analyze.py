import sys, os
import datetime
sys.path.append(os.path.dirname(__file__))

import statsmodels.api as sm
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.transforms import Affine2D
import seaborn as sns

from osrparse import Replay, parse_replay_data
from osrparse.utils import Key
import osuparse

from ReplayFrame import ReplayFrame

from utilFunctions import *
from hitCalculator import *


def explainByCoordinates(parsedReplay):
    errors = ([], [])
    positions = ([], [])
    weights = []

    thisApproachTime = approachTime(parsedReplay['replayApproachRate'])
    thisCircleSize = parsedReplay['replayCircleSize']
    hitObjects = parsedReplay['hitObjects']

    for i in range(len(hitObjects)):
        prevObj, curObj = hitObjects[i-1], hitObjects[i]
        # only circles are analysed
        if curObj['object_name'] != 'circle':
            continue
        # interval is too long to analyze
        if curObj['startTime'] - prevObj['startTime'] > 2000:
            continue
        # doubted to be a stream (distance is less than 2 * circle-diameter)
        if distance2D(prevObj['position'][0], prevObj['position'][1], curObj['position'][0], curObj['position'][1]) < thisCircleSize * 4:
            continue
        # the circle was not hit
        if curObj['hitTime'] == None:
            continue

        intervalVelocity = distance2D(prevObj['position'][0], prevObj['position'][1], curObj['position'][0], curObj['position'][1])\
            / (curObj['startTime'] - prevObj['startTime'])
        approachVelocity = distance2D(prevObj['position'][0], prevObj['position'][1], curObj['position'][0], curObj['position'][1])\
            / thisApproachTime
        weights.append(max(intervalVelocity, approachVelocity))
        
        positions[0].append(curObj['position'][0])
        positions[1].append(curObj['position'][1])

        errors[0].append(curObj['hitPosition'][0] - curObj['position'][0])
        errors[1].append(curObj['hitPosition'][1] - curObj['position'][1])
        
    return ((errors[0], positions[0]), (errors[1], positions[1]))

def explainByVectors(parsedReplay):
    errors = ([], [])
    vectors = ([], [])
    weights = []

    thisApproachTime = approachTime(parsedReplay['replayApproachRate'])
    thisCircleSize = parsedReplay['replayCircleSize']
    hitObjects = parsedReplay['hitObjects']

    for i in range(1, len(hitObjects)):
        prevObj, curObj = hitObjects[i-1], hitObjects[i]
        # only circles are analysed
        if prevObj['object_name'] != 'circle' or curObj['object_name'] != 'circle':
            continue
        # interval is too long to analyze
        if curObj['startTime'] - prevObj['startTime'] > 2000:
            continue
        # doubted to be a stream (distance is less than 2 * circle-diameter)
        if distance2D(prevObj['position'][0], prevObj['position'][1], curObj['position'][0], curObj['position'][1]) < thisCircleSize * 4:
            continue
        # the circle was not hit
        if curObj['hitTime'] == None:
            continue

        intervalVelocity = distance2D(prevObj['position'][0], prevObj['position'][1], curObj['position'][0], curObj['position'][1])\
            / (curObj['startTime'] - prevObj['startTime'])
        approachVelocity = distance2D(prevObj['position'][0], prevObj['position'][1], curObj['position'][0], curObj['position'][1])\
            / thisApproachTime
        weights.append(max(intervalVelocity, approachVelocity))
        
        vectors[0].append(curObj['position'][0] - prevObj['position'][0])
        vectors[1].append(curObj['position'][1] - prevObj['position'][1])

        errors[0].append(curObj['hitPosition'][0] - curObj['position'][0])
        errors[1].append(curObj['hitPosition'][1] - curObj['position'][1])
        
    return ((errors[0], vectors[0]), (errors[1], vectors[1]))

def explainByDirections(parsedReplay):
    aimDirections = []
    actualDirections = []
    weights = []

    thisApproachTime = approachTime(parsedReplay['replayApproachRate'])
    thisCircleSize = parsedReplay['replayCircleSize']
    hitObjects = parsedReplay['hitObjects']

    for i in range(1, len(hitObjects)):
        prevObj, curObj = hitObjects[i-1], hitObjects[i]
        # only circles are analysed
        if prevObj['object_name'] != 'circle' or curObj['object_name'] != 'circle':
            continue
        # interval is too long to analyze
        if curObj['startTime'] - prevObj['startTime'] > 2000:
            continue
        # doubted to be a stream (distance is less than 2 * circle-diameter)
        if distance2D(prevObj['position'][0], prevObj['position'][1], curObj['position'][0], curObj['position'][1]) < thisCircleSize * 4:
            continue
        # both of the current and previous circle must be hit
        if curObj['hitTime'] == None or prevObj['hitTime'] == None:
            continue

        intervalVelocity = distance2D(prevObj['position'][0], prevObj['position'][1], curObj['position'][0], curObj['position'][1])\
            / (curObj['startTime'] - prevObj['startTime'])
        approachVelocity = distance2D(prevObj['position'][0], prevObj['position'][1], curObj['position'][0], curObj['position'][1])\
            / thisApproachTime
        weights.append(max(intervalVelocity, approachVelocity))
        
        actualDirections.append(vectorToAngle(\
            curObj['position'][0] - prevObj['position'][0], curObj['position'][1] - prevObj['position'][1]\
            ))

        aimDirections.append(vectorToAngle(\
            curObj['hitPosition'][0] - prevObj['hitPosition'][0], curObj['hitPosition'][1] - prevObj['hitPosition'][1]\
            ))
        
    return [(aimDirections, actualDirections)]

def analyzeByOLS(data, addConstant=True):
    models = []

    for datum in data:
        if addConstant:
            model = sm.OLS(datum[0], sm.add_constant(datum[1]))
        else:
            model = sm.OLS(datum[0], datum[1])
        models.append(model)

    return models

def analyzeByOLSDistance(data):
    dist = []
    err = []
    for i in range(len(data[0][0])):
        vx, vy = data[0][1][i], data[1][1][i]
        ex, ey = data[0][0][i], data[1][0][i]
        dist.append(distance2D(0, 0, vx, vy))
        err.append(distance2D(0, 0, ex, ey))
    
    model = sm.OLS(err, dist)
    return model

def cooksDistance(models):
    cooksX = models[0].get_influence().cooks_distance
    cooksY = models[1].get_influence().cooks_distance

    return (cooksX, cooksY)

def plotCoordinatesDiagnosis(models, ax=None):
    x_lb, estimated_w = (models[0].fit().params)[0], 512 + 512 * (models[0].fit().params)[1]
    y_lb, estimated_h = -((models[1].fit().params)[0]) - 384 * (models[1].fit().params)[1],\
        384 + 384 * (models[1].fit().params)[1]
    
    #fig, ax = plt.subplots()
    ax.axis('off')
    ax.add_patch(Rectangle((0, 0), 512, 384, fill=False, edgecolor = 'deeppink'))
    ax.add_patch(Rectangle((x_lb, y_lb), estimated_w, estimated_h, fill=False, edgecolor = 'blue'))

    x_zero = -((models[0].fit().params)[0] / (models[0].fit().params)[1])
    y_zero = -((models[1].fit().params)[0] / (models[1].fit().params)[1])
    ax.plot([x_zero], [y_zero], marker="x")

    return ax

def plotDirectionsDiagnosis(models, ax=None):
    realPlayfield = Rectangle((0, 0), 512, 384, fill=False, edgecolor = 'deeppink')
    playerPlayfield = Rectangle((0, 0), 512, 384, fill=False, edgecolor = 'blue')

    transform = Affine2D().rotate_deg_around(256, 192, -(models[0].fit().params)[0] * 180 / 3.1415) + ax.transData
    playerPlayfield.set_transform(transform)

    ax.axis('off')
    ax.add_patch(realPlayfield)
    ax.add_patch(playerPlayfield)

    ax.plot([256], [192], marker='.', color='black')

    return ax
    
