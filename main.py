import sys
from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import QFileDialog, QDialog
from PyQt6.QtGui import QIcon, QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from MainWindow import Ui_MainWindow
from ResultWindow import Ui_ResultWindow

import core.analyze as analyzer
import core.hitCalculator as calculator

import numpy as np

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, obj=None, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.setWindowTitle("osu! Aim Analyzer")
        self.setWindowIcon(QIcon("assets/icon.png"))

        self.replays = [None] * 5
        self.maps = [None] * 5

        self.replayLine_1.setReadOnly(True)
        self.replayLine_2.setReadOnly(True)
        self.replayLine_3.setReadOnly(True)
        self.replayLine_4.setReadOnly(True)
        self.replayLine_5.setReadOnly(True)

        self.mapLine_1.setReadOnly(True)
        self.mapLine_2.setReadOnly(True)
        self.mapLine_3.setReadOnly(True)
        self.mapLine_4.setReadOnly(True)
        self.mapLine_5.setReadOnly(True)

        self.replayBrowse_1.clicked.connect(self.getFileReplay1)
        self.mapBrowse_1.clicked.connect(self.getFileMap1)
        self.replayBrowse_2.clicked.connect(self.newWin)

        self.loadButton.clicked.connect(self.load)

        ## Slot 2-5 is currently not available
        self.replayBrowse_2.setDisabled(True)
        self.replayBrowse_3.setDisabled(True)
        self.replayBrowse_4.setDisabled(True)
        self.replayBrowse_5.setDisabled(True)
        self.replayLine_2.setText("Not avaliable")
        self.replayLine_3.setText("Not avaliable")
        self.replayLine_4.setText("Not avaliable")
        self.replayLine_5.setText("Not avaliable")
        self.mapBrowse_2.setDisabled(True)
        self.mapBrowse_3.setDisabled(True)
        self.mapBrowse_4.setDisabled(True)
        self.mapBrowse_5.setDisabled(True)


    def newWin(self):
        w = ResultWindow(None, None)
        w.show()

    def getFileReplay1(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', 'c:\\', "osu! replay files (*.osr)")
        if fname[0]:
            self.replayLine_1.setText(fname[0])
            self.replays[0] = fname[0]
    
    def getFileMap1(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', 'c:\\', "osu! map files (*.osu)")
        if fname[0]:
            self.mapLine_1.setText(fname[0])
            self.maps[0] = fname[0]

    def load(self):
        self.progressBar.setValue(0)

        # parse raw results
        res = calculator.calculateHitPlace(self.replays[0], self.maps[0])
        rawResultList = []
        for obj in res['hitObjects']:
            if obj['object_name'] == 'spinner':
                rawResultList.append("Object: spinner\tPressed: None")
            else:
                if obj['hitTime']:
                    rawResultList.append("Time {} - Object: ({}, {})\tPressed: ({}, {}) @ {}".format(obj['startTime'], obj['position'][0], obj['position'][1], obj['hitPosition'][0], obj['hitPosition'][1], obj['hitTime']))
                else:
                    rawResultList.append("Time {} - Object: ({}, {})\tPressed: Not Pressed".format(obj['startTime'], obj['position'][0], obj['position'][1]))
        rawResult = '\n'.join(rawResultList)
        self.progressBar.setValue(33)

        skewed_data = analyzer.explainByCoordinates(res)
        skewed_models = analyzer.analyzeByOLS(skewed_data, addConstant=True)
        self.progressBar.setValue(66)
        
        rotated_data = analyzer.explainByDirections(res)
        rotated_models = analyzer.analyzeByOLS(rotated_data, addConstant=True)
        self.progressBar.setValue(100)

        #print(models[0].fit().summary())
        #print(models[1].fit().summary())

        dlg = ResultWindow(skewed_models, rotated_models, rawResult)
        dlg.exec()

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
        else:
            self.rotatednessResult.setStyleSheet("background-color:lightpink")

        ## Graph
        rotatePlot = MplCanvas(self, width=5, height=4, dpi=100)
        analyzer.plotDirectionsDiagnosis(modelsRotated, rotatePlot.axes)
        rotatePlot.axes.set_xlim([-50, 600])
        rotatePlot.axes.set_ylim([-50, 450])
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
        widePlot.axes.set_ylim([-50, 450])
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
        else:
            self.skewednessRightward.setStyleSheet("background-color:lightpink")
        if skewednessUpwardPValue < 0.05:
            self.skewednessUpward.setStyleSheet("background-color:lightgreen")
        else:
            self.skewednessUpward.setStyleSheet("background-color:lightpink")
        
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
        else:
            self.widenessHorizontal.setStyleSheet("background-color:lightpink")
        if widenessVerticalPValue < 0.05:
            self.widenessVertical.setStyleSheet("background-color:lightgreen")
        else:
            self.widenessVertical.setStyleSheet("background-color:lightpink")
        
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
