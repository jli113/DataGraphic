from ryven.NWENV import *
from qtpy.QtWidgets import (
    QLabel,
    QTextEdit,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QWidget,
)
from qtpy.QtCore import Signal
from qtpy.QtGui import QFont
import os


class ChooseFileInputWidget(IWB, QPushButton):
    path_chosen = Signal(str)

    def __init__(self, params):
        IWB.__init__(self, params)
        QPushButton.__init__(self, "Select")

        self.clicked.connect(self.button_clicked)

    def button_clicked(self):
        file_path = QFileDialog.getOpenFileName(self, "Select image")[0]
        try:
            file_path = os.path.relpath(file_path)
        except ValueError:
            return

        self.path_chosen.emit(file_path)


class PathInput(IWB, QWidget):
    path_chosen = Signal(str)

    def __init__(self, params):
        IWB.__init__(self, params)
        QWidget.__init__(self)

        self.path = ""

        # setup UI
        l = QVBoxLayout()
        button = QPushButton("choose")
        button.clicked.connect(self.choose_button_clicked)
        l.addWidget(button)
        self.path_label = QLabel("path")
        l.addWidget(self.path_label)
        self.setLayout(l)

    def choose_button_clicked(self):
        abs_f_path = QFileDialog.getSaveFileName(self, "Save")[0]
        self.path = os.path.relpath(abs_f_path)

        self.path_label.setText(self.path)
        self.adjustSize()  # important! otherwise the widget won't shrink

        self.path_chosen.emit(self.path)

        self.node.update_shape()

    def get_state(self):
        return {"path": self.path}

    def set_state(self, data):
        self.path = data["path"]
        self.path_label.setText(self.path)
        self.node.update_shape()


class WatchWidget(MWB, QTextEdit):
    def __init__(self, params, base_width=256, base_height=256):
        MWB.__init__(self, params)
        QTextEdit.__init__(self)

        c = self.node.color
        self.setStyleSheet(
            """
QTextEdit{
    color: """
            + c
            + """;
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 0px;
    font-family: Source Code Pro;
    font-size: 10pt;
}
        """
        )
        # border: 1px solid '''+c+''';

        # self.setFont(font)
        self.base_width = base_width
        self.base_height = base_height
        self.setFixedSize(self.base_width, self.base_height)
        self.setReadOnly(True)
        self.hidden_size = None

    def show_val(self, new_val):
        self.setText(str(new_val))


class SmallWatchWidget(MWB, QTextEdit):
    def __init__(self, params, base_width=60, base_height=80):
        MWB.__init__(self, params)
        QTextEdit.__init__(self)

        c = self.node.color
        self.setStyleSheet(
            """
QTextEdit{
    color: """
            + c
            + """;
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 0px;
    font-family: Source Code Pro;
    font-size: 10pt;
}
        """
        )
        # border: 1px solid '''+c+''';

        # self.setFont(font)
        self.base_width = base_width
        self.base_height = base_height
        self.setFixedSize(self.base_width, self.base_height)
        self.setReadOnly(True)
        self.hidden_size = None

    def show_val(self, new_val):
        self.setText(str(new_val))


export_widgets(
    ChooseFileInputWidget, PathInput, WatchWidget, SmallWatchWidget,
)
