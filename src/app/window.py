from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)

import audio as core
from app.widgets import LogBox, PathListPanel


@dataclass(frozen=True)
class ProgressEvent:
    done: int
    total: int
    message: str


class Worker(QObject):
    progressed = Signal(object)
    finished = Signal(object, object)

    def __init__(self, fn: Callable[[], object]) -> None:
        super().__init__()
        self._fn = fn

    def run(self) -> None:
        try:
            out = self._fn()
            self.finished.emit(out, None)
        except Exception as e:
            self.finished.emit(None, e)


class JobController(QObject):
    progressed = Signal(object)
    finished = Signal(object, object)

    def __init__(self) -> None:
        super().__init__()
        self._thread: Optional[QThread] = None
        self._worker: Optional[Worker] = None

    def start(self, fn: Callable[[], object]) -> None:
        self.stop()
        t = QThread()
        w = Worker(fn)
        w.moveToThread(t)
        t.started.connect(w.run)
        w.progressed.connect(self.progressed)
        w.finished.connect(self.finished)
        w.finished.connect(t.quit)
        w.finished.connect(w.deleteLater)
        t.finished.connect(t.deleteLater)
        self._thread = t
        self._worker = w
        t.start()

    def stop(self) -> None:
        if self._thread is not None:
            self._thread.quit()
        self._thread = None
        self._worker = None


class ProbeTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.controller = JobController()

        self.inputs = PathListPanel("Inputs")
        self.btn_probe = QPushButton("Probe")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.logbox = LogBox()

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["File", "Duration (s)", "Sample Rate", "Channels", "Codec", "Bitrate"])

        btns = QHBoxLayout()
        btns.addWidget(self.btn_probe)
        btns.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.inputs)
        layout.addLayout(btns)
        layout.addWidget(self.progress)
        layout.addWidget(self.table)
        layout.addWidget(self.logbox)

        self.inputs.btn_add_files.clicked.connect(self._add_files)
        self.inputs.btn_remove.clicked.connect(self.inputs.list.remove_selected)
        self.inputs.btn_clear.clicked.connect(self.inputs.list.clear_all)
        self.btn_probe.clicked.connect(self._run)

        self.controller.progressed.connect(self._on_progress)
        self.controller.finished.connect(self._on_finished)

    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Select audio files")
        self.inputs.list.add_paths([Path(f) for f in files])

    def _on_progress(self, ev: object) -> None:
        e: ProgressEvent = ev
        if e.total > 0:
            self.progress.setValue(int((e.done * 100) / e.total))
        self.logbox.log(e.message)

    def _on_finished(self, result: object, error: object) -> None:
        if error is not None:
            self.logbox.log(f"Error: {error}")
            return

        infos: list[core.AudioInfo] = result
        self.table.setRowCount(0)
        self.table.setRowCount(len(infos))

        for i, info in enumerate(infos):
            self.table.setItem(i, 0, QTableWidgetItem(str(info.path.name)))
            self.table.setItem(i, 1, QTableWidgetItem(f"{info.duration_s:.3f}"))
            self.table.setItem(i, 2, QTableWidgetItem("" if info.sample_rate is None else str(info.sample_rate)))
            self.table.setItem(i, 3, QTableWidgetItem("" if info.channels is None else str(info.channels)))
            self.table.setItem(i, 4, QTableWidgetItem("" if info.codec is None else str(info.codec)))
            self.table.setItem(i, 5, QTableWidgetItem("" if info.bit_rate is None else str(info.bit_rate)))

        self.logbox.log("Done")

    def _run(self) -> None:
        paths = self.inputs.list.get_paths()
        if not paths:
            QMessageBox.warning(self, "Missing input", "Add at least one audio file.")
            return

        self.progress.setValue(0)
        self.table.setRowCount(0)
        self.logbox.log("Probing...")

        def fn() -> object:
            out: list[core.AudioInfo] = []
            total = len(paths)
            for idx, p in enumerate(paths, start=1):
                info = core.probe_file(p)
                out.append(info)
                self.controller.progressed.emit(ProgressEvent(idx, total, f"{idx}/{total} Probed {p.name}"))
            return out

        self.controller.start(fn)


class ConvertTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.controller = JobController()

        self.inputs = PathListPanel("Inputs")

        self.out_dir = QLineEdit()
        self.btn_out_dir = QPushButton("Choose")

        self.sample_rate = QSpinBox()
        self.sample_rate.setRange(8000, 192000)
        self.sample_rate.setValue(48000)

        self.channels = QSpinBox()
        self.channels.setRange(1, 8)
        self.channels.setValue(1)

        self.bit_depth = QSpinBox()
        self.bit_depth.setRange(16, 32)
        self.bit_depth.setSingleStep(8)
        self.bit_depth.setValue(16)

        self.overwrite = QCheckBox("Overwrite")

        self.btn_convert = QPushButton("Convert")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.logbox = LogBox()

        out_row = QHBoxLayout()
        out_row.addWidget(self.out_dir)
        out_row.addWidget(self.btn_out_dir)

        opts = QGroupBox("Options")
        form = QFormLayout(opts)
        form.addRow("Output folder", out_row)
        form.addRow("Sample rate", self.sample_rate)
        form.addRow("Channels", self.channels)
        form.addRow("Bit depth", self.bit_depth)
        form.addRow("", self.overwrite)

        btns = QHBoxLayout()
        btns.addWidget(self.btn_convert)
        btns.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.inputs)
        layout.addWidget(opts)
        layout.addLayout(btns)
        layout.addWidget(self.progress)
        layout.addWidget(self.logbox)

        self.inputs.btn_add_files.clicked.connect(self._add_files)
        self.inputs.btn_remove.clicked.connect(self.inputs.list.remove_selected)
        self.inputs.btn_clear.clicked.connect(self.inputs.list.clear_all)

        self.btn_out_dir.clicked.connect(self._choose_out_dir)
        self.btn_convert.clicked.connect(self._run)

        self.controller.progressed.connect(self._on_progress)
        self.controller.finished.connect(self._on_finished)

    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Select audio files")
        self.inputs.list.add_paths([Path(f) for f in files])

    def _choose_out_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select output folder")
        if d:
            self.out_dir.setText(d)

    def _on_progress(self, ev: object) -> None:
        e: ProgressEvent = ev
        if e.total > 0:
            self.progress.setValue(int((e.done * 100) / e.total))
        self.logbox.log(e.message)

    def _on_finished(self, result: object, error: object) -> None:
        if error is not None:
            self.logbox.log(f"Error: {error}")
            return
        outs: list[Path] = result
        self.logbox.log(f"Done: {len(outs)} file(s)")

    def _run(self) -> None:
        paths = self.inputs.list.get_paths()
        if not paths:
            QMessageBox.warning(self, "Missing input", "Add at least one audio file.")
            return

        out_dir_str = self.out_dir.text().strip()
        if not out_dir_str:
            QMessageBox.warning(self, "Missing output", "Choose an output folder.")
            return

        out_dir = Path(out_dir_str)

        opts = core.ConvertOptions(
            out_dir=out_dir,
            sample_rate=int(self.sample_rate.value()),
            channels=int(self.channels.value()),
            bit_depth=int(self.bit_depth.value()),
            overwrite=self.overwrite.isChecked(),
            force_wav=True,
        )

        self.progress.setValue(0)
        self.logbox.log("Converting...")

        def fn() -> object:
            outs: list[Path] = []
            total = len(paths)
            for idx, p in enumerate(paths, start=1):
                outp = core.convert_file(p, opts)
                outs.append(outp)
                self.controller.progressed.emit(ProgressEvent(idx, total, f"{idx}/{total} Converted {p.name}"))
            return outs

        self.controller.start(fn)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Audio Tool (Probe + Convert)")

        tabs = QTabWidget()
        tabs.addTab(ProbeTab(), "Probe")
        tabs.addTab(ConvertTab(), "Convert")

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(tabs)
        root.setLayout(layout)
        self.setCentralWidget(root)
        self.resize(1100, 800)