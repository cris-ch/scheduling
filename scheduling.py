import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QComboBox, QListWidget, 
                             QTextEdit, QGridLayout, QScrollArea, QTabWidget, QMessageBox,
                             QFileDialog, QCheckBox, QStatusBar, QCalendarWidget, QSplitter)
from PyQt6.QtCore import Qt, QSize, QDate, QPoint, pyqtSignal, QObject, QEvent, QPointF
from PyQt6.QtGui import QColor, QPalette, QShortcut, QKeySequence, QIcon, QMouseEvent, QCursor, QFont
from datetime import time, datetime, timedelta
import json
from collections import defaultdict

class Student:
    def __init__(self, name, level, availability, twice_weekly):
        self.name = name
        self.level = level
        self.availability = availability
        self.twice_weekly = twice_weekly
        self.scheduled_days = 0

class AvailabilityButton(QPushButton):
    def __init__(self, day, time, parent, is_teacher=True):
        super().__init__(parent)
        self.day = day
        self.time = time
        self.is_teacher = is_teacher
        self.parent_window = parent
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            QPushButton {
                border: 1px solid #BDC3C7;
                border-radius: 2px;
                background-color: #ECF0F1;
            }
            QPushButton:checked {
                background-color: #2ECC71;
            }
            QPushButton:hover {
                background-color: #3498DB;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_window.start_drag(self)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.parent_window.continue_drag(self, event.pos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_window.end_drag()
        super().mouseReleaseEvent(event)

class AcademySchedulerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Academy Scheduler")
        self.setGeometry(100, 100, 1300, 900)

        self.set_style()

        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        self.levels = ['Kids I', 'Kids II', 'Kids III', 'Pre-Teens I', 'Pre-Teens II', 'Pre-Teens III', 
                       'Teens I', 'Teens II', 'Teens III', 'B1+', 'First']
        self.teacher_availability = {day: set() for day in self.days}
        self.students = []
        self.selected_student = None

        self.is_dragging = False
        self.drag_start_state = None
        self.last_dragged_button = None

        self.create_widgets()
        self.create_shortcuts()
        self.statusBar().showMessage("Welcome to Academy Scheduler")

        self.student_availability = {day: set() for day in self.days}

    def set_style(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 248, 255))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(44, 62, 80))
        palette.setColor(QPalette.ColorRole.Button, QColor(52, 152, 219))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(46, 204, 113))
        self.setPalette(palette)

        font = QFont()
        font.setPointSize(11)
        QApplication.setFont(font)

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #F0F8FF;
            }
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QPushButton:pressed {
                background-color: #2C3E50;
            }
            QLineEdit, QComboBox, QTextEdit {
                background-color: white;
                border: 1px solid #BDC3C7;
                padding: 3px;
                border-radius: 3px;
            }
            QTabWidget::pane {
                border: 1px solid #BDC3C7;
                border-radius: 3px;
            }
            QTabBar::tab {
                background-color: #ECF0F1;
                color: #2C3E50;
                border: 1px solid #BDC3C7;
                padding: 5px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            QTabBar::tab:selected {
                background-color: #3498DB;
                color: white;
            }
            QListWidget, QScrollArea {
                background-color: white;
                border: 1px solid #BDC3C7;
                border-radius: 3px;
            }
            QLabel {
                color: #2C3E50;
            }
            QCheckBox {
                color: #2C3E50;
            }
            QStatusBar {
                background-color: #ECF0F1;
                color: #2C3E50;
            }
        """)

    def create_widgets(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        self.teacher_widget = QWidget()
        self.student_widget = QWidget()
        self.schedule_widget = QWidget()

        tab_widget.addTab(self.teacher_widget, QIcon("icons/teacher.png"), "Teacher Availability")
        tab_widget.addTab(self.student_widget, QIcon("icons/student.png"), "Student Information")
        tab_widget.addTab(self.schedule_widget, QIcon("icons/schedule.png"), "Schedule")

        self.create_teacher_availability_widget()
        self.create_student_info_widget()
        self.create_schedule_widget()

        button_layout = QHBoxLayout()
        save_button = QPushButton(QIcon("icons/save.png"), "Save Data")
        load_button = QPushButton(QIcon("icons/load.png"), "Load Data")
        save_button.clicked.connect(self.save_data)
        load_button.clicked.connect(self.load_data)
        button_layout.addWidget(save_button)
        button_layout.addWidget(load_button)
        main_layout.addLayout(button_layout)

        self.setStatusBar(QStatusBar())

    def create_teacher_availability_widget(self):
        layout = QVBoxLayout(self.teacher_widget)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QGridLayout(scroll_widget)
        scroll_layout.setHorizontalSpacing(1)
        scroll_layout.setVerticalSpacing(1)

        times = [time(hour=h, minute=m).strftime("%H:%M") for h in range(8, 22) for m in (0, 30)]

        for col, day in enumerate(self.days):
            label = QLabel(day)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scroll_layout.addWidget(label, 0, col + 1)

        for row, t in enumerate(times):
            time_label = QLabel(t)
            time_label.setFixedWidth(40)
            time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            scroll_layout.addWidget(time_label, row + 1, 0)
            for col, day in enumerate(self.days):
                btn = AvailabilityButton(day, t, self, is_teacher=True)
                btn.setFixedSize(QSize(25, 25))
                btn.setToolTip(f"Click to toggle availability for {day} at {t}")
                scroll_layout.addWidget(btn, row + 1, col + 1)

        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        scroll_area.setObjectName("TeacherScrollArea")

    def create_student_info_widget(self):
        layout = QVBoxLayout(self.student_widget)

        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("Name:"))
        self.name_entry = QLineEdit()
        form_layout.addWidget(self.name_entry)
        form_layout.addWidget(QLabel("Level:"))
        self.level_dropdown = QComboBox()
        self.level_dropdown.addItems(self.levels)
        form_layout.addWidget(self.level_dropdown)
        self.twice_weekly_checkbox = QCheckBox("Twice Weekly")
        form_layout.addWidget(self.twice_weekly_checkbox)
        layout.addLayout(form_layout)

        availability_scroll = QScrollArea()
        availability_scroll.setWidgetResizable(True)
        availability_widget = QWidget()
        availability_layout = QGridLayout(availability_widget)
        availability_layout.setHorizontalSpacing(1)
        availability_layout.setVerticalSpacing(1)
        self.student_availability = {day: set() for day in self.days}

        times = [time(hour=h, minute=m).strftime("%H:%M") for h in range(12, 22) for m in (0, 30)]

        for col, day in enumerate(self.days):
            label = QLabel(day)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            availability_layout.addWidget(label, 0, col + 1)

        for row, t in enumerate(times):
            time_label = QLabel(t)
            time_label.setFixedWidth(40)
            time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            availability_layout.addWidget(time_label, row + 1, 0)
            for col, day in enumerate(self.days):
                btn = AvailabilityButton(day, t, self, is_teacher=False)
                btn.setFixedSize(QSize(25, 25))
                btn.setToolTip(f"Click to toggle availability for {day} at {t}")
                availability_layout.addWidget(btn, row + 1, col + 1)

        availability_scroll.setWidget(availability_widget)
        layout.addWidget(availability_scroll)
        availability_scroll.setObjectName("StudentScrollArea")

        button_layout = QHBoxLayout()
        self.add_button = QPushButton(QIcon("icons/add.png"), "Add Student")
        self.add_button.setToolTip("Add a new student")
        self.add_button.clicked.connect(self.add_student)
        button_layout.addWidget(self.add_button)
        
        self.modify_button = QPushButton(QIcon("icons/modify.png"), "Modify Student")
        self.modify_button.setToolTip("Modify selected student")
        self.modify_button.clicked.connect(self.modify_student)
        self.modify_button.setEnabled(False)
        button_layout.addWidget(self.modify_button)
        
        self.delete_button = QPushButton(QIcon("icons/delete.png"), "Delete Student")
        self.delete_button.setToolTip("Delete selected student")
        self.delete_button.clicked.connect(self.delete_student)
        self.delete_button.setEnabled(False)
        button_layout.addWidget(self.delete_button)
        
        layout.addLayout(button_layout)

        self.student_listbox = QListWidget()
        self.student_listbox.itemClicked.connect(self.select_student)
        layout.addWidget(self.student_listbox)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_entry = QLineEdit()
        self.search_entry.textChanged.connect(self.search_students)
        search_layout.addWidget(self.search_entry)
        layout.addLayout(search_layout)

    def create_schedule_widget(self):
        layout = QVBoxLayout(self.schedule_widget)
        generate_button = QPushButton(QIcon("icons/generate.png"), "Generate Schedule")
        generate_button.setToolTip("Generate a new schedule")
        generate_button.clicked.connect(self.generate_schedule)
        layout.addWidget(generate_button)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        self.schedule_text = QTextEdit()
        self.schedule_text.setReadOnly(True)
        splitter.addWidget(self.schedule_text)

        calendar_widget = QCalendarWidget()
        calendar_widget.selectionChanged.connect(self.update_schedule_for_date)
        
        calendar_widget.setStyleSheet("""
            QCalendarWidget QAbstractItemView {
                font-size: 14px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                height: 40px;
            }
            QCalendarWidget QToolButton {
                font-size: 14px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                font-size: 14px;
            }
        """)
        
        splitter.addWidget(calendar_widget)

    def create_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_data)
        QShortcut(QKeySequence("Ctrl+O"), self, self.load_data)
        QShortcut(QKeySequence("Ctrl+A"), self, self.add_student)
        QShortcut(QKeySequence("Ctrl+M"), self, self.modify_student)
        QShortcut(QKeySequence("Ctrl+D"), self, self.delete_student)
        QShortcut(QKeySequence("Ctrl+G"), self, self.generate_schedule)
        QShortcut(QKeySequence("Ctrl+F"), self, self.search_entry.setFocus)

    def start_drag(self, button):
        self.is_dragging = True
        self.drag_start_state = button.isChecked()
        self.toggle_availability(button)

    def continue_drag(self, button, pos):
        if self.is_dragging:
            parent = button.parent()
            global_pos = button.mapToGlobal(pos)
            # Convert QPointF to QPoint
            global_point = QPoint(int(global_pos.x()), int(global_pos.y()))
            target_button = parent.childAt(parent.mapFromGlobal(global_point))
            if isinstance(target_button, AvailabilityButton) and target_button != self.last_dragged_button:
                target_button.setChecked(self.drag_start_state)
                self.toggle_availability(target_button)
                self.last_dragged_button = target_button

    def end_drag(self):
        self.is_dragging = False
        self.drag_start_state = None
        self.last_dragged_button = None

    def toggle_availability(self, button):
        day, time = button.day, button.time
        if button.is_teacher:  # Teacher availability
            if time in self.teacher_availability[day]:
                self.teacher_availability[day].remove(time)
            else:
                self.teacher_availability[day].add(time)
        else:  # Student availability
            if time in self.student_availability[day]:
                self.student_availability[day].remove(time)
            else:
                self.student_availability[day].add(time)
        
        button.setChecked(time in (self.teacher_availability[day] if button.is_teacher else self.student_availability[day]))

    def search_students(self):
        search_text = self.search_entry.text().lower()
        for i in range(self.student_listbox.count()):
            item = self.student_listbox.item(i)
            if search_text in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def update_schedule_for_date(self):
        selected_date = self.sender().selectedDate()
        day_of_week = selected_date.dayOfWeek()
        if 1 <= day_of_week <= 5:
            day_name = self.days[day_of_week - 1]
            self.display_schedule_for_day(day_name)
        else:
            self.schedule_text.setText("No classes scheduled for weekends.")

    def display_schedule_for_day(self, day):
        pass

    def add_student(self):
        name = self.name_entry.text()
        level = self.level_dropdown.currentText()
        twice_weekly = self.twice_weekly_checkbox.isChecked()
        if name and level:
            if self.is_duplicate_name(name):
                QMessageBox.warning(self, "Error", "A student with this name already exists. Please use a different name.")
                return
            student = Student(name, level, {day: set(times) for day, times in self.student_availability.items()}, twice_weekly)
            self.students.append(student)
            self.student_listbox.addItem(f"{name} - {level} {'(Twice Weekly)' if twice_weekly else ''}")
            self.clear_student_form()
            self.statusBar().showMessage(f"Student {name} added successfully", 2000)
        else:
            QMessageBox.warning(self, "Error", "Please enter both name and level")

    def select_student(self, item):
        index = self.student_listbox.row(item)
        self.selected_student = self.students[index]
        self.name_entry.setText(self.selected_student.name)
        self.level_dropdown.setCurrentText(self.selected_student.level)
        self.twice_weekly_checkbox.setChecked(self.selected_student.twice_weekly)
        self.student_availability = self.selected_student.availability.copy()
        self.update_availability_ui()
        self.modify_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.add_button.setText("Save as New")
        self.add_button.clicked.disconnect()
        self.add_button.clicked.connect(self.save_as_new_student)

    def save_as_new_student(self):
        name = self.name_entry.text()
        level = self.level_dropdown.currentText()
        twice_weekly = self.twice_weekly_checkbox.isChecked()
        if name and level:
            if self.is_duplicate_name_strict(name):
                QMessageBox.warning(self, "Error", "A student with this name already exists. Please use a different name.")
                return
            student = Student(name, level, self.student_availability.copy(), twice_weekly)
            self.students.append(student)
            self.student_listbox.addItem(f"{name} - {level} {'(Twice Weekly)' if twice_weekly else ''}")
            self.clear_student_form()
            self.statusBar().showMessage(f"New student {name} saved successfully", 2000)
        else:
            QMessageBox.warning(self, "Error", "Please enter both name and level")

    def clear_student_form(self):
        self.name_entry.clear()
        self.level_dropdown.setCurrentIndex(0)
        self.twice_weekly_checkbox.setChecked(False)
        self.reset_student_availability()
        self.selected_student = None
        self.modify_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.add_button.setText("Add Student")
        self.add_button.clicked.disconnect()
        self.add_button.clicked.connect(self.add_student)

    def update_availability_ui(self):
        availability_layout = self.student_widget.layout().itemAt(1).widget().widget().layout()
        for col, day in enumerate(self.days, start=1):
            for row, time in enumerate(self.get_time_slots(), start=1):
                btn = availability_layout.itemAtPosition(row, col).widget()
                if btn:
                    btn.setChecked(time in self.student_availability[day])

    def reset_student_availability(self):
        self.student_availability = {day: set() for day in self.days}
        self.update_availability_ui()

    @staticmethod
    def get_time_slots():
        return [time(hour=h, minute=m).strftime("%H:%M") for h in range(12, 22) for m in (0, 30)]

    def modify_student(self):
        if self.selected_student:
            new_name = self.name_entry.text()
            if new_name != self.selected_student.name and self.is_duplicate_name(new_name):
                QMessageBox.warning(self, "Error", "A student with this name already exists. Please use a different name.")
                return
            self.selected_student.name = new_name
            self.selected_student.level = self.level_dropdown.currentText()
            self.selected_student.twice_weekly = self.twice_weekly_checkbox.isChecked()
            self.selected_student.availability = self.student_availability.copy()
            self.update_student_listbox()
            self.clear_student_form()
            self.statusBar().showMessage(f"Student {new_name} information updated", 2000)

    def delete_student(self):
        if self.selected_student:
            student_name = self.selected_student.name  # Store the name before deletion
            self.students.remove(self.selected_student)
            self.update_student_listbox()
            self.clear_student_form()
            self.statusBar().showMessage(f"Student {student_name} deleted", 2000)
        else:
            self.statusBar().showMessage("No student selected for deletion", 2000)

    def update_student_listbox(self):
        self.student_listbox.clear()
        for student in self.students:
            self.student_listbox.addItem(f"{student.name} - {student.level} {'(Twice Weekly)' if student.twice_weekly else ''}")

    def generate_schedule(self):
        self.schedule_text.clear()
        schedule = self.create_optimal_schedule()
        self.display_schedule(schedule)

    def create_optimal_schedule(self):
        schedule = {day: [] for day in self.days}
        students_by_level = defaultdict(list)
        for student in self.students:
            students_by_level[student.level].append(student)
            student.scheduled_days = 0

        for day in self.days:
            available_times = sorted(self.teacher_availability[day])
            for start_time in available_times:
                end_time = self.add_hour_to_time(start_time)
                if end_time not in self.teacher_availability[day]:
                    continue

                for level, students in students_by_level.items():
                    available_students = self.get_available_students(students, day, start_time, end_time)
                
                    if 3 <= len(available_students) <= 7:
                        schedule[day].append({
                            'time': start_time,
                            'level': level,
                            'students': available_students
                        })
                        for student in available_students:
                            student.scheduled_days += 1
                        break  # Move to the next time slot
                    elif len(available_students) > 7:
                        class_students = available_students[:7]
                        schedule[day].append({
                            'time': start_time,
                            'level': level,
                            'students': class_students
                        })
                        for student in class_students:
                            student.scheduled_days += 1
                        break  # Move to the next time slot

        return schedule

    def get_available_students(self, students, day, start_time, end_time):
        return [s for s in students if 
                start_time in s.availability[day] and
                end_time in s.availability[day] and
                (not s.twice_weekly and s.scheduled_days == 0) or
                (s.twice_weekly and s.scheduled_days < 2)]

    def add_hour_to_time(self, time_str):
        t = datetime.strptime(time_str, "%H:%M")
        t += timedelta(hours=1)
        return t.strftime("%H:%M")

    def display_schedule(self, schedule):
        self.schedule_text.clear()
        self.schedule_text.append("Weekly Schedule:")
        self._display_scheduled_classes(schedule)
        self._display_unscheduled_students(schedule)

    def _display_scheduled_classes(self, schedule):
        for day, classes in schedule.items():
            self.schedule_text.append(f"\n{day}:")
            if not classes:
                self.schedule_text.append("  No classes scheduled")
            for class_info in classes:
                start_time = class_info['time']
                end_time = self.add_hour_to_time(start_time)
                self.schedule_text.append(f"  {start_time} - {end_time}: {class_info['level']} Class")
                self.schedule_text.append(f"    Students: {', '.join(s.name for s in class_info['students'])}")

    def _display_unscheduled_students(self, schedule):
        unscheduled_students = self.get_unscheduled_students(schedule)
        if unscheduled_students:
            self.schedule_text.append("\nUnscheduled Students:")
            for level, students in unscheduled_students.items():
                self.schedule_text.append(f"  {level}:")
                for student, reason in students:
                    self.schedule_text.append(f"    {student.name}: {reason}")

    def get_unscheduled_students(self, schedule):
        unscheduled = defaultdict(list)
        for student in self.students:
            if student.scheduled_days == 0:
                reason = self.get_unscheduled_reason(student, schedule)
                unscheduled[student.level].append((student, reason))
            elif student.twice_weekly and student.scheduled_days < 2:
                reason = self.get_partially_scheduled_reason(student, schedule)
                unscheduled[student.level].append((student, reason))
        return unscheduled

    def get_unscheduled_reason(self, student, schedule):
        if not any(student.availability.values()):
            return "No available time slots"
        for day, classes in schedule.items():
            for class_info in classes:
                if (student.level == class_info['level'] and
                    class_info['time'] in student.availability[day]):
                    return "Class was full"
        return "No matching class times"

    def get_partially_scheduled_reason(self, student, schedule):
        available_days = [day for day, times in student.availability.items() if times]
        if len(available_days) < 2:
            return "Insufficient availability for twice-weekly classes"
        scheduled_day = next(day for day, classes in schedule.items() 
                             if any(student in class_info['students'] for class_info in classes))
        remaining_days = [day for day in available_days if day != scheduled_day]
        for day in remaining_days:
            for class_info in schedule[day]:
                if (student.level == class_info['level'] and
                    class_info['time'] in student.availability[day]):
                    return "Second class was full"
        return "No matching time for second class"

    def save_data(self):
        try:
            generated_schedule = self.get_current_schedule()
            data = {
                'teacher_availability': {day: list(times) for day, times in self.teacher_availability.items()},
                'students': [{
                    'name': s.name, 
                    'level': s.level, 
                    'availability': {d: list(t) for d, t in s.availability.items()},
                    'twice_weekly': s.twice_weekly
                } for s in self.students],
                'generated_schedule': generated_schedule
            }
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Data", "", "JSON Files (*.json)")
            if file_path:
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
                self.statusBar().showMessage(f"Data saved to {file_path}", 2000)
        except Exception as e:
            self.statusBar().showMessage(f"Error saving data: {str(e)}", 5000)

    def get_current_schedule(self):
        schedule = {}
        schedule_text = self.schedule_text.toPlainText()
        current_day = None
        class_info = None
        for line in schedule_text.split('\n'):
            line = line.strip()
            if line in self.days:
                current_day = line
                schedule[current_day] = []
            elif current_day and ' - ' in line and ':' in line:
                time_range, class_details = line.split(': ', 1)
                start_time = time_range.split(' - ')[0]
                level = class_details.split(' Class')[0]
                class_info = {'time': start_time, 'level': level, 'students': []}
                schedule[current_day].append(class_info)
            elif line.startswith('Students:'):
                if class_info is not None:
                    students = [s.strip() for s in line.split(':', 1)[1].split(',')]
                    class_info['students'] = students
            elif line == "Weekly Schedule:":
                pass
            elif line == "Unscheduled Students:":
                break

        return schedule

    def load_data(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Data", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, 'r') as f:
                data = json.load(f)
            self.teacher_availability = {day: set(data['teacher_availability'].get(day, [])) for day in self.days}
            self.students = [Student(s['name'], s['level'], {d: set(t) for d, t in s['availability'].items()}, s['twice_weekly']) for s in data['students']]
            self.update_gui_from_data()
            if 'generated_schedule' in data:
                self.display_loaded_schedule(data['generated_schedule'])
            self.statusBar().showMessage(f"Data loaded from {file_path}", 2000)

    def display_loaded_schedule(self, schedule):
        self.schedule_text.clear()
        self.schedule_text.append("Weekly Schedule:")
        for day, classes in schedule.items():
            self.schedule_text.append(f"\n{day}:")
            if not classes:
                self.schedule_text.append("  No classes scheduled")
            for class_info in classes:
                start_time = class_info['time']
                end_time = self.add_hour_to_time(start_time)
                self.schedule_text.append(f"  {start_time} - {end_time}: {class_info['level']} Class")
                self.schedule_text.append(f"    Students: {', '.join(class_info['students'])}")

    def update_gui_from_data(self):
        teacher_layout = self.teacher_widget.layout()
        scroll_area = teacher_layout.itemAt(0).widget()
        scroll_widget = scroll_area.widget()
        grid_layout = scroll_widget.layout()

        for col, day in enumerate(self.days):
            for row, time_str in enumerate(self.get_time_slots()):
                btn = grid_layout.itemAtPosition(row + 1, col + 1).widget()
                if btn:
                    btn.setChecked(time_str in self.teacher_availability[day])

        self.student_listbox.clear()
        for student in self.students:
            self.student_listbox.addItem(f"{student.name} - {student.level} {'(Twice Weekly)' if student.twice_weekly else ''}")

        self.reset_student_availability()
        
        if self.selected_student:
            self.student_availability = self.selected_student.availability.copy()
            self.update_availability_ui()

    def is_duplicate_name(self, name):
        return any(student.name.lower() == name.lower() for student in self.students if student != self.selected_student)

    def is_duplicate_name_strict(self, name):
        return any(student.name.lower() == name.lower() for student in self.students)

def main():
    app = QApplication(sys.argv)
    window = AcademySchedulerGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()