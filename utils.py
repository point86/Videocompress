import shutil
import subprocess
import re
import sys

#string format: Duration: 00:02:00.92, start: 0.000000, bitrate: 10156 kb/s
durationRegex = re.compile("[ ]+Duration: (\d{2}):(\d{2}):(\d{2}.\d{2})")
#string format: frame=  361 fps= 51 q=32.0 size=    1792kB time=00:00:12.04 bitrate=1219.0kbits/s speed=1.71x
progressRegex = re.compile("frame=[ 0-9]+fps=[ 0-9\.]+q=[ 0-9\.\-]+L*size=[ 0-9]+[bBkKgGmM ]+time=(\d{2}):(\d{2}):(\d{2}.\d{2})")

#TODO: preserve input file permissions? (output file permission are different)
#conversion of a read-only file will generate a non-readonly file.
def convert_file(input_name, output_name, updProgress):
    fileSize = input_name.stat().st_size
    # cthick = 0
    progress=0
    # length=0
    DQ="\""
    #ffmpeg: sane values are between 18 and 28
    #https://trac.ffmpeg.org/wiki/Encode/H.264
    #ffmpeg -i input.mp4 -c:v libx264 -crf 26 output.mp4
    proc = subprocess.Popen("ffmpeg -y -loglevel info -i " + DQ + str(input_name) + DQ + " -c:v libx264 -crf 26 " + DQ+str(output_name)+DQ,stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True)

    while True:
        #another way is to use ffmpeg -y -progress filename ....and parse filename, but there are the same info ffmpeg print to stderr.
        sys.stderr.flush()
        #read STDERR output (only for ffmpeg, because it have the option to send video output to stdout stream, so it uses stderr for logs.)
        line=proc.stderr.readline()
        p = re.match(progressRegex, line)
        if p is not None:
            #calculating current time interval
            hh=float(p.group(1)) #hours
            mm=float(p.group(2)) #mins
            ss=float(p.group(3)) #secs (floating point, ex: 21.95)
            progress=hh*3600+mm*60+ss
            updProgress(round(100/duration*progress), fileSize)
            # self.emitProgress.emit(round(100/self.totSize*self.processedSize), self.thick*(self.processedSize+fileSize*(progress/duration)))
        else:
            #calculating total video time
            p=re.match(durationRegex,line)
            if p is not None:
                hh=float(p.group(1)) #hours
                mm=float(p.group(2)) #mins
                ss=float(p.group(3)) #secs (floating point, ex: 21.95)
                duration = hh*3600+mm*60+ss
                # cthick = 100/duration
        if proc.poll() == 0:
            break
        elif proc.poll()==1:
            raise Exception("ffmpeg exited with error converting %s." % str(input_name)) #TODO which error? have to read last ffmpeg output!
            break
    return fileSize

#copy file inputPath to outputPath, calling callback every 250KB copied.
#(250=trigger value)
#https://hg.python.org/cpython/file/eb09f737120b/Lib/shutil.py#l215
def copy(inputPath, outputPath, updProgress):
    length = 16*1024
    trigger = 250*1024
    fileSize = inputPath.stat().st_size
    copied = count = 0
    fsrc = open(inputPath, 'rb')
    fdst = open(outputPath, 'wb')
    while 1:
        buf = fsrc.read(length)
        if not buf:
            break
        fdst.write(buf)
        copied += len(buf)
        count += len(buf)
        if count >= trigger:
            count = 0
            updProgress(round(100/fileSize*copied), fileSize)
    shutil.copymode(inputPath, outputPath, follow_symlinks=False)
    return fileSize

def getTotalSize(inputPath): #type (inputPath) = <class pathlib>
    #inputPath is a file:
    size = 0
    if inputPath.is_file():
        return inputPath.stat().st_size
    #inputPath is a folder:
    for item in inputPath.iterdir():
        size += getTotalSize(item)
    return size
