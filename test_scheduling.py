import os

os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.*=false'

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QMessageBox  # Add this import statement

import unittest
import warnings
import logging
from unittest.mock import mock_open
import json

# Suppress QBasicTimer warnings
logging.getLogger("PyQt6").setLevel(logging.ERROR)

# Suppress layout warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

from unittest.mock import MagicMock, patch
from unittest.mock import mock_open

from PyQt6.QtWidgets import QApplication, QWidget, QTabWidget, QPushButton, QListWidget, QLineEdit, QComboBox, QCheckBox, QTextEdit, QCalendarWidget, QScrollArea, QVBoxLayout, QGridLayout, QLabel, QSplitter
from PyQt6.QtCore import Qt, QPoint, QSize, QEvent, QPointF
from PyQt6.QtGui import QMouseEvent, QShortcut
from PyQt6.QtTest import QTest
from scheduling import Student, AvailabilityButton, AcademySchedulerGUI


class TestStudent(unittest.TestCase):

    def test_student_initialization(self):
        availability = {
            'Monday': set(['09:00', '10:00']),
            'Tuesday': set(['14:00', '15:00'])
        }
        student = Student("John Doe", "Kids I", availability, False)

        self.assertEqual(student.name, "John Doe")
        self.assertEqual(student.level, "Kids I")
        self.assertEqual(student.availability, availability)
        self.assertFalse(student.twice_weekly)
        self.assertEqual(student.scheduled_days, 0)

    def test_student_twice_weekly(self):
        availability = {
            'Monday': set(['09:00', '10:00']),
            'Tuesday': set(['14:00', '15:00'])
        }
        student = Student("Jane Doe", "Teens II", availability, True)

        self.assertTrue(student.twice_weekly)

    def test_student_availability_modification(self):
        availability = {
            'Monday': set(['09:00', '10:00']),
            'Tuesday': set(['14:00', '15:00'])
        }
        student = Student("Alice", "Pre-Teens I", availability, False)

        # Add new availability
        student.availability['Monday'].add('11:00')
        self.assertIn('11:00', student.availability['Monday'])

        # Remove availability
        student.availability['Tuesday'].remove('14:00')
        self.assertNotIn('14:00', student.availability['Tuesday'])


class MockMainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.drag_started = False
        self.drag_continued = False
        self.drag_ended = False

    def start_drag(self, button):
        self.drag_started = True

    def continue_drag(self, button, pos):
        self.drag_continued = True

    def end_drag(self):
        self.drag_ended = True


class TestAvailabilityButton(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])

    def setUp(self):
        self.parent = MockMainWindow()
        self.button = AvailabilityButton("Monday", "09:00", self.parent)

    def test_button_initialization(self):
        self.assertEqual(self.button.day, "Monday")
        self.assertEqual(self.button.time, "09:00")
        self.assertTrue(self.button.is_teacher)
        self.assertEqual(self.button.parent_window, self.parent)
        self.assertTrue(self.button.isCheckable())

    def test_mouse_press_event(self):
        QTest.mousePress(self.button, Qt.MouseButton.LeftButton)
        self.assertTrue(self.parent.drag_started)

    def test_mouse_move_event(self):
        QTest.mousePress(self.button, Qt.MouseButton.LeftButton)
        QTest.mouseMove(self.button, QPoint(10, 10))
        self.assertTrue(self.parent.drag_continued)

    def test_mouse_release_event(self):
        QTest.mousePress(self.button, Qt.MouseButton.LeftButton)
        QTest.mouseRelease(self.button, Qt.MouseButton.LeftButton)
        self.assertTrue(self.parent.drag_ended)

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()


class TestAcademySchedulerGUI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])

    def setUp(self):
        self.gui = AcademySchedulerGUI()

    def add_test_data(self):
        # Add some students
        students_data = [
            ("John Doe", "Kids I", False),
            ("Jane Doe", "Kids II", True),
            ("Alice Smith", "Teens I", False)
        ]
        for name, level, twice_weekly in students_data:
            self.gui.name_entry.setText(name)
            self.gui.level_dropdown.setCurrentText(level)
            self.gui.twice_weekly_checkbox.setChecked(twice_weekly)
            with patch.object(self.gui, 'is_duplicate_name', return_value=False):
                self.gui.add_student()
        
        # Set some teacher availability
        for day in self.gui.days:
            for time in ["09:00", "10:00", "11:00"]:
                self.gui.teacher_availability[day].add(time)

    def test_add_student(self):
        self.gui.name_entry.setText("John Doe")
        self.gui.level_dropdown.setCurrentText("Kids I")
        self.gui.twice_weekly_checkbox.setChecked(False)

        with patch.object(self.gui, 'is_duplicate_name', return_value=False):
            self.gui.add_student()

        self.assertEqual(len(self.gui.students), 1)
        self.assertEqual(self.gui.students[0].name, "John Doe")
        self.assertEqual(self.gui.students[0].level, "Kids I")
        self.assertFalse(self.gui.students[0].twice_weekly)

    def test_modify_student(self):
        # First, add a student
        self.test_add_student()

        # Select the student
        self.gui.student_listbox.setCurrentRow(0)
        self.gui.select_student(self.gui.student_listbox.item(0))

        # Now, modify the student
        self.gui.name_entry.setText("Jane Doe")
        self.gui.level_dropdown.setCurrentText("Kids II")
        self.gui.twice_weekly_checkbox.setChecked(True)

        with patch.object(self.gui, 'is_duplicate_name', return_value=False):
            self.gui.modify_student()

        self.assertEqual(self.gui.students[0].name, "Jane Doe")
        self.assertEqual(self.gui.students[0].level, "Kids II")
        self.assertTrue(self.gui.students[0].twice_weekly)

    def test_delete_student(self):
        # First, add a student
        self.test_add_student()

        # Select the student
        self.gui.student_listbox.setCurrentRow(0)
        self.gui.select_student(self.gui.student_listbox.item(0))

        # Store the name before deletion
        student_name = self.gui.selected_student.name

        # Now delete the student
        self.gui.delete_student()

        self.assertEqual(len(self.gui.students), 0)
        self.assertIsNone(self.gui.selected_student)

        # Check if the status bar message is correct
        self.assertEqual(self.gui.statusBar().currentMessage(), f"Student {student_name} deleted")

    def test_generate_schedule(self):
        # Add some students and generate a schedule
        self.add_test_data()
        self.gui.generate_schedule()
        
        # Check if schedule is not empty
        self.assertNotEqual(self.gui.schedule_text.toPlainText(), "")

    def test_save_and_load_data(self):
        # Add some students and set teacher availability
        self.add_test_data()
        
        # Save data
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', return_value=('test_save.json', '')):
            self.gui.save_data()
        
        # Clear existing data
        self.gui.students.clear()
        self.gui.teacher_availability = {day: set() for day in self.gui.days}
        
        # Load data
        mock_data = {
            'students': [{'name': 'Test Student', 'level': 'Kids I', 'availability': {day: [] for day in self.gui.days}, 'twice_weekly': False}],
            'teacher_availability': {day: ['09:00'] for day in self.gui.days},
            'generated_schedule': {}
        }
        with patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName', return_value=('test_save.json', '')):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_data))):
                self.gui.load_data()
        
        # Check if data is loaded correctly
        self.assertGreater(len(self.gui.students), 0)
        self.assertGreater(sum(len(times) for times in self.gui.teacher_availability.values()), 0)

    def test_toggle_availability(self):
        # Test teacher availability toggle
        teacher_button = AvailabilityButton("Monday", "09:00", self.gui, is_teacher=True)
        self.gui.toggle_availability(teacher_button)
        self.assertIn("09:00", self.gui.teacher_availability["Monday"])
        self.gui.toggle_availability(teacher_button)
        self.assertNotIn("09:00", self.gui.teacher_availability["Monday"])

        # Test student availability toggle
        student_button = AvailabilityButton("Monday", "14:00", self.gui, is_teacher=False)
        self.gui.toggle_availability(student_button)
        self.assertIn("14:00", self.gui.student_availability["Monday"])
        self.gui.toggle_availability(student_button)
        self.assertNotIn("14:00", self.gui.student_availability["Monday"])

    def test_search_students(self):
        # Add some students
        self.add_test_data()
        
        # Search for existing student
        self.gui.search_entry.setText("John")
        self.gui.search_students()
        self.assertFalse(self.gui.student_listbox.item(0).isHidden())
        self.assertTrue(self.gui.student_listbox.item(1).isHidden())
        
        # Search for non-existing student
        self.gui.search_entry.setText("Bob")
        self.gui.search_students()
        for i in range(self.gui.student_listbox.count()):
            self.assertTrue(self.gui.student_listbox.item(i).isHidden())

    def test_update_schedule_for_date(self):
        # Add some students and generate a schedule
        self.add_test_data()
        self.gui.generate_schedule()
        
        # Create a mock calendar widget
        mock_calendar = MagicMock()
        mock_calendar.selectedDate.return_value = QDate.currentDate()
        
        # Test weekday
        monday = QDate.currentDate().addDays(-QDate.currentDate().dayOfWeek() + 1)
        mock_calendar.selectedDate.return_value = monday
        with patch.object(self.gui, 'sender', return_value=mock_calendar):
            self.gui.update_schedule_for_date()
        self.assertNotEqual(self.gui.schedule_text.toPlainText(), "No classes scheduled for weekends.")
        
        # Test weekend
        saturday = monday.addDays(5)
        mock_calendar.selectedDate.return_value = saturday
        with patch.object(self.gui, 'sender', return_value=mock_calendar):
            self.gui.update_schedule_for_date()
        self.assertEqual(self.gui.schedule_text.toPlainText(), "No classes scheduled for weekends.")

    def test_create_optimal_schedule(self):
        self.add_test_data()
        schedule = self.gui.create_optimal_schedule()
        
        # Check if schedule is created for all days
        self.assertEqual(set(schedule.keys()), set(self.gui.days))
        
        # Check if classes are scheduled within teacher availability
        for day, classes in schedule.items():
            for class_info in classes:
                self.assertIn(class_info['time'], self.gui.teacher_availability[day])

        # Check if students are scheduled according to their availability and level
        for day, classes in schedule.items():
            for class_info in classes:
                self.assertGreaterEqual(len(class_info['students']), 3)  # At least 3 students per class
                self.assertLessEqual(len(class_info['students']), 7)  # At most 7 students per class
                for student in class_info['students']:
                    self.assertEqual(student.level, class_info['level'])
                    self.assertIn(class_info['time'], student.availability[day])

        # Check if twice weekly students are scheduled correctly
        for student in self.gui.students:
            if student.twice_weekly:
                self.assertLessEqual(student.scheduled_days, 2)
            else:
                self.assertLessEqual(student.scheduled_days, 1)

    def test_get_unscheduled_students(self):
        self.add_test_data()
        schedule = self.gui.create_optimal_schedule()
        unscheduled = self.gui.get_unscheduled_students(schedule)
        
        # Check if unscheduled students are correctly identified
        scheduled_students = set()
        for day, classes in schedule.items():
            for class_info in classes:
                scheduled_students.update(class_info['students'])
        
        for level, students in unscheduled.items():
            for student, reason in students:
                self.assertNotIn(student, scheduled_students)

    def test_save_and_load_data_integration(self):
        # Add some students and set teacher availability
        self.add_test_data()
        original_students = self.gui.students.copy()
        original_teacher_availability = self.gui.teacher_availability.copy()
        
        # Save data to a temporary file
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', return_value=('temp_save.json', '')):
            self.gui.save_data()
        
        # Clear existing data
        self.gui.students.clear()
        self.gui.teacher_availability = {day: set() for day in self.gui.days}
        
        # Load data from the temporary file
        with patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName', return_value=('temp_save.json', '')):
            self.gui.load_data()
        
        # Check if loaded data matches original data
        self.assertEqual(len(self.gui.students), len(original_students))
        for original, loaded in zip(original_students, self.gui.students):
            self.assertEqual(original.name, loaded.name)
            self.assertEqual(original.level, loaded.level)
            self.assertEqual(original.availability, loaded.availability)
            self.assertEqual(original.twice_weekly, loaded.twice_weekly)
        
        self.assertEqual(self.gui.teacher_availability, original_teacher_availability)
        
        # Clean up temporary file
        import os
        os.remove('temp_save.json')

    def test_error_handling(self):
        # Test adding a student with duplicate name
        self.gui.name_entry.setText("John Doe")
        self.gui.level_dropdown.setCurrentText("Kids I")
        with patch.object(self.gui, 'is_duplicate_name', return_value=True):
            with patch.object(QMessageBox, 'warning') as mock_warning:
                self.gui.add_student()
                mock_warning.assert_called_once()

        # Test modifying a student with duplicate name
        self.test_add_student()  # Add a student first
        self.gui.student_listbox.setCurrentRow(0)
        self.gui.select_student(self.gui.student_listbox.item(0))
        self.gui.name_entry.setText("Jane Doe")
        with patch.object(self.gui, 'is_duplicate_name', return_value=True):
            with patch.object(QMessageBox, 'warning') as mock_warning:
                self.gui.modify_student()
                mock_warning.assert_called_once()

        # Test saving data with file write error
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', return_value=('test_save.json', '')):
            with patch('builtins.open', side_effect=IOError("Test error")):
                with patch.object(self.gui.statusBar(), 'showMessage') as mock_status:
                    self.gui.save_data()
                    mock_status.assert_called_with("Error saving data: Test error", 5000)

    def test_get_available_students(self):
        # Create some test students
        students = [
            Student("John", "Kids I", {"Monday": {"09:00", "10:00"}}, False),
            Student("Jane", "Kids I", {"Monday": {"09:00", "10:00"}}, True),
            Student("Alice", "Kids I", {"Monday": {"11:00"}}, False),
            Student("Bob", "Kids I", {"Monday": {"09:00", "10:00"}}, False)
        ]
        
        # Set scheduled days for some students
        students[1].scheduled_days = 1  # Jane is scheduled once (twice weekly)
        students[3].scheduled_days = 1  # Bob is scheduled (not twice weekly)

        # Test the method
        available_students = self.gui.get_available_students(students, "Monday", "09:00", "10:00")
        
        # Check results
        self.assertEqual(len(available_students), 2)
        self.assertIn(students[0], available_students)  # John should be available
        self.assertIn(students[1], available_students)  # Jane should be available (twice weekly, only scheduled once)
        self.assertNotIn(students[2], available_students)  # Alice should not be available (wrong time)
        self.assertNotIn(students[3], available_students)  # Bob should not be available (already scheduled)

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()


if __name__ == '__main__':
    unittest.main()