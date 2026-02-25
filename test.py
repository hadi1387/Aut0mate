import sys
import os
import json
import pyautogui
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLabel, QMessageBox, QSpinBox, QFileDialog, QFrame,
    QDialog, QLineEdit, QInputDialog
)
from PySide6.QtCore import Qt, QTimer, QObject, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from pynput import mouse as pynput_mouse

# --- Click Handler ---
class ClickHandler(QObject):
    click_detected = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.listener = None
        self.running = False

    def start_listening(self):
        if self.running:
            return
        self.running = True

        def on_click(x, y, button, pressed):
            if pressed and button == pynput_mouse.Button.left:
                self.click_detected.emit(x, y)
                return False

        self.listener = pynput_mouse.Listener(on_click=on_click)
        self.listener.start()

    def stop_listening(self):
        self.running = False
        if self.listener:
            self.listener.stop()
            self.listener = None
# ----------------------------------

# --- Editor Dialog ---
class ActionEditorDialog(QDialog):
    def __init__(self, parent, actions):
        super().__init__(parent)
        self.setWindowTitle("ویرایش دستورات")
        self.setModal(True)
        self.resize(480, 380)
        self.actions = actions.copy()
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("ویرایش دستورات")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #4dabf7; margin: 10px;")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setFont(QFont("Vazir", 11))
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 6px;
                outline: 0;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #2d2d2d;
                text-align: center;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
        """)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_up = QPushButton("↑ بالا")
        self.btn_down = QPushButton("↓ پایین")
        self.btn_edit = QPushButton("ویرایش متن")
        self.btn_save = QPushButton("ذخیره و بستن")

        for btn in [self.btn_up, self.btn_down, self.btn_edit, self.btn_save]:
            btn.setFixedHeight(36)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    border: 1px solid #444444;
                    border-radius: 6px;
                    font-size: 13px;
                    color: #ffffff;
                    text-align: center;
                    padding: 0 10px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                }
                QPushButton:disabled {
                    background-color: #1e1e1e;
                    color: #666666;
                }
            """)

        btn_layout.addWidget(self.btn_up)
        btn_layout.addWidget(self.btn_down)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        self.btn_up.clicked.connect(self.move_up)
        self.btn_down.clicked.connect(self.move_down)
        self.btn_edit.clicked.connect(self.edit_selected)
        self.btn_save.clicked.connect(self.save_and_close)

        self.update_list()

    def update_list(self):
        self.list_widget.clear()
        for i, action in enumerate(self.actions):
            act_type = action[0]
            if act_type == 'move':
                self.list_widget.addItem(f"{i+1}. حرکت به ({action[1]}, {action[2]})")
            elif act_type == 'click':
                self.list_widget.addItem(f"{i+1}. کلیک در ({action[1]}, {action[2]})")
            elif act_type == 'show_mouse':
                self.list_widget.addItem(f"{i+1}. مختصات ماوس: ({action[1]}, {action[2]})")
            elif act_type == 'show_screen':
                self.list_widget.addItem(f"{i+1}. اندازه صفحه: {action[1]} × {action[2]}")
            elif act_type == 'type':
                self.list_widget.addItem(f"{i+1}. تایپ: '{action[1]}' در ({action[2]}, {action[3]})")

    def move_up(self):
        current_row = self.list_widget.currentRow()
        if current_row <= 0:
            return
        item = self.actions.pop(current_row)
        self.actions.insert(current_row - 1, item)
        self.update_list()
        self.list_widget.setCurrentRow(current_row - 1)

    def move_down(self):
        current_row = self.list_widget.currentRow()
        if current_row >= len(self.actions) - 1:
            return
        item = self.actions.pop(current_row)
        self.actions.insert(current_row + 1, item)
        self.update_list()
        self.list_widget.setCurrentRow(current_row + 1)

    def edit_selected(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "هشدار", "هیچ دستوری انتخاب نشده است.")
            return
        action = self.actions[current_row]
        if action[0] != 'type':
            QMessageBox.information(self, "توجه", "فقط دستورات تایپ قابل ویرایش هستند.")
            return
        old_text = action[1]
        new_text, ok = QInputDialog.getText(
            self,
            "ویرایش متن",
            "متن جدید را وارد کنید:",
            text=old_text
        )
        if ok and new_text.strip():
            self.actions[current_row] = ('type', new_text, action[2], action[3])
            self.update_list()

    def save_and_close(self):
        self.parent.actions = self.actions.copy()
        self.parent.update_button_states()
        self.parent.list_widget.clear()
        for act in self.parent.actions:
            act_type = act[0]
            if act_type == 'move':
                self.parent.list_widget.addItem(f"حرکت به ({act[1]}, {act[2]})")
            elif act_type == 'click':
                self.parent.list_widget.addItem(f"کلیک در ({act[1]}, {act[2]})")
            elif act_type == 'show_mouse':
                self.parent.list_widget.addItem(f"مختصات ماوس: ({act[1]}, {act[2]})")
            elif act_type == 'show_screen':
                self.parent.list_widget.addItem(f"اندازه صفحه: {act[1]} × {act[2]}")
            elif act_type == 'type':
                self.parent.list_widget.addItem(f"تایپ: '{act[1]}' در ({act[2]}, {act[3]})")
        self.accept()

# ----------------------------------

class ActionRecorder(QMainWindow):
    def __init__(self):
        super().__init__()
        self.actions = []
        self.undo_stack = []
        self.redo_stack = []
        self.replay_count = 1
        self.delay_between_actions = 0.3
        self.waiting_for_click = False
        self.pending_action_type = None
        self.pending_text = None
        self.click_handler = ClickHandler()
        self.click_handler.click_detected.connect(self.on_user_click)
        self.init_ui()
        self.setup_shortcuts()

    def init_ui(self):
        self.setWindowTitle("ضبط‌کننده حرکات ماوس")
        self.resize(600, 680)  # ✅ Smaller window: 600x680
        QApplication.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Title Card
        title_card = QFrame()
        title_card.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 10px;
                padding: 14px;
                border: 1px solid #333333;
            }
        """)
        title_layout = QVBoxLayout(title_card)
        title = QLabel("ضبط و اجرای خودکار حرکات ماوس")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4dabf7;")
        title_layout.addWidget(title)
        main_layout.addWidget(title_card)

        # Action Buttons Group
        actions_card = QFrame()
        actions_card.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 10px;
                padding: 14px;
                border: 1px solid #333333;
            }
        """)
        actions_layout = QVBoxLayout(actions_card)
        actions_layout.setSpacing(9)

        self.btn_move = QPushButton("۱. ضبط حرکت به موقعیتی که کلیک می‌کنید")
        self.btn_click = QPushButton("۲. ضبط کلیک در موقعیتی که کلیک می‌کنید")
        self.btn_mouse_pos = QPushButton("۳. ضبط مختصات فعلی ماوس")
        self.btn_screen_size = QPushButton("۵. ضبط اندازه صفحه‌نمایش")
        self.btn_type = QPushButton("۶. ضبط تایپ متن در موقعیتی که کلیک می‌کنید")
        self.btn_edit = QPushButton("۷. ویرایش دستورات")
        self.btn_delay = QPushButton("۸. تنظیم تأخیر بین دستورات (ثانیه)")

        buttons = [self.btn_move, self.btn_click, self.btn_mouse_pos, self.btn_screen_size, self.btn_type, self.btn_edit, self.btn_delay]
        for btn in buttons:
            btn.setFixedHeight(42)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    border: 1px solid #444444;
                    border-radius: 7px;
                    text-align: center;
                    padding: 0 10px;
                    font-size: 13px;
                    color: #ffffff;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                    border: 1px solid #555555;
                }
                QPushButton:pressed {
                    background-color: #444444;
                }
                QPushButton:disabled {
                    background-color: #1e1e1e;
                    color: #666666;
                    border: 1px solid #333333;
                }
            """)
            actions_layout.addWidget(btn)

        main_layout.addWidget(actions_card)

        # Controls Group
        controls_card = QFrame()
        controls_card.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 10px;
                padding: 14px;
                border: 1px solid #333333;
            }
        """)
        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setSpacing(12)

        # Replay row
        replay_layout = QHBoxLayout()
        replay_label = QLabel("تعداد دفعات اجرا:")
        replay_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        replay_label.setStyleSheet("font-size: 13px; color: #ffffff;")
        self.spin_replay = QSpinBox()
        self.spin_replay.setRange(1, 100)
        self.spin_replay.setValue(1)
        self.spin_replay.setFixedWidth(70)
        self.spin_replay.setStyleSheet("""
            QSpinBox {
                background-color: #2d2d2d;
                border: 1px solid #444444;
                border-radius: 5px;
                padding: 3px;
                color: #ffffff;
                selection-background-color: #4dabf7;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #1e1e1e;
                border: 1px solid #444444;
                width: 18px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #3a3a3a;
            }
        """)
        self.btn_set_replay = QPushButton("۴. تنظیم تعداد اجرا")
        self.btn_set_replay.setFixedWidth(150)
        self.btn_set_replay.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #444444;
                border-radius: 7px;
                font-size: 13px;
                color: #ffffff;
                text-align: center;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """)
        replay_layout.addWidget(self.btn_set_replay)
        replay_layout.addWidget(self.spin_replay)
        replay_layout.addWidget(replay_label)
        replay_layout.addStretch()
        controls_layout.addLayout(replay_layout)

        # Save/Load row
        save_load_layout = QHBoxLayout()
        self.btn_save = QPushButton("ذخیره دستورات")
        self.btn_load = QPushButton("بارگذاری دستورات")
        for btn in [self.btn_save, self.btn_load]:
            btn.setFixedHeight(38)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    border: 1px solid #444444;
                    border-radius: 7px;
                    font-size: 13px;
                    color: #ffffff;
                    text-align: center;
                    padding: 0 10px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                }
            """)
        save_load_layout.addWidget(self.btn_save)
        save_load_layout.addWidget(self.btn_load)
        controls_layout.addLayout(save_load_layout)

        # Undo/Redo/Clear row
        edit_layout = QHBoxLayout()
        self.btn_undo = QPushButton("واگرد (Ctrl+Z)")
        self.btn_redo = QPushButton("بازگردانی (Ctrl+Y)")
        self.btn_clear = QPushButton("پاک‌کردن همه")
        for btn in [self.btn_undo, self.btn_redo, self.btn_clear]:
            btn.setFixedHeight(38)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    border: 1px solid #444444;
                    border-radius: 7px;
                    font-size: 13px;
                    color: #ffffff;
                    text-align: center;
                    padding: 0 10px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                }
                QPushButton:disabled {
                    background-color: #1e1e1e;
                    color: #666666;
                }
            """)
        edit_layout.addWidget(self.btn_clear)
        edit_layout.addWidget(self.btn_redo)
        edit_layout.addWidget(self.btn_undo)
        controls_layout.addLayout(edit_layout)

        main_layout.addWidget(controls_card)

        # Actions List
        list_label = QLabel("دستورات ضبط‌شده:")
        list_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        list_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff; margin-top: 8px;")
        main_layout.addWidget(list_label)

        self.list_widget = QListWidget()
        self.list_widget.setFont(QFont("Vazir", 11))
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 6px;
                outline: 0;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #2d2d2d;
                text-align: center;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
        """)
        main_layout.addWidget(self.list_widget)

        # Execute Button
        self.btn_execute = QPushButton("اجرای دستورات")
        self.btn_execute.setFixedHeight(48)
        self.btn_execute.setStyleSheet("""
            QPushButton {
                background-color: #4dabf7;
                color: #000000;
                border-radius: 9px;
                font-size: 15px;
                font-weight: bold;
                text-align: center;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #339af0;
            }
            QPushButton:pressed {
                background-color: #228be6;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
        """)
        main_layout.addWidget(self.btn_execute)

        # Connect signals
        self.btn_move.clicked.connect(lambda: self.prepare_for_position_capture('move'))
        self.btn_click.clicked.connect(lambda: self.prepare_for_position_capture('click'))
        self.btn_mouse_pos.clicked.connect(self.add_mouse_pos_action)
        self.btn_screen_size.clicked.connect(self.add_screen_size_action)
        self.btn_type.clicked.connect(self.prepare_for_type_capture)
        self.btn_edit.clicked.connect(self.open_editor)
        self.btn_delay.clicked.connect(self.set_delay_between_actions)
        self.btn_set_replay.clicked.connect(self.set_replay_count)
        self.btn_clear.clicked.connect(self.clear_all_actions)
        self.btn_execute.clicked.connect(self.execute_actions)
        self.btn_save.clicked.connect(self.save_actions)
        self.btn_load.clicked.connect(self.load_actions)
        self.btn_undo.clicked.connect(self.undo_action)
        self.btn_redo.clicked.connect(self.redo_action)

        font = QFont()
        font.setFamilies(["Vazir", "IRANSans", "B Nazanin", "Arial", "sans-serif"])
        font.setPointSize(12)
        QApplication.setFont(font)

        self.update_button_states()

    def setup_shortcuts(self):
        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.activated.connect(self.undo_action)
        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.redo_shortcut.activated.connect(self.redo_action)

    def add_action_to_history(self, action):
        self.actions.append(action)
        self.undo_stack.append(action)
        self.redo_stack.clear()
        self.update_button_states()

    def undo_action(self):
        if not self.undo_stack:
            return
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        self.actions.pop()
        self.list_widget.takeItem(self.list_widget.count() - 1)
        self.update_button_states()

    def redo_action(self):
        if not self.redo_stack:
            return
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        self.actions.append(action)
        act_type = action[0]
        if act_type == 'move':
            self.list_widget.addItem(f"حرکت به ({action[1]}, {action[2]})")
        elif act_type == 'click':
            self.list_widget.addItem(f"کلیک در ({action[1]}, {action[2]})")
        elif act_type == 'show_mouse':
            self.list_widget.addItem(f"مختصات ماوس: ({action[1]}, {action[2]})")
        elif act_type == 'show_screen':
            self.list_widget.addItem(f"اندازه صفحه: {action[1]} × {action[2]}")
        elif act_type == 'type':
            self.list_widget.addItem(f"تایپ: '{action[1]}' در ({action[2]}, {action[3]})")
        self.update_button_states()

    def update_button_states(self):
        self.btn_undo.setEnabled(len(self.undo_stack) > 0)
        self.btn_redo.setEnabled(len(self.redo_stack) > 0)
        self.btn_clear.setEnabled(len(self.actions) > 0)
        self.btn_execute.setEnabled(len(self.actions) > 0)

    # --- Action recording ---
    def prepare_for_type_capture(self):
        if self.waiting_for_click:
            return
        self.pending_action_type = 'type'
        self.waiting_for_click = True
        for btn in self.get_all_buttons():
            btn.setEnabled(False)
        QMessageBox.information(
            self,
            "در انتظار کلیک",
            "لطفاً در جایی که می‌خواهید متن تایپ شود، کلیک کنید."
        )
        self.click_handler.start_listening()

    def on_user_click(self, x, y):
        if not self.waiting_for_click:
            return
        self.waiting_for_click = False
        self.click_handler.stop_listening()

        if self.pending_action_type == 'move':
            action = ('move', x, y)
            self.list_widget.addItem(f"حرکت به ({x}, {y})")
            self.add_action_to_history(action)
            QMessageBox.information(self, "موفق", f"موقعیت ({x}, {y}) برای حرکت ضبط شد.")

        elif self.pending_action_type == 'click':
            action = ('click', x, y)
            self.list_widget.addItem(f"کلیک در ({x}, {y})")
            self.add_action_to_history(action)
            QMessageBox.information(self, "موفق", f"موقعیت ({x}, {y}) برای کلیک ضبط شد.")

        elif self.pending_action_type == 'type':
            text, ok = QInputDialog.getText(self, "تایپ متن", "متن مورد نظر را وارد کنید:")
            if ok and text.strip():
                action = ('type', text, x, y)
                self.list_widget.addItem(f"تایپ: '{text}' در ({x}, {y})")
                self.add_action_to_history(action)
                QMessageBox.information(self, "موفق", f"متن برای تایپ در ({x}, {y}) ضبط شد.")
            else:
                QMessageBox.warning(self, "لغو", "تایپ لغو شد.")

        for btn in self.get_all_buttons():
            btn.setEnabled(True)

    def open_editor(self):
        if not self.actions:
            QMessageBox.warning(self, "هشدار", "هیچ دستوری برای ویرایش وجود ندارد!")
            return
        editor = ActionEditorDialog(self, self.actions)
        editor.exec()

    def add_mouse_pos_action(self):
        x, y = pyautogui.position()
        action = ('show_mouse', x, y)
        self.add_action_to_history(action)
        self.list_widget.addItem(f"مختصات ماوس: ({x}, {y})")
        QMessageBox.information(self, "موفق", f"مختصات فعلی ({x}, {y}) ضبط شد.")

    def add_screen_size_action(self):
        w, h = pyautogui.size()
        action = ('show_screen', w, h)
        self.add_action_to_history(action)
        self.list_widget.addItem(f"اندازه صفحه: {w} × {h}")
        QMessageBox.information(self, "موفق", f"اندازه صفحه ({w} × {h}) ضبط شد.")

    def clear_all_actions(self):
        reply = QMessageBox.question(self, "تأیید", "همه دستورات پاک شوند؟", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.actions.clear()
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.list_widget.clear()
            self.update_button_states()
            QMessageBox.information(self, "پاک‌شده", "همه دستورات حذف شدند.")

    def save_actions(self):
        if not self.actions:
            QMessageBox.warning(self, "هشدار", "هیچ دستوری برای ذخیره نیست!")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره دستورات", "", "فایل ضبط ماوس (*.rec);;All Files (*)"
        )
        if file_path:
            if not file_path.endswith(".rec"):
                file_path += ".rec"
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.actions, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "موفق", "دستورات ذخیره شدند.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"ذخیره ناموفق:\n{str(e)}")

    def load_actions(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "بارگذاری دستورات", "", "فایل ضبط ماوس (*.rec);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                self.actions = [tuple(item) for item in loaded]
                self.undo_stack = self.actions.copy()
                self.redo_stack.clear()
                self.list_widget.clear()
                for act in self.actions:
                    act_type = act[0]
                    if act_type == 'move':
                        self.list_widget.addItem(f"حرکت به ({act[1]}, {act[2]})")
                    elif act_type == 'click':
                        self.list_widget.addItem(f"کلیک در ({act[1]}, {act[2]})")
                    elif act_type == 'show_mouse':
                        self.list_widget.addItem(f"مختصات ماوس: ({act[1]}, {act[2]})")
                    elif act_type == 'show_screen':
                        self.list_widget.addItem(f"اندازه صفحه: {act[1]} × {act[2]}")
                    elif act_type == 'type':
                        self.list_widget.addItem(f"تایپ: '{act[1]}' در ({act[2]}, {act[3]})")
                self.update_button_states()
                QMessageBox.information(self, "موفق", "دستورات بارگذاری شدند.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"بارگذاری ناموفق:\n{str(e)}")

    def set_replay_count(self):
        self.replay_count = self.spin_replay.value()
        QMessageBox.information(self, "موفق", f"تعداد اجرا: {self.replay_count}")

    def set_delay_between_actions(self):
        # ❌ PySide6 QInputDialog.getDouble does NOT support min/max → removed
        delay, ok = QInputDialog.getDouble(
            self,
            "تنظیم تأخیر",
            "تأخیر بین هر دستور (ثانیه):",
            value=self.delay_between_actions,
            decimals=1
        )
        if ok:
            # ✅ Manual validation
            if delay < 0:
                delay = 0.0
            elif delay > 5.0:
                delay = 5.0
            self.delay_between_actions = delay
            QMessageBox.information(self, "موفق", f"تأخیر بین دستورات: {delay} ثانیه")

    def execute_actions(self):
        if not self.actions:
            QMessageBox.warning(self, "هشدار", "هیچ دستوری برای اجرا نیست!")
            return
        QMessageBox.information(
            self,
            "آماده‌سازی",
            f"اجرای دستورات آغاز می‌شود!\nلطفاً به پنجره مورد نظر بروید.\nتعداد اجرا: {self.replay_count}"
        )
        QTimer.singleShot(100, self._run_execution)

    def _run_execution(self):
        try:
            for run in range(self.replay_count):
                for i, action in enumerate(self.actions):
                    act_type = action[0]
                    if act_type == 'move':
                        _, x, y = action
                        duration = min(0.5, self.delay_between_actions)
                        pyautogui.moveTo(x, y, duration=duration)
                    elif act_type == 'click':
                        _, x, y = action
                        pyautogui.click(x, y)
                    elif act_type == 'type':
                        _, text, x, y = action
                        pyautogui.click(x, y)
                        pyautogui.write(text, interval=0.05)

                    # Delay after each action (except after last action of last run)
                    if not (run == self.replay_count - 1 and i == len(self.actions) - 1):
                        time.sleep(self.delay_between_actions)
            QMessageBox.information(self, "پایان", "اجرای دستورات با موفقیت انجام شد!")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در اجرا:\n{str(e)}")

    def get_all_buttons(self):
        return [
            self.btn_move, self.btn_click, self.btn_mouse_pos, self.btn_screen_size, self.btn_type, self.btn_edit, self.btn_delay,
            self.btn_set_replay, self.btn_clear, self.btn_execute,
            self.btn_save, self.btn_load, self.btn_undo, self.btn_redo
        ]

# === Main ===
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Mouse Action Recorder")

    app.setStyleSheet("""
        * {
            background-color: #121212;
            color: #ffffff;
            font-family: 'Vazir', 'IRANSans', 'B Nazanin', 'Arial', 'sans-serif';
            font-size: 12px;
        }
        QPushButton {
            background-color: #2d2d2d;
            border: 1px solid #444444;
            border-radius: 7px;
            padding: 5px 10px;
            text-align: center;
            color: #ffffff;
        }
        QPushButton:hover {
            background-color: #3a3a3a;
        }
        QPushButton:pressed {
            background-color: #444444;
        }
        QPushButton:disabled {
            background-color: #1e1e1e;
            color: #666666;
        }
        QSpinBox {
            background-color: #2d2d2d;
            border: 1px solid #444444;
            border-radius: 5px;
            padding: 3px;
            color: #ffffff;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            background-color: #1e1e1e;
            border: 1px solid #444444;
            width: 18px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #3a3a3a;
        }
        QListWidget {
            background-color: #1e1e1e;
            border: 1px solid #333333;
            border-radius: 8px;
            padding: 6px;
            color: #ffffff;
        }
        QListWidget::item {
            padding: 5px;
            border-bottom: 1px solid #2d2d2d;
            text-align: center;
        }
        QListWidget::item:last {
            border-bottom: none;
        }
        QLabel {
            color: #ffffff;
        }
        QMessageBox {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QMessageBox QLabel {
            color: #ffffff;
        }
        QMessageBox QPushButton {
            background-color: #2d2d2d;
            border: 1px solid #444444;
            border-radius: 6px;
            padding: 5px 10px;
            font-size: 12px;
            color: #ffffff;
            text-align: center;
        }
        QMessageBox QPushButton:hover {
            background-color: #3a3a3a;
        }
        QInputDialog {
            background-color: #1e1e1e;
        }
        QInputDialog QLabel {
            color: #ffffff;
        }
        QInputDialog QLineEdit {
            background-color: #2d2d2d;
            border: 1px solid #444444;
            border-radius: 4px;
            padding: 4px;
            color: #ffffff;
        }
    """)

    window = ActionRecorder()
    window.show()
    sys.exit(app.exec())