from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
import sqlite3
import csv
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.datatables import MDDataTable
from kivy.metrics import dp


def create_tables():
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        aadhaar TEXT UNIQUE,
        qualification TEXT,
        course_name TEXT,
        phone_no TEXT,
        full_fees REAL,
        remaining_balance REAL,
        date_of_joining TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        amount_paid REAL,
        payment_date TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id))''')
    conn.commit()
    conn.close()


def add_student(data):
    try:
        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO students 
            (name, aadhaar, qualification, course_name, phone_no, full_fees, remaining_balance, date_of_joining) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                       (data["name"], data["aadhaar"], data["qualification"], data["course_name"], data["phone_no"],
                        float(data["fees"]), float(data["fees"]), data["date_of_joining"]))
        conn.commit()
        return "Student added successfully."
    except sqlite3.IntegrityError:
        return "Aadhaar already exists."
    except Exception as e:
        return str(e)
    finally:
        conn.close()


def add_payment(identifier, amount, date):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, remaining_balance FROM students WHERE aadhaar=? OR phone_no=?", (identifier, identifier))
    student = cursor.fetchone()
    if not student:
        return "Student not found."
    student_id, balance = student
    if amount > balance:
        return "Amount exceeds balance."
    new_balance = balance - amount
    cursor.execute("UPDATE students SET remaining_balance=? WHERE id=?", (new_balance, student_id))
    cursor.execute("INSERT INTO payments (student_id, amount_paid, payment_date) VALUES (?, ?, ?)",
                   (student_id, amount, date))
    conn.commit()
    conn.close()
    return "Payment recorded."


def export_data():
    try:
        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM students")
        students = cursor.fetchall()
        with open("/sdcard/students.csv", "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Aadhaar", "Qualification", "Course", "Phone", "Full Fees", "Balance", "Join Date"])
            writer.writerows(students)

        cursor.execute("""SELECT p.payment_id, s.name, s.aadhaar, p.amount_paid, p.payment_date 
                          FROM payments p JOIN students s ON p.student_id = s.id""")
        payments = cursor.fetchall()
        with open("/sdcard/payments.csv", "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Payment ID", "Name", "Aadhaar", "Amount", "Date"])
            writer.writerows(payments)

        conn.close()
        return "Export successful to /sdcard/."
    except Exception as e:
        return f"Export failed: {str(e)}"


class MainScreen(Screen):
    pass


class AddStudentScreen(Screen):
    def submit(self):
        data = {
            "name": self.ids.name.text,
            "aadhaar": self.ids.aadhaar.text,
            "qualification": self.ids.qualification.text,
            "course_name": self.ids.course.text,
            "phone_no": self.ids.phone.text,
            "fees": self.ids.fees.text,
            "date_of_joining": self.ids.date.text,
        }
        result = add_student(data)
        self.dialog("Add Student", result)

    def show_date_picker(self):
        date_dialog = MDDatePicker()
        date_dialog.bind(on_save=self.on_date_selected)
        date_dialog.open()

    def on_date_selected(self, instance, value, date_range):
        self.ids.date.text = str(value)

    def dialog(self, title, text):
        self.dialog_instance = MDDialog(
            title=title,
            text=text,
            buttons=[MDFlatButton(text="OK", on_release=self.dismiss_dialog)]
        )
        self.dialog_instance.open()

    def dismiss_dialog(self, instance):
        self.dialog_instance.dismiss()
        self.manager.current = 'main'


class ExportScreen(Screen):
    def export(self):
        msg = export_data()
        MDDialog(title="Export Result", text=msg,
                 buttons=[MDFlatButton(text="OK", on_release=lambda x: self.dismiss_dialog())]).open()

    def dismiss_dialog(self):
        self.manager.current = 'main'


KV = '''
ScreenManager:
    MainScreen:
    AddStudentScreen:
    ExportScreen:

<MainScreen>:
    name: 'main'
    BoxLayout:
        orientation: 'vertical'
        MDTopAppBar:
            title: "Student Manager"
        MDRaisedButton:
            text: "Add Student"
            on_release: app.root.current = 'add_student'
        MDRaisedButton:
            text: "Export to CSV"
            on_release: app.root.current = 'export'

<AddStudentScreen>:
    name: 'add_student'
    ScrollView:
        MDBoxLayout:
            orientation: 'vertical'
            padding: dp(20)
            spacing: dp(10)
            size_hint_y: None
            height: self.minimum_height

            MDTextField:
                id: name
                hint_text: "Name"
            MDTextField:
                id: aadhaar
                hint_text: "Aadhaar"
            MDTextField:
                id: qualification
                hint_text: "Qualification"
            MDTextField:
                id: course
                hint_text: "Course"
            MDTextField:
                id: phone
                hint_text: "Phone"
            MDTextField:
                id: fees
                hint_text: "Full Fees"
            MDTextField:
                id: date
                hint_text: "Joining Date"
                on_focus: if self.focus: root.show_date_picker()

            MDRaisedButton:
                text: "Submit"
                on_release: root.submit()

<ExportScreen>:
    name: 'export'
    BoxLayout:
        orientation: 'vertical'
        spacing: dp(10)
        padding: dp(20)
        MDLabel:
            text: "Export Students & Payments"
            halign: "center"
        MDRaisedButton:
            text: "Export Now"
            on_release: root.export()
'''


class StudentApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        create_tables()
        return Builder.load_string(KV)


if __name__ == "__main__":
    StudentApp().run()
