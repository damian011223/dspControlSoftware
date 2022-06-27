from time import time
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic

import sys
import os
from datetime import datetime

from visualizer import MidiVisualizer
from matplotlib.backends.backend_qtagg import (FigureCanvas,  NavigationToolbar2QT as NavigationToolbar)
from mido import MidiFile

#dsp interface
from asyncio.windows_events import NULL
from urllib.parse import MAX_CACHE_SIZE
from mido import MidiFile
from dsp_interface import ChannelHandler
from signal import signal, SIGINT
from multithread import Worker

#-----------------------------------------------------------------------

#-----------------------------------------------------------------------


class MainWindow(QMainWindow):


    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        uic.loadUi('steuerung.ui', self) # Load the .ui file
        #setup and load Midi Visualizer Widget
        self.fileList = []
        self.cbMidiFile.activated.connect(self.selectedFileChanged)
        ######
        self.midVis = MidiVisualizer()
        self.canvas = FigureCanvas(self.midVis.initFigure())
        self.canvas.setStyleSheet("background-color:transparent;")
        #self.canvas.si #set_size_inches(2, 3)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setVisible(False)
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        self.scrollArea = QScrollArea(self.midoVisualizerWidget)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea.setAlignment(Qt.AlignLeft)
        self.scrollArea.setWidget(self.canvas)
        self.scrollArea.widgetResizable = True
        self.scrollArea.setVisible(False)
        layout.addWidget(self.scrollArea)
        self.midoVisualizerWidget.setLayout(layout)
        #connections between buttons
        self.buttonOpenFile.clicked.connect(self.openNewFile) 
        self.buttonPlay.clicked.connect(self.playTrack)
        self.buttonStop.clicked.connect(self.stopTrack)
        self.adjustVolume.setMinimum(48)
        self.adjustVolume.setMaximum(127)
        self.adjustVolume.valueChanged.connect(self.setVolume)
        #load default values
        self.progressBar.setRange(0,0)
        #self.progressBar.hide()
        self.is_stopped = False
        #self.chHandler = ChannelHandler()
        #######
        #show main Window
        self.duration = 1
        self.startTime = time()
        self.fileList = []
        self.show()

        self.threadpool = QThreadPool()

    def selectedFileChanged(self):
            self.midVis.clearAll()
            self.hideMidiFile()
            self.progressBar.show()
            self.filename = self.fileList[self.cbMidiFile.currentIndex()]
            worker = Worker(self.loadFileThread)
            worker.signals.finished.connect(self.showMidiFile)
            # Execute worker
            self.threadpool.start(worker)

    def loadFileThread(self, progress_callback):
            trackCount = self.midVis.loadFile(self.filename)
            self.updateLog("Opening " + self.filename)
            figureSize = self.midVis.getSizeInPixels()
            self.canvas.resize(figureSize[0]-50,figureSize[1])

    def showMidiFile(self):
        self.scrollArea.setVisible(True)

    def hideMidiFile(self):
        self.scrollArea.setVisible(False)

    def openNewFile(self):
        self.filename, _ = QFileDialog.getOpenFileName(None, 'Open File', '.',"Midi Files (*.mid)")
        if self.filename:
            self.fileList.append(self.filename)
            self.cbMidiFile.addItem(os.path.basename(self.filename))
            self.cbMidiFile.setCurrentText(os.path.basename(self.filename))
            self.cbMidiFile.activated.emit(1)

            
    def playTrack(self):
        
        #load parameters
        self.is_stopped = False
        self.progressBar.setMaximum(self.midVis.getMessageCount())
        #create worker thread
        worker = Worker(self.playMidiFile)
        worker.signals.finished.connect(self.stopTrack)
        worker.signals.progress.connect(self.progress_fn)
        # Execute worker
        self.threadpool.start(worker)
        self.updateLog("Start playing File")        

    def stopTrack(self):
        self.is_stopped = True
        self.progressBar.setValue(0)
        self.updateLog("Stop playing track")

    def setVolume(self):
        #set global volume here
        newVolume = self.adjustVolume.value()
        #self.chHandler.setVolume(newVolume)
        self.updateLog("Volume is set to " + str(newVolume))

    def updateLog(self, message):
        now = datetime.now()
        self.logOutput.append(now.strftime("%H:%M:%S") + "  " + message + "\n")

    # thread functions
    def playMidiFile(self, progress_callback):
        #Playing the midi messages in seperate thread
        mid = MidiFile(self.filename)
        msgCounter = 0
        maxTones= 0 
        
        self.startTime = time()
        self.duration = self.midVis.totalTimeSeconds 
        
        
        print("Duration: " + str(self.duration))       
        
        for msg in mid.play():
            if not msg.is_meta:
                if self.is_stopped:
                    #stop all running tones
                    #----------------------
                    #self.chHandler.dspInterface.resetDSP()
                    #----------------------
                    return "Stopped"
                if not msg.is_cc():
                    if msg.type in ("note_on", "note_off"):# and msg.dict()["channel"] == 0:
                        if msg.type == "note_on":
                            #self.chHandler.startTone(msg.note, msg.velocity,  msg.dict()["channel"])
                            progress_callback.emit(msgCounter)
                            msgCounter += 1

                        #elif msg.type  == "note_off":
                            #self.chHandler.stopTone(msg.note, msg.dict()["channel"])
                        #maxTones = max(maxTones, len(self.chHandler.tones))
        #self.stopTrack()
        return "Done."

    # thread signal outputs
    def progress_fn(self, counter):
        #update progress bar
        self.progressBar.setValue(counter)

    def thread_complete(self, retValue):
        print("Thread completed, with " + retValue)
    

app = QApplication([])
window = MainWindow()
app.exec_()