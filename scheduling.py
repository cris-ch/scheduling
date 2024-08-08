import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QComboBox, QListWidget, 
                             QTextEdit, QGridLayout, QScrollArea, QTabWidget, QMessageBox,
                             QFileDialog, QCheckBox, QStatusBar, QCalendarWidget, QSplitter)
from PyQt6.QtCore import Qt, QSize, QDate, QPoint, pyqtSignal, QObject, QEvent
from PyQt6.QtGui import QColor, QPalette, QShortcut, QKeySequence, QIcon, QMouseEvent, QCursor
from datetime import time, datetime, timedelta
import json
from collections import defaultdict

class AvailabilityButton(QPushButton):
    def __init__(self, day, time, main_window, parent=None):
        super().__init__(parent)
        self.day = day
        self.time = time
        self.main_window = main_window
        self.setCheckable(True)
        self.toggled.connect(self.update_style)
        self.press_pos = None
        self.is_drag = False

    def update_style(self):
        self.setStyleSheet("background-color: #90EE90;" if self.isChecked() else "")
        print(f"Button {self.day} {self.time} toggled: {self.isChecked()}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_pos = event.pos()
            self.is_drag = False
            print(f"Mouse press on button {self.day} {self.time}")
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            drag_distance = (event.pos() - self.press_pos).manhattanLength()
            print(f"Mouse move on button {self.day} {self.time}. Drag distance: {drag_distance}")
            if drag_distance >= QApplication.startDragDistance():
                self.is_drag = True
                print(f"Drag distance exceeded on button {self.day} {self.time}")
                self.main_window.start_drag(self)
            self.main_window.continue_drag(self, event.pos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            print(f"Mouse release on button {self.day} {self.time}")
            if not self.is_drag:
                print(f"Treating as click on button {self.day} {self.time}")
                self.setChecked(not self.isChecked())
                self.main_window.toggle_availability(self)
            else:
                print(f"Ending drag on button {self.day} {self.time}")
                self.main_window.end_drag()
        self.press_pos = None
        self.is_drag = False
        super().mouseReleaseEvent(event)

class AcademySchedulerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Academy Scheduler")
        self.setGeometry(100, 100, 1200, 800)

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
        print("AcademySchedulerGUI initialized")

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

        times = [time(hour=h, minute=m).strftime("%H:%M") for h in range(8, 22) for m in (0, 30)]

        for col, day in enumerate(self.days):
            scroll_layout.addWidget(QLabel(day), 0, col + 1)

        for row, t in enumerate(times):
            scroll_layout.addWidget(QLabel(t), row + 1, 0)
            for col, day in enumerate(self.days):
                btn = AvailabilityButton(day, t, self)
                btn.setFixedSize(QSize(30, 30))
                btn.setToolTip(f"Click to toggle availability for {day} at {t}")
                scroll_layout.addWidget(btn, row + 1, col + 1)

        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        scroll_area.setObjectName("TeacherScrollArea")
        print("Teacher availability widget created")

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
        self.student_availability = {day: set() for day in self.days}

        times = [time(hour=h, minute=m).strftime("%H:%M") for h in range(12, 22) for m in (0, 30)]

        for col, day in enumerate(self.days):
            availability_layout.addWidget(QLabel(day), 0, col + 1)

        for row, t in enumerate(times):
            availability_layout.addWidget(QLabel(t), row + 1, 0)
            for col, day in enumerate(self.days):
                btn = AvailabilityButton(day, t, self)
                btn.setFixedSize(QSize(30, 30))
                btn.setToolTip(f"Click to toggle availability for {day} at {t}")
                availability_layout.addWidget(btn, row + 1, col + 1)

        availability_scroll.setWidget(availability_widget)
        layout.addWidget(availability_scroll)
        availability_scroll.setObjectName("StudentScrollArea")
        print("Student info widget created")

        button_layout = QHBoxLayout()
        self.add_button = QPushButton(QIcon("icons/add.png"), "Add Student")
        self.add_button.clicked.connect(self.add_student)
        button_layout.addWidget(self.add_button)
        
        self.modify_button = QPushButton(QIcon("icons/modify.png"), "Modify Student")
        self.modify_button.clicked.connect(self.modify_student)
        self.modify_button.setEnabled(False)
        button_layout.addWidget(self.modify_button)
        
        self.delete_button = QPushButton(QIcon("icons/delete.png"), "Delete Student")
        self.delete_button.clicked.connect(self.delete_student)
        self.delete_button.setEnabled(False)
        button_layout.addWidget(self.delete_button)
        
        layout.addLayout(button_layout)

        self.student_listbox = QListWidget()
        self.student_listbox.itemClicked.connect(self.select_student)
        layout.addWidget(self.student_listbox)

        # Add search functionality
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_entry = QLineEdit()
        self.search_entry.textChanged.connect(self.search_students)
        search_layout.addWidget(self.search_entry)
        layout.addLayout(search_layout)

    def create_schedule_widget(self):
        layout = QVBoxLayout(self.schedule_widget)
        generate_button = QPushButton(QIcon("icons/generate.png"), "Generate Schedule")
        generate_button.clicked.connect(self.generate_schedule)
        layout.addWidget(generate_button)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        self.schedule_text = QTextEdit()
        self.schedule_text.setReadOnly(True)
        splitter.addWidget(self.schedule_text)

        calendar_widget = QCalendarWidget()
        calendar_widget.selectionChanged.connect(self.update_schedule_for_date)
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
        if not self.is_dragging:
            self.is_dragging = True
            self.drag_start_state = not button.isChecked()
            self.last_dragged_button = button
            print(f"Drag started on button {button.day} {button.time}. Start state: {self.drag_start_state}")
            button.setChecked(self.drag_start_state)
            self.toggle_availability(button)

    def continue_drag(self, button, pos):
        print(f"Continue drag called for button {button.day} {button.time}")
        if self.is_dragging:
            parent = button.parent()
            global_pos = button.mapToGlobal(pos)
            target_button = parent.childAt(parent.mapFromGlobal(global_pos))
            if isinstance(target_button, AvailabilityButton) and target_button != self.last_dragged_button:
                target_button.setChecked(self.drag_start_state)
                self.toggle_availability(target_button)
                self.last_dragged_button = target_button
                print(f"Dragged over button {target_button.day} {target_button.time}")
            else:
                print(f"Drag not continued. Target button: {target_button}")
        else:
            print(f"Drag not continued. is_dragging: {self.is_dragging}")

    def end_drag(self):
        print(f"Ending drag. Last dragged button: {self.last_dragged_button.day} {self.last_dragged_button.time if self.last_dragged_button else None}")
        self.is_dragging = False
        self.drag_start_state = None
        self.last_dragged_button = None
        print("Drag ended")

    def toggle_availability(self, button):
        day, time = button.day, button.time
        if isinstance(button.parent().parent().parent(), QScrollArea):  # Teacher availability
            if time in self.teacher_availability[day]:
                self.teacher_availability[day].remove(time)
            else:
                self.teacher_availability[day].add(time)
            print(f"Teacher availability for {day} at {time} toggled. Current state: {time in self.teacher_availability[day]}")
        else:  # Student availability
            if time in self.student_availability[day]:
                self.student_availability[day].remove(time)
            else:
                self.student_availability[day].add(time)
            print(f"Student availability for {day} at {time} toggled. Current state: {time in self.student_availability[day]}")

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
        if 1 <= day_of_week <= 5:  # Monday to Friday
            day_name = self.days[day_of_week - 1]
            self.display_schedule_for_day(day_name)
        else:
            self.schedule_text.setText("No classes scheduled for weekends.")

    def display_schedule_for_day(self, day):
        # This method should be implemented to display the schedule for a specific day
        # You'll need to modify your schedule generation to store the schedule by day
        pass

    def add_student(self):
        name = self.name_entry.text()
        level = self.level_dropdown.currentText()
        twice_weekly = self.twice_weekly_checkbox.isChecked()
        if name and level:
            if self.is_duplicate_name(name):
                QMessageBox.warning(self, "Error", "A student with this name already exists. Please use a different name.")
                return
            student = Student(name, level, self.student_availability.copy(), twice_weekly)
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
        self.update_availability_buttons()
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

    def update_availability_buttons(self):
        availability_layout = self.student_widget.layout().itemAt(1).widget().widget().layout()
        for col, day in enumerate(self.days):
            for row, time_str in enumerate(self.get_time_slots()):
                btn = availability_layout.itemAtPosition(row + 1, col + 1).widget()
                if btn:
                    btn.setChecked(time_str in self.student_availability[day])

    def reset_student_availability(self):
        self.student_availability = {day: set() for day in self.days}
        availability_layout = self.student_widget.layout().itemAt(1).widget().widget().layout()
        for col in range(1, len(self.days) + 1):
            for row in range(1, len(self.get_time_slots()) + 1):
                btn = availability_layout.itemAtPosition(row, col).widget()
                if btn:
                    btn.setChecked(False)

    def get_time_slots(self):
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
            self.students.remove(self.selected_student)
            self.update_student_listbox()
            self.clear_student_form()
            self.statusBar().showMessage(f"Student {self.selected_student.name} deleted", 2000)

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
            student.scheduled_days = 0  # Reset scheduled days

        for day in self.days:
            available_times = sorted(self.teacher_availability[day])
            for start_time in available_times:
                end_time = self.add_hour_to_time(start_time)
                if end_time not in self.teacher_availability[day]:
                    continue

                for level, students in students_by_level.items():
                    available_students = [s for s in students if start_time in s.availability[day] and 
                                          (not s.twice_weekly or s.scheduled_days < 2)]
                    if len(available_students) >= 3:
                        class_students = self.distribute_students(available_students)
                        for group in class_students:
                            schedule[day].append({
                                'time': start_time,
                                'level': level,
                                'students': group
                            })
                            for student in group:
                                student.scheduled_days += 1
                        break  # Move to next time slot after scheduling classes

        return schedule

    def distribute_students(self, available_students):
        if len(available_students) <= 7:
            return [available_students]
        
        num_classes = (len(available_students) + 6) // 7  # Round up division
        students_per_class = len(available_students) // num_classes
        remainder = len(available_students) % num_classes

        classes = []
        start = 0
        for i in range(num_classes):
            end = start + students_per_class + (1 if i < remainder else 0)
            classes.append(available_students[start:end])
            start = end

        return classes

    def add_hour_to_time(self, time_str):
        t = datetime.strptime(time_str, "%H:%M")
        t += timedelta(hours=1)
        return t.strftime("%H:%M")

    def display_schedule(self, schedule):
        self.schedule_text.append("Weekly Schedule:")
        for day, classes in schedule.items():
            self.schedule_text.append(f"\n{day}:")
            if not classes:
                self.schedule_text.append("  No classes scheduled")
            for class_info in classes:
                self.schedule_text.append(f"  {class_info['time']} - {self.add_hour_to_time(class_info['time'])}: {class_info['level']} Class")
                self.schedule_text.append(f"    Students: {', '.join(s.name for s in class_info['students'])}")

        unscheduled_students = self.get_unscheduled_students(schedule)
        if unscheduled_students:
            self.schedule_text.append("\nUnscheduled Students:")
            for level, students in unscheduled_students.items():
                self.schedule_text.append(f"  {level}: {', '.join(s.name for s in students)}")

    def get_unscheduled_students(self, schedule):
        unscheduled = defaultdict(list)
        for student in self.students:
            if student.scheduled_days == 0:
                unscheduled[student.level].append(student)
            elif student.twice_weekly and student.scheduled_days < 2:
                unscheduled[student.level].append(f"{student.name} (1/2)")
        return unscheduled

    def save_data(self):
        data = {
            'teacher_availability': {day: list(times) for day, times in self.teacher_availability.items()},
            'students': [{
                'name': s.name, 
                'level': s.level, 
                'availability': {d: list(t) for d, t in s.availability.items()},
                'twice_weekly': s.twice_weekly
            } for s in self.students]
        }
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Data", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(data, f)
            self.statusBar().showMessage(f"Data saved to {file_path}", 2000)

    def load_data(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Data", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, 'r') as f:
                data = json.load(f)
            self.teacher_availability = {day: set(times) for day, times in data['teacher_availability'].items()}
            self.students = [Student(s['name'], s['level'], {d: set(t) for d, t in s['availability'].items()}, s['twice_weekly']) for s in data['students']]
            self.update_gui_from_data()
            self.statusBar().showMessage(f"Data loaded from {file_path}", 2000)

    def update_gui_from_data(self):
        # Update teacher availability buttons
        teacher_layout = self.teacher_widget.layout()
        scroll_area = teacher_layout.itemAt(0).widget()
        scroll_widget = scroll_area.widget()
        grid_layout = scroll_widget.layout()

        for col, day in enumerate(self.days):
            for row, time_str in enumerate(self.get_time_slots()):
                btn = grid_layout.itemAtPosition(row + 1, col + 1).widget()
                if btn:
                    btn.setChecked(time_str in self.teacher_availability[day])

        # Update student listbox
        self.student_listbox.clear()
        for student in self.students:
            self.student_listbox.addItem(f"{student.name} - {student.level} {'(Twice Weekly)' if student.twice_weekly else ''}")

        # Reset student availability buttons
        self.reset_student_availability()
        
        # If a student was previously selected, update the availability buttons
        if self.selected_student:
            self.student_availability = self.selected_student.availability.copy()
            self.update_availability_buttons()

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