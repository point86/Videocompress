from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import os
import sys
from taskPerformer import TaskPerformer


class MainWindow(QWidget):

    DESC =  "Videocompress is a simple utility that runs ffmpeg over a single file or an entire directory (thus recursively on all\n"\
            "files and subdirs).\n"\
            "If input is an entire directory, this program will create another folder with the same structure and all the same files, the\n"\
            "only difference is that all video files will be the output of ffmpeg execution (non video files will be copied)."
    FFMPEG_SITE = "Need more options? <a href=\"https://ffmpeg.org/\">FFmpeg offical site</a> has all the documentation you will need."
    REPOSITORY = "Created by Paolo Venturato and distribuited under the MIT license. <a href=\"https://www.github.com\">Fork me on GitHub</a>"
    FFMPEGSETTINGS_DEF = "-c:v libx264 -crf 26"

    inputPath = None

    def __init__(self, parent = None):

        QWidget.__init__(self, parent)
        #vertical layout
        vbox = QVBoxLayout()

        #introduction labels
        l_intro = QLabel(self.DESC)
        vbox.addWidget(l_intro)
        l_site = QLabel(self.FFMPEG_SITE)
        l_site.setOpenExternalLinks(True)
        l_repo = QLabel(self.REPOSITORY)
        l_repo.setOpenExternalLinks(True)
        vbox.addWidget(l_site)
        vbox.addWidget(l_repo)

        #input area
        l_input = QLabel("Input path:")
        vbox.addWidget(l_input)

        self.treeView = QTreeView()
        self.model = QFileSystemModel() #data model for treeView
        self.model.setRootPath(QDir().rootPath())
        self.treeView.setModel(self.model)
        self.treeView.setColumnWidth(0,200)#name column
        self.treeView.setMinimumSize(QSize(400, 200))
        self.treeView.clicked.connect(self.selectInput)
        vbox.addWidget(self.treeView)

        #output area
        l_output = QLabel("Output path:")
        vbox.addWidget(l_output)
        outputHBox = QHBoxLayout()
        self.tb_output = QLineEdit("")
        outputHBox.addWidget(self.tb_output)
        self.btt_output = QPushButton("Select")
        self.btt_output.clicked.connect(self.selectOutputDir_btt)
        outputHBox.addWidget(self.btt_output)
        vbox.addLayout(outputHBox)

        #settings area
        l_encoding = QLabel("Encoding settings:")
        vbox.addWidget(l_encoding)

        #2 radio buttons
        self.std_rb = QRadioButton("H.264 - CRF 28")
        self.std_rb.setChecked(True)
        self.std_rb.toggled.connect(self.changeStack)
        self.adv_rb = QRadioButton("Advanced - (Custom command line options)")
        self.adv_rb.toggled.connect(self.changeStack)
        radiobttHBox = QHBoxLayout()
        radiobttHBox.addWidget(self.std_rb)
        radiobttHBox.addWidget(self.adv_rb)
        vbox.addLayout(radiobttHBox)

        #simple settings (x264), with slider
        simple_sett_layout = QHBoxLayout()
        l_min = QLabel("High quality\n(Bigger size)")
        l_max = QLabel("Low quality\n(Smaller size)")
        self.slider = QSlider(Qt.Horizontal)
        #total CRF range is 0-51, but 18-28 is a sane range
        self.slider.setMinimum(18) #visually lossless or nearly so
        self.slider.setMaximum(28) #higher values than 28 results in very poor quality
        self.slider.setValue(26)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.valueChanged.connect(self.sliderValuechange)
        simple_sett_layout.addWidget(l_min)
        simple_sett_layout.addWidget(self.slider)
        simple_sett_layout.addWidget(l_max)

        #advanced settings (explicit commands)
        adv_sett_layout = QHBoxLayout()
        self.tb_advsett = QLineEdit(self.FFMPEGSETTINGS_DEF)
        self.tb_advsett.setEnabled(True) #useless
        self.btt_restdef = QPushButton("Restore defalut")
        self.btt_restdef.clicked.connect(self.ffmpeg_btt)
        adv_sett_layout.addWidget(self.btt_restdef)
        adv_sett_layout.addWidget(self.tb_advsett)

        #encoding stack
        stack0 = QWidget()
        stack1 = QWidget()
        stack0.setLayout(simple_sett_layout)
        stack1.setLayout(adv_sett_layout)
        self.settingsStack = QStackedWidget()
        self.settingsStack.addWidget(stack0)
        self.settingsStack.addWidget(stack1)
        vbox.addWidget(self.settingsStack)

        #start button
        vbox.addStretch(1)
        startHbox = QHBoxLayout()
        self.btt_start = QPushButton("Start")
        self.btt_start.setStyleSheet("color: green")
        self.btt_start.clicked.connect(self.start_btt)
        self.btt_start.setFixedWidth(100)
        startHbox.addWidget(self.btt_start)
        vbox.addLayout(startHbox)

        self.setLayout(vbox)
        self.resize(600, 400)
        self.setWindowTitle("VideoCompress")

    #when user change sliver value, update radio button label
    def sliderValuechange(self):
        value = self.slider.value()
        self.std_rb.setText("H.264 - CRF " + str(value))

    #toggled when user use radio buttons, to change setting options area
    def changeStack(self):
        if self.adv_rb.isChecked() == True:
            self.settingsStack.setCurrentIndex(1)
        else:
            self.settingsStack.setCurrentIndex(0)

    #select input folder (QTreeView) callback
    def selectInput(self, index):
        self.inputPath = os.path.normpath(self.model.filePath(index))

    #select output folder callback
    def selectOutputDir_btt(self,window):
        t = QFileDialog.getExistingDirectory(None, "Output Folder", None)

        self.tb_output.setText(os.path.normpath(t))

    #restore ffmpeg settings callback
    def ffmpeg_btt(self, window):
        self.tb_advsett.setText(self.FFMPEGSETTINGS_DEF)

    #start conversion dialog
    def start_btt(self, window):
        #if input and output are not set, show error dialog and do not start conversion

        if (self.inputPath == None) or (self.tb_output.text() == None) or (self.inputPath == self.tb_output.text()):
           msg = QMessageBox()
           msg.setIcon(QMessageBox.Critical)
           msg.setWindowTitle("Error")
           msg.setText("Please verify ipunt and output path.")
           msg.setStandardButtons(QMessageBox.Ok)
           msg.exec_()
           return

        #user in stack0 (preset H.264, simple options): retrieve slider value
        #and add to ffmpeg command
        if self.settingsStack.currentIndex() == 0:
            ffmpegOpt = " -c:v libx264 -crf " + str(self.slider.value())
            #user in stack1 (custom ffmpeg options, textbox):
        else:
            ffmpegOpt = self.tb_advsett.text()

        performer = TaskPerformer(self.inputPath, self.tb_output.text(), ffmpegOpt)
        performer.start_conversion()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
