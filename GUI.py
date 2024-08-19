import sys
from threading import Thread

from PyQt6.QtWidgets import (QWidget, QToolTip,
    QPushButton, QApplication, QSlider, QLabel, QComboBox, QCheckBox, QMessageBox,
    QHBoxLayout, QVBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QFont, QIcon

import multiprocessing
from soundcard.mediafoundation import SoundcardRuntimeWarning
from Trigger import SoftKbMouseV2, SoftKbMouseV3, HardKbMouse, GamePad, DodgingTrigger

import warnings
warnings.filterwarnings('ignore', category=SoundcardRuntimeWarning)

SAMPLE_PATH = "./特征波形_完整.wav"

class ZZZWheelchair(QWidget):

    def __init__(self):
        super().__init__()
        self.isRunning = False
        self.threshold = 0.1
        self.maxNCC = 1.0
        self.sucTri = False
        self.action = "dodge"

        self.t: Thread = None
        self.et: DodgingTrigger = None

        self.initUI()


    def initUI(self):

        QToolTip.setFont(QFont('SansSerif', 10))
        
        Thres_Label = QLabel('阈值', self)
        Thres_Label.setToolTip('触发动作阈值，取值[0, 1]，默认0.1')
        Thres_Slider = QSlider(Qt.Orientation.Horizontal, self)
        Thres_Slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        Thres_Slider.setFixedWidth(190)
        Thres_Slider.setRange(0, 100)
        Thres_Slider.setValue(10)
        Thres_Slider.setToolTip(f'{Thres_Slider.value() / 100.0}')
        Thres_Slider.valueChanged[int].connect(self.setThres)
        Thres_Hbox = QHBoxLayout()
        Thres_Hbox.addWidget(Thres_Label)
        Thres_Hbox.addWidget(Thres_Slider)
        

        MaxNcc_Label = QLabel('最大NCC系数', self)
        MaxNcc_Label.setToolTip('最大归一化交叉相关 (MAXIMUM NORMALIZED CROSS-CORRELATE) 的倍数，取值[0.0, 2.0]，默认1.0')
        MaxNCC_Slider = QSlider(Qt.Orientation.Horizontal, self)
        MaxNCC_Slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        MaxNCC_Slider.setFixedWidth(190)
        MaxNCC_Slider.setRange(0, 200)
        MaxNCC_Slider.setValue(100)
        MaxNCC_Slider.setToolTip(f'{MaxNCC_Slider.value() / 100.0}')
        MaxNCC_Slider.valueChanged[int].connect(self.setMaxNCC)
        MaxNCC_Hbox = QHBoxLayout()
        MaxNCC_Hbox.addWidget(MaxNcc_Label)
        MaxNCC_Hbox.addWidget(MaxNCC_Slider)

        SucTri_Checkbox = QCheckBox('防止连续触发', self)
        SucTri_Checkbox.setToolTip('是否可以连续触发，默认不可以False (防止连续触发)')
        SucTri_Checkbox.toggle()
        SucTri_Checkbox.stateChanged.connect(self.setSucTri)
        SucTri_Hbox = QHBoxLayout()
        SucTri_Hbox.addWidget(SucTri_Checkbox)


        Action_Label = QLabel('动作', self)
        Action_Combobox = QComboBox(self)
        Action_Combobox.addItem('闪避')
        Action_Combobox.addItem('双闪')
        Action_Combobox.addItem('换人')
        Action_Combobox.textActivated[str].connect(self.setAction)
        Action_Hbox = QHBoxLayout()
        Action_Hbox.addWidget(Action_Label)
        Action_Hbox.addWidget(Action_Combobox)

        Input_Label = QLabel('输入设备', self)
        Input_Combobox = QComboBox(self)
        Input_Combobox.addItem('键鼠')
        Input_Combobox.addItem('手柄')
        Input_Combobox.textActivated[str].connect(self.setInputDevice)
        Input_Hbox = QHBoxLayout()
        Input_Hbox.addWidget(Input_Label)
        Input_Hbox.addWidget(Input_Combobox)

        Info_Btn = QPushButton('信息', self)
        Info_Btn.clicked.connect(self.onInfoClicked)
        self.Run_Btn = QPushButton('开始', self)
        self.Run_Btn.setStyleSheet("""
            QPushButton{ color:#ffffffff; background-color:#007ad9 }\
            QPushButton:hover{ background-color:#0070d0 }""")
        self.Run_Btn.clicked.connect(self.onRunClicked)
        Run_Hbox = QHBoxLayout()
        Run_Hbox.addWidget(Info_Btn)
        Run_Hbox.addWidget(self.Run_Btn)

        vbox = QVBoxLayout()
        vbox.addLayout(Thres_Hbox)
        vbox.addLayout(MaxNCC_Hbox)
        vbox.addLayout(SucTri_Hbox)
        vbox.addLayout(Action_Hbox)
        vbox.addLayout(Input_Hbox)
        vbox.addLayout(Run_Hbox)

        self.setLayout(vbox)

        self.setGeometry(300, 300, 300, 200)
        self.setWindowTitle('ZZZ轮椅')
        self.setWindowIcon(QIcon('icon.ico'))
        self.show()

    def setThres(self, value):
        self.threshold = value / 100
        if self.isRunning:
            self.et.setThreshold(self.threshold)

    def setMaxNCC(self, value):
        self.maxNCC = value / 100
        if self.isRunning:
            self.et.setRatio(self.maxNCC)

    def setSucTri(self, state):
        self.sucTri = state == Qt.CheckState.Checked.value
        if self.isRunning:
            self.et.setSucTri(self.sucTri)
        print(self.sucTri)

    def setAction(self, text):
        self.action = {"闪避": 'dodge', "双闪": 'double_dodge', "换人": 'push_space'}.get(text, 'dodge')
        print(self.action)
        if self.isRunning:
            self.et.setAction(eval("controller.{}".format(self.action)))

    def setInputDevice(self, text):
        print(text)
        global controller
        if text == '手柄':
            controller = GamePad()
        else:
            controller = SoftKbMouseV3()

    def onInfoClicked(self):
        print('信息')
        about = '原作者：ImLaoBJie\nGithub：https://github.com/ImLaoBJie/ZZZSoundTrigger\nUI：SaltSakya'
        QMessageBox.about(self, 'ZZZ轮椅', about)

    def onRunClicked(self):
        if self.isRunning:
            self.et.stop()
            self.Run_Btn.setEnabled(False)
            self.Run_Btn.setText('停止中')
            self.t.join()
            self.isRunning = False
            self.Run_Btn.setEnabled(True)
            self.Run_Btn.setText('开始')
            self.Run_Btn.setStyleSheet("""
            QPushButton{ color:#ffffffff; background-color:#007ad9 }\
            QPushButton:hover{ background-color:#0070d0 }""")
        else:
            self.isRunning = True
            self.Run_Btn.setEnabled(False)
            self.Run_Btn.setText('准备中')
            self.et = DodgingTrigger(
                    SAMPLE_PATH,
                    eval("controller.{}".format(self.action)),
                    threshold=self.threshold,
                    ratio=self.maxNCC,
                    is_allowed_succe_dodge=self.sucTri,
                    callback=self.readyCallback)

    def readyCallback(self, et):
        self.t = Thread(target=et.online_listening)
        self.t.start()
        self.Run_Btn.setEnabled(True)
        self.Run_Btn.setText('停止')
        self.Run_Btn.setStyleSheet("""
            QPushButton{ color:#ffffffff; background-color:#ed3d45 }\
            QPushButton:hover{ background-color:#e03841 }""")

    def closeEvent(self, a0: QCloseEvent) -> None:
        print('关闭')
        if self.isRunning:
            if QMessageBox.question(self, '警告', '轮椅正在运行\n确定要关闭吗？', 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
                a0.ignore()
                return
            self.isRunning = False
            self.et.stop()
        return super().closeEvent(a0)

if __name__ == '__main__':
    multiprocessing.freeze_support()
    controller = SoftKbMouseV3()  # 软模拟GamePad
    app = QApplication(sys.argv)
    zzz = ZZZWheelchair()
    sys.exit(app.exec())