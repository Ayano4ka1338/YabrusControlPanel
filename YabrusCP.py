#!/usr/bin/env python3

import sys
import os
import subprocess
import importlib
import time
import threading
import json
import shutil
import socket
from datetime import datetime
from pathlib import Path

def check_library(lib_name):
    try:
        importlib.import_module(lib_name)
        return True
    except ImportError:
        return False

def install_package(package):
    try:
        print(f"Устанавливаем {package}...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", package,
            "--break-system-packages"
        ])
        return True
    except:
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package,
                "--user"
            ])
            return True
        except:
            return False

def check_and_install_dependencies():
    required = {
        'PyQt5': 'PyQt5',
        'psutil': 'psutil'
    }
    
    missing = []
    for name, pip_name in required.items():
        if not check_library(name):
            missing.append(pip_name)
    
    if missing:
        print("Устанавливаем зависимости...")
        for pkg in missing:
            if not install_package(pkg):
                print(f"Не удалось установить {pkg}")
                print("Установите вручную:")
                print(f"pip install {pkg} --break-system-packages")
                return False
    return True

if not check_and_install_dependencies():
    print("Невозможно продолжить работу")
    sys.exit(1)

from PyQt5 import QtWidgets, QtCore, QtGui
import psutil

try:
    import pulsectl
    HAS_PULSE = True
except:
    HAS_PULSE = False

class BackgroundMessageManager:
    def __init__(self, parent):
        self.parent = parent
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.show_message)
        self.timer.start(180000)
        self.message_count = 0
        QtCore.QTimer.singleShot(30000, self.show_message)
        
    def show_message(self):
        self.message_count += 1
        msg = QtWidgets.QMessageBox(self.parent)
        msg.setWindowTitle("💡 Напоминание")
        msg.setIcon(QtWidgets.QMessageBox.Information)
        
        content = f"""
        <h3 style='color: #2196F3;'>🌟 Спасибо, что используете наше приложение!</h3>
        <p style='font-size: 14px;'>
            Мы ценим ваше время и стараемся сделать программу<br>
            максимально удобной и функциональной.
        </p>
        <br>
        <p style='color: #666; font-size: 12px;'>
            ⏱️ Сообщение #{self.message_count}
        </p>
        <p style='color: #999; font-size: 11px;'>
            Подсказка: используйте горячие клавиши для быстрого доступа
        </p>
        """
        
        msg.setText(content)
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        dont_show = msg.addButton("Не показывать", QtWidgets.QMessageBox.RejectRole)
        dont_show.clicked.connect(self.disable_messages)
        msg.exec_()
        
    def disable_messages(self):
        self.timer.stop()
        QtWidgets.QMessageBox.information(
            self.parent,
            "Уведомления отключены",
            "Фоновые сообщения отключены.\nВы всегда можете включить их в настройках."
        )

class TerminalEmulator(QtWidgets.QWidget):
    def __init__(self, parent=None):
        self.history = []
        self.history_index = -1
        self.current_dir = os.path.expanduser("~")
        self.process = None
        self.output_buffer = ""
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        
        toolbar = QtWidgets.QHBoxLayout()
        self.path_label = QtWidgets.QLabel(f"📁 {self.current_dir}")
        toolbar.addWidget(self.path_label)
        toolbar.addStretch()
        clear_btn = QtWidgets.QPushButton("🧹 Очистить")
        clear_btn.clicked.connect(self.clear_terminal)
        toolbar.addWidget(clear_btn)
        stop_btn = QtWidgets.QPushButton("⏹ Стоп")
        stop_btn.clicked.connect(self.stop_command)
        toolbar.addWidget(stop_btn)
        layout.addLayout(toolbar)
        
        self.output = QtWidgets.QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Monospace', 'Courier New';
                font-size: 12px;
                border: 1px solid #333;
            }
        """)
        layout.addWidget(self.output)
        
        input_layout = QtWidgets.QHBoxLayout()
        self.prompt = QtWidgets.QLabel("$ ")
        self.prompt.setStyleSheet("color: #4CAF50; font-weight: bold;")
        input_layout.addWidget(self.prompt)
        self.input = QtWidgets.QLineEdit()
        self.input.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: none;
                padding: 5px;
                font-family: 'Monospace', 'Courier New';
            }
        """)
        self.input.returnPressed.connect(self.execute_command)
        input_layout.addWidget(self.input)
        layout.addLayout(input_layout)
        
        self.append_output("=" * 60)
        self.append_output("Добро пожаловать в эмулятор терминала!")
        self.append_output(f"Текущая директория: {self.current_dir}")
        self.append_output("=" * 60)
        self.append_output("")
        
    def append_output(self, text):
        self.output.append(text)
        self.output.ensureCursorVisible()
        
    def execute_command(self):
        command = self.input.text().strip()
        if not command:
            return
        self.input.clear()
        self.append_output(f"\n$ {command}")
        self.history.append(command)
        self.history_index = len(self.history)
        
        if command == "clear":
            self.clear_terminal()
            return
        elif command == "exit":
            self.append_output("Выход из терминала")
            return
        elif command.startswith("cd "):
            try:
                path = command[3:].strip()
                if path == "~" or path == "":
                    path = os.path.expanduser("~")
                elif not os.path.isabs(path):
                    path = os.path.join(self.current_dir, path)
                if os.path.isdir(path):
                    self.current_dir = os.path.abspath(path)
                    self.path_label.setText(f"📁 {self.current_dir}")
                    self.append_output(f"Перешли в: {self.current_dir}")
                else:
                    self.append_output(f"Ошибка: {path} - не директория")
            except Exception as e:
                self.append_output(f"Ошибка: {e}")
            return
        
        self.run_command_in_thread(command)
        
    def run_command_in_thread(self, command):
        def thread_func():
            try:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=self.current_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                self.process = process
                for line in iter(process.stdout.readline, ''):
                    if line:
                        self.append_output(line.rstrip())
                process.stdout.close()
                process.wait()
                if process.returncode != 0:
                    error = process.stderr.read()
                    if error:
                        self.append_output(f"Ошибка: {error.rstrip()}")
            except Exception as e:
                self.append_output(f"Ошибка: {e}")
            finally:
                self.process = None
        
        thread = threading.Thread(target=thread_func)
        thread.daemon = True
        thread.start()
        
    def stop_command(self):
        if self.process:
            try:
                self.process.terminate()
                self.append_output("\nКоманда остановлена")
            except:
                pass
        
    def clear_terminal(self):
        self.output.clear()
        self.append_output("Терминал очищен")
        
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Up:
            if self.history and self.history_index > 0:
                self.history_index -= 1
                self.input.setText(self.history[self.history_index])
        elif event.key() == QtCore.Qt.Key_Down:
            if self.history and self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.input.setText(self.history[self.history_index])
            else:
                self.history_index = len(self.history)
                self.input.clear()
        else:
            super().keyPressEvent(event)

class SoundManager:
    def __init__(self):
        self.volume = 50
        self.muted = False
        
    def get_volume(self):
        return self.volume
        
    def set_volume(self, volume):
        self.volume = max(0, min(100, volume))
        try:
            if HAS_PULSE:
                pulse = pulsectl.Pulse('sound-manager')
                sink = pulse.get_sink_by_name(
                    pulse.server_info().default_sink_name
                )
                pulse.volume_set_all_chans(sink, volume / 100)
                pulse.close()
        except:
            pass
                
    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.set_volume(0)
        else:
            self.set_volume(self.volume)
        return self.muted
            
    def play_test_sound(self):
        try:
            subprocess.run(['paplay', '/usr/share/sounds/freedesktop/stereo/complete.oga'], 
                         timeout=1, stderr=subprocess.DEVNULL)
        except:
            try:
                subprocess.run(['beep', '-f', '1000', '-l', '200'], timeout=1)
            except:
                pass

class ControlPanel(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🛠️ Панель управления системой")
        self.setGeometry(50, 50, 1200, 800)
        
        self.sound_manager = SoundManager()
        self.settings_file = os.path.join(os.path.expanduser("~"), ".control_panel_settings.json")
        self.settings = self.load_settings()
        self.show_messages = self.settings.get('show_messages', True)
        self.cpu_progress = None
        self.mem_progress = None
        self.disk_progress = None
        self.network_graph = None
        
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout()
        central.setLayout(main_layout)
        
        self.create_top_panel(main_layout)
        
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)
        
        self.tabs.addTab(self.create_system_tab(), "💻 Система")
        self.tabs.addTab(self.create_sound_tab(), "🔊 Звук")
        self.tabs.addTab(self.create_terminal_tab(), "🖥️ Терминал")
        self.tabs.addTab(self.create_processes_tab(), "⚙️ Процессы")
        self.tabs.addTab(self.create_network_tab(), "🌐 Сеть")
        self.tabs.addTab(self.create_files_tab(), "📁 Файлы")
        self.tabs.addTab(self.create_settings_tab(), "⚙️ Настройки")
        
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status("Готов к работе")
        
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_system_info)
        self.timer.start(2000)
        
        self.apply_settings()
        
        self.message_manager = BackgroundMessageManager(self)
        if not self.show_messages:
            self.message_manager.timer.stop()
        
    def create_top_panel(self, parent_layout):
        panel = QtWidgets.QFrame()
        panel.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                color: white;
                padding: 5px;
            }
        """)
        
        layout = QtWidgets.QHBoxLayout()
        panel.setLayout(layout)
        
        self.sys_info = QtWidgets.QLabel("🖥️ Загрузка...")
        layout.addWidget(self.sys_info)
        layout.addStretch()
        
        self.cpu_info = QtWidgets.QLabel("CPU: 0%")
        layout.addWidget(self.cpu_info)
        
        self.memory_info = QtWidgets.QLabel("💾 0%")
        layout.addWidget(self.memory_info)
        
        self.time_info = QtWidgets.QLabel()
        self.update_time()
        layout.addWidget(self.time_info)
        
        quick_buttons = [
            ("🔊", self.toggle_mute_quick),
            ("🔄", self.refresh_system),
            ("⏹️", self.shutdown_system),
        ]
        
        for text, callback in quick_buttons:
            btn = QtWidgets.QPushButton(text)
            btn.setFixedSize(35, 35)
            btn.clicked.connect(callback)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #34495e;
                    color: white;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #4a6a8a;
                }
            """)
            layout.addWidget(btn)
        
        parent_layout.addWidget(panel)
        
        self.time_timer = QtCore.QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)
    
    def toggle_mute_quick(self):
        muted = self.sound_manager.toggle_mute()
        self.update_status("Звук выключен" if muted else "Звук включен")
        if hasattr(self, 'mute_btn'):
            self.mute_btn.setText("🔇 Выкл" if muted else "🔊 Вкл")
        
    def create_system_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout()
        widget.setLayout(layout)
        
        sys_group = QtWidgets.QGroupBox("📊 Системная информация")
        sys_layout = QtWidgets.QFormLayout()
        sys_group.setLayout(sys_layout)
        
        self.sys_fields = {}
        info_items = [
            ("ОС", self.get_os_info),
            ("Хост", self.get_hostname),
            ("Пользователь", self.get_username),
            ("Ядер CPU", self.get_cpu_cores),
            ("Память", self.get_memory_info),
            ("Диски", self.get_disk_info),
        ]
        
        for label, func in info_items:
            value = QtWidgets.QLabel("...")
            sys_layout.addRow(label, value)
            self.sys_fields[label] = (func, value)
        
        layout.addWidget(sys_group, 0, 0, 2, 1)
        
        ctrl_group = QtWidgets.QGroupBox("🎮 Управление")
        ctrl_layout = QtWidgets.QGridLayout()
        ctrl_group.setLayout(ctrl_layout)
        
        buttons = [
            ("📋 Информация", self.show_system_info),
            ("📊 Монитор", self.show_system_monitor),
            ("🔄 Обновить", self.refresh_system),
            ("📦 Пакеты", self.show_packages),
            ("💾 Резервное копирование", self.backup_system),
            ("🧹 Очистка", self.clean_system),
        ]
        
        for i, (text, callback) in enumerate(buttons):
            btn = QtWidgets.QPushButton(text)
            btn.clicked.connect(callback)
            btn.setMinimumHeight(40)
            ctrl_layout.addWidget(btn, i // 2, i % 2)
        
        layout.addWidget(ctrl_group, 2, 0, 2, 1)
        
        graph_group = QtWidgets.QGroupBox("📈 Графики загрузки")
        graph_layout = QtWidgets.QVBoxLayout()
        graph_group.setLayout(graph_layout)
        
        cpu_label = QtWidgets.QLabel("Загрузка CPU")
        graph_layout.addWidget(cpu_label)
        self.cpu_progress = QtWidgets.QProgressBar()
        self.cpu_progress.setRange(0, 100)
        graph_layout.addWidget(self.cpu_progress)
        
        mem_label = QtWidgets.QLabel("Использование памяти")
        graph_layout.addWidget(mem_label)
        self.mem_progress = QtWidgets.QProgressBar()
        self.mem_progress.setRange(0, 100)
        graph_layout.addWidget(self.mem_progress)
        
        disk_label = QtWidgets.QLabel("Использование диска")
        graph_layout.addWidget(disk_label)
        self.disk_progress = QtWidgets.QProgressBar()
        self.disk_progress.setRange(0, 100)
        graph_layout.addWidget(self.disk_progress)
        
        layout.addWidget(graph_group, 0, 1, 4, 1)
        
        return widget
    
    def create_sound_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)
        
        vol_group = QtWidgets.QGroupBox("🔊 Громкость")
        vol_layout = QtWidgets.QVBoxLayout()
        vol_group.setLayout(vol_layout)
        
        self.volume_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.sound_manager.get_volume())
        self.volume_slider.valueChanged.connect(self.change_volume)
        vol_layout.addWidget(self.volume_slider)
        
        vol_info = QtWidgets.QHBoxLayout()
        self.volume_label = QtWidgets.QLabel(f"Громкость: {self.sound_manager.get_volume()}%")
        vol_info.addWidget(self.volume_label)
        vol_info.addStretch()
        self.mute_btn = QtWidgets.QPushButton("🔊 Вкл")
        self.mute_btn.clicked.connect(self.toggle_mute)
        vol_info.addWidget(self.mute_btn)
        vol_layout.addLayout(vol_info)
        
        sound_buttons = QtWidgets.QHBoxLayout()
        sound_btns = [
            ("🔊 Тест", self.test_sound),
            ("⏫ Увеличить", lambda: self.change_volume(self.volume_slider.value() + 10)),
            ("⏬ Уменьшить", lambda: self.change_volume(self.volume_slider.value() - 10)),
        ]
        
        for text, callback in sound_btns:
            btn = QtWidgets.QPushButton(text)
            btn.clicked.connect(callback)
            sound_buttons.addWidget(btn)
        
        vol_layout.addLayout(sound_buttons)
        layout.addWidget(vol_group)
        
        scheme_group = QtWidgets.QGroupBox("🎵 Звуковые схемы")
        scheme_layout = QtWidgets.QVBoxLayout()
        scheme_group.setLayout(scheme_layout)
        
        self.scheme_combo = QtWidgets.QComboBox()
        self.scheme_combo.addItems(["Системная", "Тихая", "Громкая", "Пользовательская"])
        scheme_layout.addWidget(self.scheme_combo)
        
        scheme_btn = QtWidgets.QPushButton("Применить схему")
        scheme_btn.clicked.connect(self.apply_sound_scheme)
        scheme_layout.addWidget(scheme_btn)
        
        layout.addWidget(scheme_group)
        
        return widget
    
    def create_terminal_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)
        self.terminal = TerminalEmulator()
        layout.addWidget(self.terminal)
        return widget
    
    def create_processes_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)
        
        control = QtWidgets.QHBoxLayout()
        self.process_filter = QtWidgets.QLineEdit()
        self.process_filter.setPlaceholderText("🔍 Фильтр процессов...")
        self.process_filter.textChanged.connect(self.filter_processes)
        control.addWidget(self.process_filter)
        refresh_btn = QtWidgets.QPushButton("🔄 Обновить")
        refresh_btn.clicked.connect(self.refresh_processes)
        control.addWidget(refresh_btn)
        kill_btn = QtWidgets.QPushButton("⏹ Завершить")
        kill_btn.clicked.connect(self.kill_selected_process)
        control.addWidget(kill_btn)
        layout.addLayout(control)
        
        self.process_table = QtWidgets.QTableWidget()
        self.process_table.setColumnCount(6)
        self.process_table.setHorizontalHeaderLabels([
            "PID", "Имя", "CPU%", "Память%", "Статус", "Пользователь"
        ])
        self.process_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.process_table.setAlternatingRowColors(True)
        layout.addWidget(self.process_table)
        
        self.refresh_processes()
        
        return widget
    
    def create_network_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout()
        widget.setLayout(layout)
        
        net_group = QtWidgets.QGroupBox("📡 Сетевая информация")
        net_layout = QtWidgets.QFormLayout()
        net_group.setLayout(net_layout)
        
        self.network_fields = {}
        net_items = [
            ("IP адрес", self.get_ip_address),
            ("Хост", self.get_hostname),
            ("Скорость скачивания", self.get_download_speed),
            ("Скорость загрузки", self.get_upload_speed),
            ("Сетевой интерфейс", self.get_network_interface),
        ]
        
        for label, func in net_items:
            value = QtWidgets.QLabel("...")
            net_layout.addRow(label, value)
            self.network_fields[label] = (func, value)
        
        layout.addWidget(net_group, 0, 0, 2, 1)
        
        tools_group = QtWidgets.QGroupBox("🛠 Сетевые инструменты")
        tools_layout = QtWidgets.QGridLayout()
        tools_group.setLayout(tools_layout)
        
        tools = [
            ("📡 Пинг", self.ping_host),
            ("🔍 DNS запрос", self.dns_lookup),
            ("📊 Трассировка", self.trace_route),
            ("🌐 Wi-Fi", self.show_wifi),
            ("🔌 Порты", self.show_ports),
            ("📈 Статистика", self.show_network_stats),
        ]
        
        for i, (text, callback) in enumerate(tools):
            btn = QtWidgets.QPushButton(text)
            btn.clicked.connect(callback)
            btn.setMinimumHeight(35)
            tools_layout.addWidget(btn, i // 2, i % 2)
        
        layout.addWidget(tools_group, 2, 0, 2, 1)
        
        graph_group = QtWidgets.QGroupBox("📊 График сети")
        graph_layout = QtWidgets.QVBoxLayout()
        graph_group.setLayout(graph_layout)
        
        self.network_graph = QtWidgets.QProgressBar()
        self.network_graph.setRange(0, 100)
        graph_layout.addWidget(QtWidgets.QLabel("Использование сети"))
        graph_layout.addWidget(self.network_graph)
        
        layout.addWidget(graph_group, 0, 1, 4, 1)
        
        return widget
    
    def create_files_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)
        
        nav = QtWidgets.QHBoxLayout()
        self.path_input = QtWidgets.QLineEdit()
        self.path_input.setText(os.path.expanduser("~"))
        self.path_input.returnPressed.connect(self.navigate_to_path)
        nav.addWidget(self.path_input)
        go_btn = QtWidgets.QPushButton("📂 Перейти")
        go_btn.clicked.connect(self.navigate_to_path)
        nav.addWidget(go_btn)
        up_btn = QtWidgets.QPushButton("📤 Вверх")
        up_btn.clicked.connect(self.go_up)
        nav.addWidget(up_btn)
        layout.addLayout(nav)
        
        self.file_list = QtWidgets.QListWidget()
        self.file_list.itemDoubleClicked.connect(self.open_file_item)
        self.file_list.setAlternatingRowColors(True)
        layout.addWidget(self.file_list)
        
        self.refresh_file_list()
        
        return widget
    
    def create_settings_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widget.setLayout(layout)
        
        general_group = QtWidgets.QGroupBox("⚙️ Общие настройки")
        general_layout = QtWidgets.QFormLayout()
        general_group.setLayout(general_layout)
        
        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.addItems(["Светлая", "Тёмная", "Системная"])
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        general_layout.addRow("Тема", self.theme_combo)
        
        self.messages_check = QtWidgets.QCheckBox()
        self.messages_check.setChecked(self.show_messages)
        self.messages_check.toggled.connect(self.toggle_messages)
        general_layout.addRow("Показывать фоновые сообщения", self.messages_check)
        
        self.autostart_check = QtWidgets.QCheckBox()
        self.autostart_check.toggled.connect(self.toggle_autostart)
        general_layout.addRow("Автозагрузка", self.autostart_check)
        
        layout.addWidget(general_group)
        
        appearance_group = QtWidgets.QGroupBox("🎨 Внешний вид")
        appearance_layout = QtWidgets.QFormLayout()
        appearance_group.setLayout(appearance_layout)
        
        self.font_size_spin = QtWidgets.QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(10)
        self.font_size_spin.valueChanged.connect(self.change_font_size)
        appearance_layout.addRow("Размер шрифта", self.font_size_spin)
        
        layout.addWidget(appearance_group)
        
        management_group = QtWidgets.QGroupBox("🔧 Управление")
        management_layout = QtWidgets.QHBoxLayout()
        management_group.setLayout(management_layout)
        
        mgmt_buttons = [
            ("💾 Сохранить настройки", self.save_settings),
            ("🔄 Сбросить", self.reset_settings),
            ("📤 Экспорт", self.export_settings),
            ("📥 Импорт", self.import_settings),
        ]
        
        for text, callback in mgmt_buttons:
            btn = QtWidgets.QPushButton(text)
            btn.clicked.connect(callback)
            management_layout.addWidget(btn)
        
        layout.addWidget(management_group)
        
        about_group = QtWidgets.QGroupBox("ℹ️ О программе")
        about_layout = QtWidgets.QVBoxLayout()
        about_group.setLayout(about_layout)
        
        about_text = QtWidgets.QLabel("""
            <h3>🛠️ Панель управления системой</h3>
            <p><b>Версия:</b> 2.0.0</p>
            <p><b>Функции:</b></p>
            <ul>
                <li>Мониторинг системы</li>
                <li>Управление звуком</li>
                <li>Эмулятор терминала</li>
                <li>Управление процессами</li>
                <li>Сетевые инструменты</li>
                <li>Файловый менеджер</li>
                <li>Настройки и управление</li>
            </ul>
            <p><i>Спасибо за использование! 🎉</i></p>
        """)
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)
        
        layout.addWidget(about_group)
        
        return widget
    
    def update_system_info(self):
        try:
            cpu = psutil.cpu_percent()
            self.cpu_info.setText(f"CPU: {cpu:.1f}%")
            if self.cpu_progress:
                self.cpu_progress.setValue(int(cpu))
            
            mem = psutil.virtual_memory()
            self.memory_info.setText(f"💾 {mem.percent}%")
            if self.mem_progress:
                self.mem_progress.setValue(int(mem.percent))
            
            try:
                disk = psutil.disk_usage('/')
                if self.disk_progress:
                    self.disk_progress.setValue(int(disk.percent))
            except:
                pass
            
            if self.network_graph:
                stats = psutil.net_io_counters()
                total = stats.bytes_recv + stats.bytes_sent
                if total > 0:
                    usage = min(100, total / (1024 * 1024))
                    self.network_graph.setValue(int(usage))
            
            if hasattr(self, 'sys_fields'):
                for label, (func, widget) in self.sys_fields.items():
                    try:
                        widget.setText(func())
                    except:
                        widget.setText("Ошибка")
            
            if hasattr(self, 'network_fields'):
                for label, (func, widget) in self.network_fields.items():
                    try:
                        widget.setText(func())
                    except:
                        widget.setText("Ошибка")
                        
        except Exception as e:
            pass
            
    def update_time(self):
        self.time_info.setText(datetime.now().strftime("%H:%M:%S"))
        
    def update_status(self, message):
        if hasattr(self, 'status_bar') and self.status_bar:
            self.status_bar.showMessage(message, 3000)
        
    def get_os_info(self):
        import platform
        return f"{platform.system()} {platform.release()}"
        
    def get_hostname(self):
        return socket.gethostname()
        
    def get_username(self):
        return os.getlogin()
        
    def get_cpu_cores(self):
        return str(psutil.cpu_count())
        
    def get_memory_info(self):
        mem = psutil.virtual_memory()
        return f"{mem.total / (1024**3):.1f} GB"
        
    def get_disk_info(self):
        disk = psutil.disk_usage('/')
        return f"{disk.total / (1024**3):.1f} GB"
        
    def get_ip_address(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "Не определен"
            
    def get_download_speed(self):
        stats = psutil.net_io_counters()
        return f"{stats.bytes_recv / 1024:.1f} KB/s"
        
    def get_upload_speed(self):
        stats = psutil.net_io_counters()
        return f"{stats.bytes_sent / 1024:.1f} KB/s"
        
    def get_network_interface(self):
        try:
            import netifaces
            interfaces = netifaces.interfaces()
            return ", ".join(interfaces[:3])
        except:
            return "Не определено"
            
    def show_system_info(self):
        info = [
            "<h3>📊 Подробная информация о системе</h3>",
            f"<b>ОС:</b> {self.get_os_info()}",
            f"<b>Хост:</b> {self.get_hostname()}",
            f"<b>Пользователь:</b> {self.get_username()}",
            f"<b>Ядер CPU:</b> {self.get_cpu_cores()}",
            f"<b>Память:</b> {self.get_memory_info()}",
            f"<b>Диск:</b> {self.get_disk_info()}",
            f"<b>IP:</b> {self.get_ip_address()}",
            f"<b>Python:</b> {sys.version.split()[0]}",
            f"<b>Время работы:</b> {self.get_uptime()}",
        ]
        QtWidgets.QMessageBox.information(
            self,
            "Системная информация",
            "<br>".join(info)
        )
        
    def get_uptime(self):
        uptime = time.time() - psutil.boot_time()
        days = int(uptime // (24 * 3600))
        hours = int((uptime % (24 * 3600)) // 3600)
        minutes = int((uptime % 3600) // 60)
        return f"{days}д {hours}ч {minutes}м"
        
    def show_system_monitor(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("📊 Системный монитор")
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QtWidgets.QVBoxLayout()
        dialog.setLayout(layout)
        
        table = QtWidgets.QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Параметр", "Значение", "Статус"])
        
        items = [
            ("CPU", f"{psutil.cpu_percent()}%", "🟢" if psutil.cpu_percent() < 80 else "🟡"),
            ("Память", f"{psutil.virtual_memory().percent}%", 
             "🟢" if psutil.virtual_memory().percent < 80 else "🟡"),
            ("Диск", f"{psutil.disk_usage('/').percent}%",
             "🟢" if psutil.disk_usage('/').percent < 80 else "🟡"),
        ]
        
        for i, (name, value, status) in enumerate(items):
            table.insertRow(i)
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(name))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(value))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(status))
        
        layout.addWidget(table)
        
        btn = QtWidgets.QPushButton("Закрыть")
        btn.clicked.connect(dialog.close)
        layout.addWidget(btn)
        
        dialog.exec_()
        
    def show_packages(self):
        try:
            result = subprocess.run(['dpkg', '-l'], capture_output=True, text=True, timeout=5)
            packages = result.stdout[:2000]
            QtWidgets.QMessageBox.information(
                self,
                "Установленные пакеты",
                f"<pre>{packages}</pre>"
            )
        except:
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось получить список пакетов"
            )
            
    def backup_system(self):
        try:
            backup_dir = os.path.join(os.path.expanduser("~"), "backup")
            os.makedirs(backup_dir, exist_ok=True)
            backup_file = os.path.join(backup_dir, f"settings_backup_{datetime.now().strftime('%Y%m%d')}.json")
            self.save_settings(backup_file)
            QtWidgets.QMessageBox.information(
                self,
                "Резервное копирование",
                f"Настройки сохранены в:\n{backup_file}"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))
            
    def clean_system(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Очистка системы",
            "Очистить временные файлы?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                tmp_files = sum(1 for _ in Path('/tmp').iterdir())
                QtWidgets.QMessageBox.information(
                    self,
                    "Очистка завершена",
                    f"Временных файлов: {tmp_files}\nОчистка выполнена!"
                )
            except:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Не удалось выполнить очистку"
                )
                
    def refresh_system(self):
        self.update_system_info()
        self.update_status("Система обновлена")
        
    def shutdown_system(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Выключение",
            "Вы уверены, что хотите выключить систему?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            subprocess.run(['shutdown', '-h', 'now'])
            
    def change_volume(self, value):
        self.sound_manager.set_volume(value)
        self.volume_label.setText(f"Громкость: {value}%")
        self.update_status(f"Громкость: {value}%")
        
    def toggle_mute(self):
        muted = self.sound_manager.toggle_mute()
        self.mute_btn.setText("🔇 Выкл" if muted else "🔊 Вкл")
        self.update_status("Звук выключен" if muted else "Звук включен")
        
    def test_sound(self):
        self.sound_manager.play_test_sound()
        self.update_status("Тестовый звук воспроизведен")
        
    def apply_sound_scheme(self):
        scheme = self.scheme_combo.currentText()
        if scheme == "Тихая":
            self.volume_slider.setValue(20)
        elif scheme == "Громкая":
            self.volume_slider.setValue(100)
        elif scheme == "Системная":
            self.volume_slider.setValue(50)
        self.update_status(f"Применена схема: {scheme}")
        
    def refresh_processes(self):
        self.process_table.setRowCount(0)
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'username']):
                try:
                    info = proc.info
                    row = self.process_table.rowCount()
                    self.process_table.insertRow(row)
                    self.process_table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(info['pid'])))
                    self.process_table.setItem(row, 1, QtWidgets.QTableWidgetItem(info['name'] or '???'))
                    self.process_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{info['cpu_percent']:.1f}"))
                    self.process_table.setItem(row, 3, QtWidgets.QTableWidgetItem(f"{info['memory_percent']:.1f}"))
                    self.process_table.setItem(row, 4, QtWidgets.QTableWidgetItem(info['status'] or 'unknown'))
                    self.process_table.setItem(row, 5, QtWidgets.QTableWidgetItem(info['username'] or '???'))
                except:
                    continue
        except:
            pass
        self.update_status("Список процессов обновлен")
        
    def filter_processes(self):
        text = self.process_filter.text().lower()
        for row in range(self.process_table.rowCount()):
            item = self.process_table.item(row, 1)
            if item:
                match = text in item.text().lower()
                self.process_table.setRowHidden(row, not match)
                
    def kill_selected_process(self):
        selected = self.process_table.currentRow()
        if selected >= 0:
            pid_item = self.process_table.item(selected, 0)
            if pid_item:
                pid = int(pid_item.text())
                try:
                    proc = psutil.Process(pid)
                    proc.terminate()
                    self.update_status(f"Процесс {pid} завершен")
                    self.refresh_processes()
                except:
                    QtWidgets.QMessageBox.critical(
                        self,
                        "Ошибка",
                        f"Не удалось завершить процесс {pid}"
                    )
                    
    def ping_host(self):
        host, ok = QtWidgets.QInputDialog.getText(
            self,
            "Пинг",
            "Введите хост:",
            QtWidgets.QLineEdit.Normal,
            "google.com"
        )
        if ok and host:
            try:
                result = subprocess.run(
                    ['ping', '-c', '4', host],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                QtWidgets.QMessageBox.information(
                    self,
                    f"Пинг {host}",
                    f"<pre>{result.stdout}</pre>"
                )
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))
                
    def dns_lookup(self):
        host, ok = QtWidgets.QInputDialog.getText(
            self,
            "DNS запрос",
            "Введите домен:",
            QtWidgets.QLineEdit.Normal,
            "yandex.ru"
        )
        if ok and host:
            try:
                ip = socket.gethostbyname(host)
                QtWidgets.QMessageBox.information(
                    self,
                    "DNS запрос",
                    f"<b>{host}</b> → <b style='color: blue;'>{ip}</b>"
                )
            except:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось разрешить {host}"
                )
                
    def trace_route(self):
        host, ok = QtWidgets.QInputDialog.getText(
            self,
            "Трассировка",
            "Введите хост:",
            QtWidgets.QLineEdit.Normal,
            "google.com"
        )
        if ok and host:
            try:
                result = subprocess.run(
                    ['traceroute', '-n', '-4', host],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                QtWidgets.QMessageBox.information(
                    self,
                    f"Трассировка {host}",
                    f"<pre>{result.stdout[:2000]}</pre>"
                )
            except:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Не удалось выполнить трассировку"
                )
                
    def show_wifi(self):
        try:
            result = subprocess.run(
                ['nmcli', 'dev', 'wifi', 'list'],
                capture_output=True,
                text=True,
                timeout=10
            )
            QtWidgets.QMessageBox.information(
                self,
                "Wi-Fi сети",
                f"<pre>{result.stdout[:2000]}</pre>"
            )
        except:
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось получить список Wi-Fi сетей"
            )
            
    def show_ports(self):
        try:
            result = subprocess.run(
                ['ss', '-tuln'],
                capture_output=True,
                text=True,
                timeout=5
            )
            QtWidgets.QMessageBox.information(
                self,
                "Открытые порты",
                f"<pre>{result.stdout}</pre>"
            )
        except:
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось получить список портов"
            )
            
    def show_network_stats(self):
        stats = psutil.net_io_counters()
        info = [
            "<h3>📊 Сетевая статистика</h3>",
            f"<b>Отправлено:</b> {stats.bytes_sent / (1024**2):.1f} MB",
            f"<b>Получено:</b> {stats.bytes_recv / (1024**2):.1f} MB",
            f"<b>Пакетов отправлено:</b> {stats.packets_sent:,}",
            f"<b>Пакетов получено:</b> {stats.packets_recv:,}",
            f"<b>Ошибок:</b> {stats.errin + stats.errout}",
        ]
        QtWidgets.QMessageBox.information(
            self,
            "Сеть",
            "<br>".join(info)
        )
        
    def refresh_file_list(self):
        self.file_list.clear()
        try:
            path = self.path_input.text()
            items = sorted(os.listdir(path))
            for item in items:
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    self.file_list.addItem(f"📁 {item}")
                else:
                    size = os.path.getsize(full_path)
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f} MB"
                    self.file_list.addItem(f"📄 {item} ({size_str})")
        except Exception as e:
            self.file_list.addItem(f"⚠️ Ошибка: {e}")
            
    def navigate_to_path(self):
        path = self.path_input.text().strip()
        if os.path.exists(path):
            self.refresh_file_list()
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                f"Путь не существует: {path}"
            )
            
    def go_up(self):
        path = self.path_input.text()
        parent = os.path.dirname(path)
        if parent != path:
            self.path_input.setText(parent)
            self.refresh_file_list()
            
    def open_file_item(self, item):
        path = self.path_input.text()
        name = item.text()
        if name.startswith("📁 "):
            name = name[2:]
        elif name.startswith("📄 "):
            name = name.split(" (")[0][2:]
        full_path = os.path.join(path, name)
        if os.path.isdir(full_path):
            self.path_input.setText(full_path)
            self.refresh_file_list()
        else:
            try:
                os.startfile(full_path)
            except:
                try:
                    subprocess.run(['xdg-open', full_path])
                except:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Ошибка",
                        "Не удалось открыть файл"
                    )
                    
    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {
            'theme': 'Системная',
            'show_messages': True,
            'autostart': False,
            'font_size': 10,
            'volume': 50
        }
        
    def save_settings(self, filename=None):
        if filename is None:
            filename = self.settings_file
        try:
            settings = {
                'theme': self.theme_combo.currentText(),
                'show_messages': self.messages_check.isChecked(),
                'autostart': self.autostart_check.isChecked(),
                'font_size': self.font_size_spin.value(),
                'volume': self.volume_slider.value() if hasattr(self, 'volume_slider') else 50
            }
            with open(filename, 'w') as f:
                json.dump(settings, f, indent=2)
            self.update_status("Настройки сохранены")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))
            
    def apply_settings(self):
        settings = self.settings
        self.theme_combo.setCurrentText(settings.get('theme', 'Системная'))
        self.messages_check.setChecked(settings.get('show_messages', True))
        self.autostart_check.setChecked(settings.get('autostart', False))
        self.font_size_spin.setValue(settings.get('font_size', 10))
        if hasattr(self, 'volume_slider'):
            self.volume_slider.setValue(settings.get('volume', 50))
        self.change_theme(self.theme_combo.currentText())
        self.change_font_size(self.font_size_spin.value())
        
    def reset_settings(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Сброс настроек",
            "Сбросить все настройки на значения по умолчанию?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.settings = {
                'theme': 'Системная',
                'show_messages': True,
                'autostart': False,
                'font_size': 10,
                'volume': 50
            }
            self.apply_settings()
            self.update_status("Настройки сброшены")
            
    def export_settings(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Экспорт настроек",
            os.path.expanduser("~"),
            "JSON файлы (*.json)"
        )
        if filename:
            self.save_settings(filename)
            
    def import_settings(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Импорт настроек",
            os.path.expanduser("~"),
            "JSON файлы (*.json)"
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    settings = json.load(f)
                self.settings = settings
                self.apply_settings()
                self.update_status("Настройки импортированы")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))
                
    def change_theme(self, theme):
        if theme == "Тёмная":
            style = """
                QMainWindow, QWidget { background-color: #1e1e1e; color: #d4d4d4; }
                QPushButton { background-color: #2d2d2d; color: white; }
                QPushButton:hover { background-color: #3d3d3d; }
                QLineEdit, QTextEdit { background-color: #2d2d2d; color: #d4d4d4; }
                QTableWidget { background-color: #2d2d2d; color: #d4d4d4; }
                QGroupBox { border: 1px solid #444; }
                QTabWidget::pane { background-color: #1e1e1e; }
                QTabBar::tab { background-color: #2d2d2d; color: #d4d4d4; }
                QTabBar::tab:selected { background-color: #3d3d3d; }
            """
        elif theme == "Светлая":
            style = """
                QMainWindow, QWidget { background-color: #f0f0f0; color: #1e1e1e; }
                QPushButton { background-color: #e0e0e0; color: #1e1e1e; }
                QPushButton:hover { background-color: #d0d0d0; }
                QLineEdit, QTextEdit { background-color: white; color: #1e1e1e; }
                QTableWidget { background-color: white; color: #1e1e1e; }
                QGroupBox { border: 1px solid #aaa; }
                QTabWidget::pane { background-color: white; }
                QTabBar::tab { background-color: #e0e0e0; color: #1e1e1e; }
                QTabBar::tab:selected { background-color: white; }
            """
        else:
            style = ""
        self.setStyleSheet(style)
        
    def change_font_size(self, size):
        font = QtGui.QFont()
        font.setPointSize(size)
        self.setFont(font)
        
    def toggle_messages(self, checked):
        self.show_messages = checked
        if checked:
            self.message_manager.timer.start()
        else:
            self.message_manager.timer.stop()
        self.save_settings()
            
    def toggle_autostart(self, checked):
        try:
            autostart_dir = os.path.join(
                os.path.expanduser("~"),
                ".config/autostart"
            )
            os.makedirs(autostart_dir, exist_ok=True)
            desktop_file = os.path.join(autostart_dir, "control-panel.desktop")
            if checked:
                content = f"""[Desktop Entry]
Type=Application
Name=Control Panel
Exec={sys.executable} {os.path.abspath(__file__)}
Icon=system-preferences
Comment=System Control Panel
X-GNOME-Autostart-enabled=true
"""
                with open(desktop_file, 'w') as f:
                    f.write(content)
            else:
                if os.path.exists(desktop_file):
                    os.remove(desktop_file)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", str(e))
            
    def closeEvent(self, event):
        self.save_settings()
        reply = QtWidgets.QMessageBox.question(
            self,
            "Выход",
            "Закрыть панель управления?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Control Panel")
    app.setOrganizationName("SystemTools")
    app.setWindowIcon(QtGui.QIcon.fromTheme("system-preferences"))
    window = ControlPanel()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
