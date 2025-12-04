import sys
import os
import platform
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QFileDialog,
    QProgressBar, QTextEdit, QGroupBox, QGridLayout, QHBoxLayout, QVBoxLayout
)
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtCore import Qt, QThread, Signal


class RenameWorker(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal()

    def __init__(self, excel_path, folder_path, col_codsku, col_upc, col_color, col_muestra):
        super().__init__()
        self.excel_path = excel_path
        self.folder_path = folder_path
        self.col_codsku = col_codsku
        self.col_upc = col_upc
        self.col_color = col_color
        self.col_muestra = col_muestra

    def run(self):
        try:
            df_all = pd.read_excel(self.excel_path, dtype=str)
        except Exception as e:
            self.log.emit(f"Error leyendo Excel: {e}")
            self.finished.emit()
            return
        # Verificar columnas
        for col in (self.col_codsku, self.col_upc, self.col_color, self.col_muestra):
            if col not in df_all.columns:
                self.log.emit(f"Columna no encontrada: {col}")
                self.finished.emit()
                return
        df = df_all[[self.col_codsku, self.col_upc, self.col_color, self.col_muestra]].fillna("")
        # Filtrar filas de muestra
        df_sample = df[df[self.col_muestra].str.strip().astype(bool)]
        total_groups = df_sample.shape[0]
        done_groups = 0
        for _, sample_row in df_sample.iterrows():
            cod = sample_row[self.col_codsku]
            color = sample_row[self.col_color]
            target_upc = sample_row[self.col_upc]
            # Encontrar filas originales en mismo grupo
            originals = df[
                (df[self.col_codsku] == cod) &
                (df[self.col_color] == color) &
                (df[self.col_upc] != target_upc)
            ]
            for _, orig in originals.iterrows():
                old_upc = orig[self.col_upc]
                src = os.path.join(self.folder_path, old_upc)
                dst = os.path.join(self.folder_path, target_upc)
                if os.path.isdir(src):
                    if not os.path.exists(dst):
                        try:
                            os.rename(src, dst)
                            self.log.emit(f"Renombrado: {old_upc} → {target_upc}")
                        except Exception as e:
                            self.log.emit(f"Error renombrando {old_upc}: {e}")
                    else:
                        self.log.emit(f"Destino ya existe, saltando: {target_upc}")
                else:
                    self.log.emit(f"Carpeta no encontrada: {old_upc}")
            done_groups += 1
            pct = int(done_groups / total_groups * 100)
            self.progress.emit(pct)
        self.finished.emit()


class RenameApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Renombrar UPC - Ripley")
        self._apply_style()
        self._build_ui()

    def _apply_style(self):
        # Detectar plataforma y aplicar estilo
        system = platform.system()
        palette = QPalette()
        if system == 'Darwin':
            QApplication.setStyle('macintosh')
            self.setFont(QFont('Helvetica Neue', 12))
            palette.setColor(QPalette.Window, QColor('#ECECEC'))
        elif system == 'Windows':
            QApplication.setStyle('windowsvista')
            self.setFont(QFont('Segoe UI', 10))
            palette.setColor(QPalette.Window, QColor('#F0F0F0'))
        else:
            QApplication.setStyle('fusion')
            self.setFont(QFont('Arial', 10))
            palette.setColor(QPalette.Window, QColor('#ECECEC'))
        self.setPalette(palette)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # Panel de inputs
        grp = QGroupBox("Configuración")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        # Excel file
        grid.addWidget(QLabel("Archivo Excel:"), 0, 0)
        self.txt_excel = QLineEdit()
        grid.addWidget(self.txt_excel, 0, 1)
        btn_excel = QPushButton("Examinar...")
        btn_excel.clicked.connect(self._browse_excel)
        grid.addWidget(btn_excel, 0, 2)

        # Carpeta root
        grid.addWidget(QLabel("Carpeta UPC:"), 1, 0)
        self.txt_folder = QLineEdit()
        grid.addWidget(self.txt_folder, 1, 1)
        btn_folder = QPushButton("Examinar...")
        btn_folder.clicked.connect(self._browse_folder)
        grid.addWidget(btn_folder, 1, 2)

        # Columnas
        labels = ['codskupadrelargo', 'upc_ripley', 'color', 'muestra']
        self.cols = {}
        for i, col in enumerate(labels, start=2):
            grid.addWidget(QLabel(f"Columna {col}:"), i, 0)
            le = QLineEdit(col)
            grid.addWidget(le, i, 1, 1, 2)
            self.cols[col] = le

        grp.setLayout(grid)
        main_layout.addWidget(grp)

        # Botón iniciar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_start = QPushButton("Iniciar renombrado")
        self.btn_start.clicked.connect(self._start)
        btn_layout.addWidget(self.btn_start)
        main_layout.addLayout(btn_layout)

        # Progress y estado
        self.progress = QProgressBar()
        self.progress.setValue(0)
        main_layout.addWidget(self.progress)
        self.lbl_status = QLabel("Listo.")
        main_layout.addWidget(self.lbl_status)

        # Log
        log_grp = QGroupBox("Registro de actividad")
        vlog = QVBoxLayout()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        vlog.addWidget(self.log_area)
        log_grp.setLayout(vlog)
        main_layout.addWidget(log_grp)

        self.setLayout(main_layout)
        self.resize(600, 500)

    def _browse_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo Excel", "", "Excel Files (*.xlsx *.xls)")
        if path:
            self.txt_excel.setText(path)
            # autocompletar carpeta root con misma ubicación
            folder = os.path.dirname(path)
            self.txt_folder.setText(folder)

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de UPC")
        if path:
            self.txt_folder.setText(path)

    def _start(self):
        excel = self.txt_excel.text().strip()
        folder = self.txt_folder.text().strip()
        if not excel or not folder:
            self._log("Debe seleccionar archivo Excel y carpeta de UPC.")
            return
        cols = {k: v.text().strip() for k, v in self.cols.items()}
        # Deshabilitar UI
        self.btn_start.setEnabled(False)
        self.worker = RenameWorker(excel, folder,
                                   cols['codskupadrelargo'],
                                   cols['upc_ripley'],
                                   cols['color'],
                                   cols['muestra'])
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log.connect(self._log)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _log(self, msg):
        self.log_area.append(msg)
        self.lbl_status.setText(msg)

    def _on_finished(self):
        self.lbl_status.setText("Proceso terminado.")
        self.btn_start.setEnabled(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RenameApp()
    window.show()
    sys.exit(app.exec())
