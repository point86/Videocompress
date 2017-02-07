from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import sys
from worker import Worker

class TaskPerformer(QDialog):
    def __init__(self, inputPath, outputDir, ffmpeg_opt,  parent=None):
        super(TaskPerformer, self).__init__(parent)
        self.inputPath = inputPath
        self.outputDir = outputDir
        self.ffmpeg_opt = ffmpeg_opt
        #main layout (vertical)
        self.verticalLayout = QVBoxLayout(self)
        #log area
        self.logWindow = QPlainTextEdit(self)
        self.logWindow.setReadOnly(True)
        self.verticalLayout.addWidget(self.logWindow)

        #current video progress bar
        self.currProgBar = QProgressBar(self)
        self.verticalLayout.addWidget(self.currProgBar)
        self.currProgBar.setMinimum(0)
        self.currProgBar.setMaximum(100)
        #total files  progress bar
        self.totalProBar = QProgressBar(self)
        self.verticalLayout.addWidget(self.totalProBar)
        self.totalProBar.setMinimum(0)
        self.totalProBar.setMaximum(100)

        #buttons
        self.btt_ok = QPushButton("Ok")
        self.btt_cancel = QPushButton("Stop")
        self.hlayout = QHBoxLayout()
        self.hlayout.addStretch(1)
        self.hlayout.addWidget(self.btt_ok)
        self.hlayout.addWidget(self.btt_cancel)
        self.btt_ok.clicked.connect(self.close)
        self.btt_cancel.clicked.connect(self.cancel_btt)
        self.verticalLayout.addLayout(self.hlayout)

        self.setWindowTitle("Converting...\n")
        self.resize(400,350)



    def start_conversion(self):
        #thread that will perform all operations
        self.thread = QThread()
        #class that do the work
        self.obj = Worker(self.inputPath, self.outputDir, self.ffmpeg_opt)
        #connect signals
        self.obj.emitLog.connect(self.displayLog)
        self.obj.finished.connect(self.onThreadFinished)
        self.obj.emitProgress.connect(self.updateProgress)
        #move class obj to thread
        self.obj.moveToThread(self.thread)
        #when thread is started, call operationRunner
        self.thread.started.connect(self.obj.operationRunner)
        #starting the thread
        self.thread.start()
        self.btt_ok.setEnabled(False) #enabled in onThreadFinished
        #execute this window
        result = self.exec_()


    def updateProgress(self, total, current):
        self.currProgBar.setValue(current)
        self.totalProBar.setValue(total)

    def onThreadFinished(self):
        self.thread.quit()
        self.btt_ok.setEnabled(True)
        self.btt_cancel.setEnabled(False)
        

    def displayLog(self, i):
        self.logWindow.insertPlainText(i)

    def cancel_btt(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Warning")
        msg.setText("Press OK to close all pending operations.")
        msg.setStandardButtons(QMessageBox.Ok|QMessageBox.Cancel)
        v = msg.exec_()
        if v == QMessageBox.Ok:
            #appendPlainText: append a new paragraph to the end
            #insertPlainText: insert text to the end
            #self.logWindow.appendPlainText("Sending TERM signal...\n") #empty line before the text (so a new paragraph)
            self.obj.continueWork = False
            #sigterm signal
            if self.obj.proc.poll() == None:
                self.obj.proc.terminate()
            QMetaObject.invokeMethod(self.obj, 'termSignal', Qt.QueuedConnection, Q_ARG(str, "terminate"))
            self.logWindow.appendHtml("<font color=\"Red\">Sending TERM signal...\n")
