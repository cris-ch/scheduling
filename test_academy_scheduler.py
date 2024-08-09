import unittest
from PyQt6.QtWidgets import QApplication, QPushButton
from PyQt6.QtCore import Qt
from scheduling import AcademySchedulerGUI, Student, AvailabilityButton

class TestAcademySchedulerGUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])
        cls.gui = AcademySchedulerGUI()

    def setUp(self):
        self.gui.students.clear()
        self.gui.student_listbox.clear()
        self.gui.reset_student_availability()

    def test_add_student(self):
        self.gui.name_entry.setText("John Doe")
        self.gui.level_dropdown.setCurrentText("Kids I")
        self.gui.twice_weekly_checkbox.setChecked(True)
        self.gui.add_student()

        self.assertEqual(len(self.gui.students), 1)
        self.assertEqual(self.gui.students[0].name, "John Doe")
        self.assertEqual(self.gui.students[0].level, "Kids I")
        self.assertTrue(self.gui.students[0].twice_weekly)

    def test_duplicate_student_name(self):
        self.gui.name_entry.setText("Jane Doe")
        self.gui.level_dropdown.setCurrentText("Teens II")
        self.gui.add_student()

        self.gui.name_entry.setText("Jane Doe")
        self.gui.level_dropdown.setCurrentText("Kids III")
        self.gui.add_student()

        self.assertEqual(len(self.gui.students), 1)
        self.assertEqual(self.gui.students[0].level, "Teens II")

    def test_modify_student(self):
        self.gui.students.append(Student("Alice", "Pre-Teens I", {}, False))
        self.gui.update_student_listbox()

        self.gui.student_listbox.setCurrentRow(0)
        self.gui.select_student(self.gui.student_listbox.item(0))

        self.gui.name_entry.setText("Alice Smith")
        self.gui.level_dropdown.setCurrentText("Pre-Teens II")
        self.gui.twice_weekly_checkbox.setChecked(True)
        self.gui.modify_student()

        self.assertEqual(self.gui.students[0].name, "Alice Smith")
        self.assertEqual(self.gui.students[0].level, "Pre-Teens II")
        self.assertTrue(self.gui.students[0].twice_weekly)

    def test_delete_student(self):
        self.gui.students.append(Student("Bob", "Teens III", {}, False))
        self.gui.update_student_listbox()

        self.gui.student_listbox.setCurrentRow(0)
        self.gui.select_student(self.gui.student_listbox.item(0))
        self.gui.delete_student()

        self.assertEqual(len(self.gui.students), 0)
        self.assertEqual(self.gui.student_listbox.count(), 0)

    def test_toggle_availability(self):
        day = "Monday"
        time = "14:00"
        button = AvailabilityButton(day, time, self.gui, is_teacher=True)
        
        initial_state = time in self.gui.teacher_availability[day]
        self.gui.toggle_availability(button)
        new_state = time in self.gui.teacher_availability[day]
        
        self.assertNotEqual(initial_state, new_state)

    def test_create_optimal_schedule(self):
        # Add some test data
        self.gui.teacher_availability = {day: set(["14:00", "15:00", "16:00"]) for day in self.gui.days}
        self.gui.students = [
            Student("Student1", "Kids I", {day: set(["14:00"]) for day in self.gui.days}, False),
            Student("Student2", "Kids I", {day: set(["14:00"]) for day in self.gui.days}, False),
            Student("Student3", "Kids I", {day: set(["14:00"]) for day in self.gui.days}, False),
            Student("Student4", "Teens II", {day: set(["15:00"]) for day in self.gui.days}, False),
            Student("Student5", "Teens II", {day: set(["15:00"]) for day in self.gui.days}, False),
            Student("Student6", "Teens II", {day: set(["15:00"]) for day in self.gui.days}, False),
        ]

        schedule = self.gui.create_optimal_schedule()

        self.assertTrue(all(day in schedule for day in self.gui.days))
        self.assertTrue(any(len(classes) > 0 for classes in schedule.values()))

    def test_get_unscheduled_students(self):
        self.gui.students = [
            Student("Scheduled1", "Kids I", {}, False),
            Student("Scheduled2", "Kids I", {}, False),
            Student("Unscheduled1", "Teens II", {}, False),
            Student("PartiallyScheduled", "Pre-Teens I", {}, True),
        ]
        self.gui.students[0].scheduled_days = 1
        self.gui.students[1].scheduled_days = 1
        self.gui.students[2].scheduled_days = 0
        self.gui.students[3].scheduled_days = 1

        schedule = {day: [] for day in self.gui.days}
        unscheduled = self.gui.get_unscheduled_students(schedule)

        self.assertIn("Teens II", unscheduled)
        self.assertIn("Pre-Teens I", unscheduled)
        self.assertEqual(len(unscheduled["Teens II"]), 1)
        self.assertEqual(len(unscheduled["Pre-Teens I"]), 1)
        self.assertIn("Unscheduled1", unscheduled["Teens II"][0])
        self.assertIn("PartiallyScheduled (1/2)", unscheduled["Pre-Teens I"][0])

if __name__ == '__main__':
    unittest.main()


    