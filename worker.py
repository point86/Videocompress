from PyQt5.QtCore import *
import time
import sys
import subprocess
import re
import shutil
import pathlib

VIDEO_EXTENSIONS = [".mp4",".avi",".mkv",".3gp"] #most used video extensions


class Worker(QObject):
    finished = pyqtSignal() #taskPerformer onThreadFinished() will be called
    emitLog = pyqtSignal(str) #emit log to taskPerformer (displayLog(i))
    emitProgress = pyqtSignal(int, int) #emit progress to taskPerformer
    #string format: Duration: 00:02:00.92, start: 0.000000, bitrate: 10156 kb/s
    durationRegex = re.compile("[ ]+Duration: (\d{2}):(\d{2}):(\d{2}.\d{2})")
    #string format: frame=  361 fps= 51 q=32.0 size=    1792kB time=00:00:12.04 bitrate=1219.0kbits/s speed=1.71x
    progressRegex = re.compile("frame=[ 0-9]+fps=[ 0-9\.]+q=[ 0-9\.\-]+L*size=[ 0-9]+[bBkKgGmM ]+time=(\d{2}):(\d{2}):(\d{2}.\d{2})")
    continueWork = True
    totSize = 0 # tot files size
    thick = 0
    processedSize = 0
    copied = 0
    converted = 0
    fails = 0

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
        self.totSize = self.getTotalSize(self.inputPath)
        self.thick = 100/self.totSize
        self.emitLog.emit("Launched at %d:%02d:%02d\n" %(t.tm_hour, t.tm_min, t.tm_sec))
        self.emitLog.emit("Input path: %s\n" % str(self.inputPath))
        self.emitLog.emit("Total input size: %0.f MB\n" % round((self.totSize/(1024*1024.0)), 2))
        self.emitLog.emit("Output path: %s\n" % str(self.outputPath))
        self.emitLog.emit("ffmpeg options: %s\n" % str(self.ffmpeg_opt))
        self.emitLog.emit("-------------------------------------------------------------\n")

        self.fileManager(self.inputPath, self.outputPath)

        self.emitLog.emit("-------------------------- Done --------------------------\n")
        sec = time.time() - time_start
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        self.emitLog.emit("Total time: %d:%02d:%02d sec - It's now safe to close this window.\n" %(h,m,s))
        self.emitLog.emit("Converted files: %d - copied files: %d - errors: %d" % (self.converted, self.copied, self.fails))
        self.finished.emit()


    @pyqtSlot(str)
    def termSignal(self, text):
        if text=="terminate":
            self.proc.terminate()
        self.finished.emit()

    #copy file inputPath to outputPath, calling callback every 250KB copied.
    #(250=trigger value)
    #https://hg.python.org/cpython/file/eb09f737120b/Lib/shutil.py#l215
    def copy(self, inputPath, outputPath):
        length = 16*1024
        trigger = 250*1024
        fileSize = inputPath.stat().st_size
        count = 0
        copied=0
        self.emitProgress.emit(round(100/self.totSize*self.processedSize), 0)
        fsrc = open(inputPath, 'rb')
        fdst = open(outputPath, 'wb')
        while 1:
            buf = fsrc.read(length)
            if not buf:
                break
            fdst.write(buf)
            copied += len(buf)
            count += len(buf)
            self.processedSize += len(buf)
            if count >= trigger:
                count = 0
                self.emitProgress.emit(round(100/self.totSize*self.processedSize), round(100/fileSize*copied))
        shutil.copymode(inputPath, outputPath, follow_symlinks=False)




    #convert file only if it's a video, otherwise copy it
    #input_file: type(input_file) = type(output_file) = pathlib.Path
    def convert_or_copy(self, input_file, output_dir):
        if self.continueWork == False:
            return
        output_name = output_dir / input_file.name
        self.emitProgress.emit(round(100/self.totSize*self.processedSize), 0)
        self.emitLog.emit("Processing: %s " % str(input_file))
        try:
            if input_file.suffix in VIDEO_EXTENSIONS:
                self.convert_file(input_file, output_name)
                self.converted += 1
            else:
                self.copy(input_file, output_name)
                self.copied += 1
        except Exception as e:
            self.emitLog.emit("- Failed\n   %s\n" % str(e))
            self.fails += 1
        else:
            self.emitLog.emit("- OK\n")
        finally:
            self.emitProgress.emit(round(100/self.totSize*self.processedSize), 100)



    #scan all inputPath and perform operations
    def fileManager(self, inputPath, outputPath):
        if inputPath == outputPath:
            self.emitLog.emit("ERROR!: input path is the same as output path\n")
            return
        if self.continueWork == False:
            return
        if not outputPath.exists():
            self.emitLog.emit("Creating dir: %s\n" % str(outputPath))
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

    def convert_file(self, input_name, output_name):
        if self.continueWork == False:
            return
        fileSize = input_name.stat().st_size
        cthick = 0
        progress=0
        length=0
        DQ="\""
        #ffmpeg: sane values are between 18 and 28
        #https://trac.ffmpeg.org/wiki/Encode/H.264
        #ffmpeg -i input.mp4 -c:v libx264 -crf 26 output.mp4
        self.proc = subprocess.Popen("ffmpeg -y -loglevel info -i " + DQ + str(input_name) + DQ + " -c:v libx264 -crf 26 " + DQ+str(output_name)+DQ,stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True)

        while True:
            #another way is to use ffmpeg -y -progress filename ....and parse filename, but there are the same info ffmpeg print to stderr.
            sys.stderr.flush()
            #read STDERR output (only for ffmpeg, because it have the option to send video output to stdout stream, so it uses stderr for logs.)
            line=self.proc.stderr.readline()
            p = re.match(self.progressRegex, line)
            if p is not None:
                #calculating current time interval
                hh=float(p.group(1)) #hours
                mm=float(p.group(2)) #mins
                ss=float(p.group(3)) #secs (floating point, ex: 21.95)
                progress=hh*3600+mm*60+ss
                self.emitProgress.emit(round(100/self.totSize*self.processedSize), self.thick*(self.processedSize+fileSize*(progress/duration)))
            else:
                #calculating total video time
                p=re.match(self.durationRegex,line)
                if p is not None:
                    hh=float(p.group(1)) #hours
                    mm=float(p.group(2)) #mins
                    ss=float(p.group(3)) #secs (floating point, ex: 21.95)
                    duration = hh*3600+mm*60+ss
                    cthick = 100/duration
            if self.proc.poll() == 0:
                break
            elif self.proc.poll()==1:
                raise Exception("ffmpeg exited with error converting %s." % str(input_name)) #TODO which error?
                break
        self.processedSize += fileSize

    def getTotalSize(self, inputPath): #type (inputPath) = <class pathlib>
        #inputPath is a file:
        size = 0
        if inputPath.is_file():
            return inputPath.stat().st_size
        #inputPath is a folder:
        for item in inputPath.iterdir():
            size += self.getTotalSize(item)
        return size
