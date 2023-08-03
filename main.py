import sys, os
import traceback
import json
import pickle
import http.client

from osrparse import Replay

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QDialog, QMessageBox
from PyQt6.QtGui import QIcon, QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from MainWindow import Ui_MainWindow
from ResultWindow import Ui_ResultWindow

import core.analyze as analyzer
import core.hitCalculator as calculator
from core.beatmaphashlib import SongsFolderLibrary
from version import *

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, obj=None, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.setWindowTitle("osu! Aim Analyzer")
        self.setWindowIcon(QIcon("assets/icon.png"))

        # load settings.json
        settingsJson = self.loadSettingsJSON()
        if self.songsFolderLine and "songsFolder" in settingsJson:
            self.songsFolderLine.setText(settingsJson["songsFolder"])
        self.replayFolderPath = settingsJson["replaysFolder"] if ("replaysFolder" in settingsJson) else "c:\\"
        
        # load beatmaphashes.dat if it exists
        self.beatmapHashLib: SongsFolderLibrary | None = self.loadLibraryPickle()

        # load songs folder
        self.songsFolderBrowse.clicked.connect(self.getSongsFolder)
        self.songsFolderLoadButton.clicked.connect(self.getLibraryFromLine)

        # replays & maps line
        self.replayLine_1.setReadOnly(True)
        self.replayLine_2.setReadOnly(True)
        self.replayLine_3.setReadOnly(True)
        self.replayLine_4.setReadOnly(True)
        self.replayLine_5.setReadOnly(True)

        self.checkBox_1.setCheckState(Qt.CheckState.Checked)

        self.replayBrowse_1.clicked.connect(lambda : self.getFileReplay(1))
        self.mapBrowse_1.clicked.connect(lambda: self.getFileMap(1))
        self.replayBrowse_2.clicked.connect(lambda : self.getFileReplay(2))
        self.mapBrowse_2.clicked.connect(lambda: self.getFileMap(2))
        self.replayBrowse_3.clicked.connect(lambda : self.getFileReplay(3))
        self.mapBrowse_3.clicked.connect(lambda: self.getFileMap(3))
        self.replayBrowse_4.clicked.connect(lambda : self.getFileReplay(4))
        self.mapBrowse_4.clicked.connect(lambda: self.getFileMap(4))
        self.replayBrowse_5.clicked.connect(lambda : self.getFileReplay(5))
        self.mapBrowse_5.clicked.connect(lambda: self.getFileMap(5))

        self.replaysLoadButton.clicked.connect(self.load)

        # update checking
        if self.isThisVersionLatest():
            self.updateCheckLabel.setText("This is the latest version.")
        else:
            self.updateCheckLabel.setText("<span style=\" color:#aa0000;\"><b>New version has been released!</b></span> Visit <a href=https://github.com/rgbeing/osu-aim-analyzer>github.com/rgbeing/osu-aim-analyzer</a> to download it.")
            self.updateCheckLabel.setOpenExternalLinks(True)

    def newWin(self):
        w = ResultWindow(None, None)
        w.show()

    def loadSettingsJSON(self):
        data = None
        if os.path.exists("settings.json"):
            with open("settings.json", 'r') as file:
                data = json.load(file)
        
        return data
    
    def getSongsFolder(self):
        dname = QFileDialog.getExistingDirectory(self, 'Open folder', 'c:\\')
        if dname:
            self.songsFolderLine.setText(dname)
    
    def loadLibraryPickle(self, pathname='beatmaphashes.dat'):
        hashlib = None
        if os.path.exists(pathname):
            with open(pathname, 'rb') as file:
                hashlib = pickle.load(file)
        
        return hashlib
    
    def getLibraryFromLine(self):
        if self.beatmapHashLib and self.beatmapHashLib.songsFolderPath == self.songsFolderLine.text():
            # no need to build the library from the scratch
            self.beatmapHashLib.update()
            self.songsFolderProgressBar.setValue(100)
        else:
            library = SongsFolderLibrary(songsFolderPath=self.songsFolderLine.text(), autoProcess=False)
            beatmapFolderPathList = library.returnBeatmapsetList()
            lenList = len(beatmapFolderPathList)

            for idx, beatmapFolderPath in enumerate(beatmapFolderPathList):
                library.processEachBeatmapset(beatmapFolderPath)
                self.songsFolderProgressBar.setValue(int((idx + 1) * 100 / lenList))
            library.setDateAsNow()

            library.exportToCache()
            self.beatmapHashLib = library

    def getFileReplay(self, i):
        fname = QFileDialog.getOpenFileName(self, 'Open file', self.replayFolderPath, "osu! replay files (*.osr)")
        if fname[0]:
            eval("self.replayLine_" + str(i) + ".setText(fname[0])")
            #self.replays[i-1] = fname[0]

    def getFileMap(self, i):
        fname = QFileDialog.getOpenFileName(self, 'Open file', 'c:\\', "osu! map files (*.osu)")
        if fname[0]:
            eval("self.mapLine_" + str(i) + ".setText(fname[0])")
            #self.maps[i-1] = fname[0]

    def extractHashFromReplay(self, replayPath):
        return Replay.from_path(replayPath).beatmap_hash
    
    def loadSlot(self, i):
        replayPath = (getattr(self, "replayLine_" + str(i))).text()
        mapPath = (getattr(self, "mapLine_" + str(i))).text()

        if not mapPath:
            try:
                mapPath = self.beatmapHashLib.search(self.extractHashFromReplay(replayPath))
                if not mapPath:
                    raise Exception("Error occured auto-finding the corresponding map for the slot #{}".format(i))
            except Exception as e:
                raise

        res = calculator.calculateHitPlace(replayPath, mapPath)
        #res = calculator.calculateHitPlace(self.replays[i-1], self.maps[i-1])

        slotRawResultList = []
        slotRawResultList.append(">>>>> Slot {} <<<<<".format(i))
        for obj in res['hitObjects']:
            if obj['object_name'] == 'spinner':
                slotRawResultList.append("Object: spinner\tPressed: None")
            else:
                if ('hitTime' in obj) and obj['hitTime']:
                    slotRawResultList.append("Time {} - Object: ({}, {})\tPressed: ({}, {}) @ {}".format(obj['startTime'], obj['position'][0], obj['position'][1], obj['hitPosition'][0], obj['hitPosition'][1], obj['hitTime']))
                else:
                    slotRawResultList.append("Time {} - Object: ({}, {})\tPressed: Not Pressed".format(obj['startTime'], obj['position'][0], obj['position'][1]))
        
        return (res, slotRawResultList)

    def load(self):
        self.progressBar.setValue(0)

        try:
            # parse raw results
            self.results = []
            self.rawResultList = []

            for i in range(1, 6):
                if eval("self.checkBox_" + str(i) + ".isChecked()") == True: # if self.checkBox_i.isChecked():
                    slotResult = self.loadSlot(i)
                    self.results.append(slotResult[0])
                    self.rawResultList += slotResult[1]
                self.progressBar.setValue(int(i * 100 / 20))
            
            self.rawResult = '\n'.join(self.rawResultList)
            self.progressBar.setValue(33)

            skewed_data = analyzer.explainByCoordinates(self.results)
            skewed_models = analyzer.analyzeByOLS(skewed_data, addConstant=True)
            self.progressBar.setValue(66)
            
            rotated_data = analyzer.explainByDirections(self.results)
            rotated_models = analyzer.analyzeByOLS(rotated_data, addConstant=True)
            self.progressBar.setValue(100)

            dlg = ResultWindow(skewed_models, rotated_models, self.rawResult)
            dlg.exec()
        
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText("Error occured! \n")
            msg.setInformativeText(traceback.format_exc())
            msg.setWindowTitle("Error")
            msg.exec()
    
    def isThisVersionLatest(self):
        host = "github.com"
        conn = http.client.HTTPSConnection(host)
        latest_version = VERSION

        try:
            conn.request("GET", "/rgbeing/osu-aim-analyzer/releases/latest")
            response = conn.getresponse()
            loc = response.headers["Location"]
            latest_version = loc.split('/')[-1]
        except:
            pass
        
        return (VERSION == latest_version)
        

class ResultWindow(QDialog, Ui_ResultWindow):
    def __init__(self, modelsSkewed, modelsRotated, rawResult, parent=None, *args, obj=None, **kwargs):
        super(ResultWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.setWindowTitle("osu! Aim Analyzer: Result Window")
        self.setWindowIcon(QIcon("assets/icon.png"))

        # Raw tab
        self.rawText.setText(rawResult)
        self.rawText.setReadOnly(True)
        self.rawText.setFont(QFont("Courier New"))

        # Rotatedness tab
        self.rotateLayout.setStretchFactor(self.rotatednessScrollArea, 3)
        self.rotateLayout.setStretchFactor(self.rotateGraphLayout, 2)

        ## Rotatedness
        rotatednessParams = modelsRotated[0].fit().params
        rotatedDegree = round(rotatednessParams[0] * 180 / 3.1415, 4)
        rotatedDirection = "clockwise" if rotatedDegree > 0 else "anticlockwise"
        self.rotatednessResult.setText("Rotated <em>{}</em> <strong>{}</strong>°".format(rotatedDirection, abs(rotatedDegree)))

        rotatednessPValues = modelsRotated[0].fit().pvalues
        if rotatednessPValues[0] < 0.05:
            self.rotatednessResult.setStyleSheet("background-color:lightgreen")
            self.rotatednessResult.setToolTip("significant; recommend to follow")
        else:
            self.rotatednessResult.setStyleSheet("background-color:lightpink")
            self.rotatednessResult.setToolTip("insignificant; recommend to disregard")

        ## Graph
        rotatePlot = MplCanvas(self, width=5, height=4, dpi=100)
        analyzer.plotDirectionsDiagnosis(modelsRotated, rotatePlot.axes)
        rotatePlot.axes.set_xlim([-50, 600])
        rotatePlot.axes.set_ylim([-200, 450])
        rotatePlot.axes.set_aspect('equal')

        self.rotateGraphLayout.addWidget(rotatePlot)
        self.rotateGraphLayout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)

        ## Raw Results
        self.rotatednessRawResults.setText(str(modelsRotated[0].fit().summary()))
        self.rotatednessRawResults.setReadOnly(True)

        # Wideness tab
        self.wideLayout.setStretchFactor(self.widenessScrollArea, 3)
        self.wideLayout.setStretchFactor(self.wideGraphLayout, 2)

        ## Graph
        widePlot = MplCanvas(self, width=5, height=4, dpi=100)
        analyzer.plotCoordinatesDiagnosis(modelsSkewed, widePlot.axes)
        widePlot.axes.set_xlim([-50, 600])
        widePlot.axes.set_ylim([-200, 450])
        widePlot.axes.set_aspect('equal')

        self.wideGraphLayout.addWidget(widePlot)
        self.wideGraphLayout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)

        ## Skewedness
        xSkewedParams = modelsSkewed[0].fit().params
        ySkewedParams = modelsSkewed[1].fit().params

        x0 = xSkewedParams[0]
        x256 = round(xSkewedParams[0] + 256 * xSkewedParams[1], 4)

        y0 = ySkewedParams[0]
        y192 = round(ySkewedParams[0] + 192 * ySkewedParams[1], 4)

        if y192 < 0:
            self.skewednessUpward.setText("skewed <em>upward</em> <strong>{}</strong> px".format(-y192))
        else:
            self.skewednessUpward.setText("skewed <em>downward</em> <strong>{}</strong> px".format(y192))
        
        if x256 > 0:
            self.skewednessRightward.setText("skewed <em>rightward</em> <strong>{}</strong> px".format(x256))
        else:
            self.skewednessRightward.setText("skewed <em>leftward</em> <strong>{}</strong> px".format(-x256))
        
        skewednessRightwardPValue = (modelsSkewed[0].fit().pvalues)[0]
        skewednessUpwardPValue = (modelsSkewed[1].fit().pvalues)[0]
        if skewednessRightwardPValue < 0.05:
            self.skewednessRightward.setStyleSheet("background-color:lightgreen")
            self.skewednessRightward.setToolTip("significant; recommend to follow")
        else:
            self.skewednessRightward.setStyleSheet("background-color:lightpink")
            self.skewednessRightward.setToolTip("insignificant; recommend to disregard")
        if skewednessUpwardPValue < 0.05:
            self.skewednessUpward.setStyleSheet("background-color:lightgreen")
            self.skewednessUpward.setToolTip("significant; recommend to follow")
        else:
            self.skewednessUpward.setStyleSheet("background-color:lightpink")
            self.skewednessUpward.setToolTip("insignificant; recommend to disregard")
        
        ## Wideness
        width = 512 * (1 + xSkewedParams[1])
        height = 384 * (1 + ySkewedParams[1])

        horizontalAim = "Overaim" if width > 512 else "Underaim"
        verticalAim = "Overaim" if height > 384 else "Underaim"

        self.widenessHorizontal.setText("Horizontally <em>{}</em> <strong>{}</strong> %".format(horizontalAim, round(width/512 * 100, 2)))
        self.widenessVertical.setText("Vertically <em>{}</em> <strong>{}</strong> %".format(verticalAim, round(height/384 * 100, 2)))

        widenessHorizontalPValue = (modelsSkewed[0].fit().pvalues)[1]
        widenessVerticalPValue = (modelsSkewed[1].fit().pvalues)[1]
        if widenessHorizontalPValue < 0.05:
            self.widenessHorizontal.setStyleSheet("background-color:lightgreen")
            self.widenessHorizontal.setToolTip("significant; recommend to follow")
        else:
            self.widenessHorizontal.setStyleSheet("background-color:lightpink")
            self.widenessHorizontal.setToolTip("insignificant; recommend to disregard")
        if widenessVerticalPValue < 0.05:
            self.widenessVertical.setStyleSheet("background-color:lightgreen")
            self.widenessVertical.setToolTip("significant; recommend to follow")
        else:
            self.widenessVertical.setStyleSheet("background-color:lightpink")
            self.widenessVertical.setToolTip("insignificant; recommend to disregard")
        
        ## Raw result
        widenessRawResultList = [">>>>> x-axis:"]
        widenessRawResultList.append(str(modelsSkewed[0].fit().summary()))
        widenessRawResultList.append(">>>>> y-axis:")
        widenessRawResultList.append(str(modelsSkewed[1].fit().summary()))

        self.widenessRawResults.setText('\n'.join(widenessRawResultList))
        self.widenessRawResults.setReadOnly(True)
    
        # default tab setting
        self.tabWidget.setCurrentIndex(0)

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)

app = QtWidgets.QApplication(sys.argv)

window = MainWindow()
window.show()
app.exec()
