from PyQt5.QtCore import *
import time
import sys
import subprocess
import re
import shutil
import pathlib
import utils

VIDEO_EXTENSIONS = [".mp4",".avi",".mkv",".3gp", ".mov"] #most used video extensions

INFO = 0  #loglevel
ERROR = 1 #loglevel

class Worker(QObject):
    finished = pyqtSignal() #taskPerformer onThreadFinished() will be called
    emitLog = pyqtSignal(int, str) #emit log to taskPerformer (displayLog(i))
    emitProgress = pyqtSignal(int, int) #emit progress to taskPerformer

    continueWork = True
    totSize = processedSize = 0 # tot files size
    converted = copied = fails = 0

    def __init__(self, inputPath, outputPath, ffmpeg_opt, parent=None):
        super(Worker, self).__init__(parent)
        self.inputPath = pathlib.Path(inputPath)
        self.outputPath = pathlib.Path(outputPath)
        self.ffmpeg_opt = ffmpeg_opt

    @pyqtSlot()
    def operationRunner(self):
        #collecting and printing stats
        time_start = time.time() #start time
        t = time.localtime(time_start) #convert time_start in a tuple, for easily extracting hour, min, sec
        self.totSize = utils.getTotalSize(self.inputPath)
        self.thick = 100/self.totSize
        self.emitLog.emit(INFO, "Launched at %d:%02d:%02d\n" %(t.tm_hour, t.tm_min, t.tm_sec))
        self.emitLog.emit(INFO, "Input path: %s\n" % str(self.inputPath))
        self.emitLog.emit(INFO, "Total input size: %0.f MB\n" % round((self.totSize/(1024*1024.0)), 2))
        self.emitLog.emit(INFO, "Output path: %s\n" % str(self.outputPath))
        self.emitLog.emit(INFO, "ffmpeg options: %s\n" % str(self.ffmpeg_opt))
        self.emitLog.emit(INFO, "-------------------------------------------------------------\n")

        self.fileManager(self.inputPath, self.outputPath)

        self.emitLog.emit(INFO, "-------------------------- Done --------------------------\n")
        sec = time.time() - time_start
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        self.emitLog.emit(INFO, "Total time: %d:%02d:%02d sec - It's now safe to close this window.\n" %(h,m,s))
        self.emitLog.emit(INFO, "Processed: %d - copied files: %d - errors: %d" % (self.converted, self.copied, self.fails))
        self.finished.emit()


    @pyqtSlot(str)
    def termSignal(self, text):
        if text=="terminate":
            self.proc.terminate()
        self.finished.emit()


    #convert file only if it's a video, otherwise copy it
    #input_file: type(input_file) = type(output_file) = pathlib.Path
    def convert_or_copy(self, input_file, output_dir):
        if self.continueWork == False:
            return
        output_name = output_dir / input_file.name

        try:
            if input_file.suffix in VIDEO_EXTENSIONS:
                self.emitLog.emit(INFO, "Converson: %s " % str(input_file))
                self.processedSize += utils.convert_file(input_file, output_name, self.updProgress)
                self.converted +=1
            else:
                self.emitLog.emit(INFO, "Copy: %s " % str(input_file))
                self.processedSize += utils.copy(input_file, output_name, self.updProgress)
                self.copied +=1
        except Exception as e:
            self.emitLog.emit(INFO, "- Failed")
            self.emitLog.emit(ERROR, "&nbsp;&nbsp;&nbsp;&rarr; %s" % str(e))
            self.fails += 1
        else:
            self.emitLog.emit(INFO, "- OK\n")

    #rate: percentage of current file progress
    #fSize: current file size in bytes
    def updProgress(self, rate, fSize):
        #total progress = self.processedSize + current file processed bytes
        self.emitProgress.emit(round((100/self.totSize)*(self.processedSize+(fSize/100*rate))), rate)


    #scan all inputPath and perform operations
    def fileManager(self, inputPath, outputPath):
        if inputPath == outputPath:
            self.emitLog.emit(ERROR, "ERROR!: input path is the same as output path\n")
            return
        if self.continueWork == False:
            return
        if not outputPath.exists():
            self.emitLog.emit(INFO, "Creating dir: %s\n" % str(outputPath))
            outputPath.mkdir()
        #input is a file, need only to convert (or copy) to new location
        if inputPath.is_file():
            self.convert_or_copy(inputPath, outputPath)
        #input is a directory
        else:
            for item in inputPath.iterdir():
                if item.is_dir():
                    destin_dir = outputPath / item.name #path concatenation
                    self.fileManager(item, destin_dir)
                else:
                    self.convert_or_copy(item, outputPath)
