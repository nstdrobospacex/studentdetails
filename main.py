from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
import sqlite3
from kivymd.uix.datatables import MDDataTable
from kivy.metrics import dp
import csv
import os
from kivymd.uix.pickers import MDDatePicker



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
        return "Error: Aadhaar already exists."
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        conn.close()


def add_payment(aadhaar_or_phone, amount, date):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, remaining_balance FROM students WHERE aadhaar=? OR phone_no=?",
                   (aadhaar_or_phone, aadhaar_or_phone))
    student = cursor.fetchone()
    if not student:
        return "Student not found."
    student_id, balance = student
    if amount > balance:
        return "Payment exceeds balance."
    new_balance = balance - amount
    cursor.execute("UPDATE students SET remaining_balance=? WHERE id=?", (new_balance, student_id))
    cursor.execute("INSERT INTO payments (student_id, amount_paid, payment_date) VALUES (?, ?, ?)",
                   (student_id, amount, date))
    conn.commit()
    conn.close()
    return "Payment recorded."


def get_all_students():
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_all_payments():
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.payment_id, p.student_id, s.name, s.aadhaar, p.amount_paid, p.payment_date
        FROM payments p
        JOIN students s ON p.student_id = s.id
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def export_data():
    try:
        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()

        # Export students
        cursor.execute("SELECT * FROM students")
        students = cursor.fetchall()
        student_columns = [column[0] for column in cursor.description]
        with open("students.csv", "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(student_columns)
            writer.writerows(students)

        # Export payments
        cursor.execute("SELECT p.payment_id, p.student_id, s.name, s.aadhaar, p.amount_paid, p.payment_date FROM payments p JOIN students s ON p.student_id = s.id")
        payments = cursor.fetchall()
        payment_columns = ["payment_id", "student_id", "name", "aadhaar", "amount_paid", "payment_date"]
        with open("payments.csv", "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(payment_columns)
            writer.writerows(payments)

        conn.close()
        return "Exported to students.csv and payments.csv successfully!"
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

    def go_back(self):
        self.manager.current = 'main'


class AddPaymentScreen(Screen):
    def submit_payment(self):
        id_val = self.ids.aadhaar_phone.text
        try:
            amount = float(self.ids.amount.text)
        except ValueError:
            self.dialog("Invalid Input", "Amount must be a number.")
            return
        date = self.ids.date.text
        result = add_payment(id_val, amount, date)
        self.dialog("Add Payment", result)

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

    def go_back(self):
        self.manager.current = 'main'


class ViewStudentsScreen(Screen):
    def on_enter(self):
        self.ids.box.clear_widgets()
        students = get_all_students()
        if not students:
            self.ids.box.add_widget(MDLabel(text="No students found", halign="center"))
            return

        table = MDDataTable(
            size_hint=(1, 1),
            column_data=[
                ("ID", dp(30)),
                ("Name", dp(50)),
                ("Aadhaar", dp(80)),
                ("Qualification", dp(60)),
                ("Course", dp(60)),
                ("Phone", dp(80)),
                ("Fees", dp(50)),
                ("Remaining", dp(60)),
                ("Join Date", dp(80)),
            ],
            row_data=[
                (
                    str(s[0]), s[1], s[2], s[3], s[4], s[5],
                    f"{s[6]:.2f}", f"{s[7]:.2f}", s[8]
                )
                for s in students
            ],
            use_pagination=True
        )
        self.ids.box.add_widget(table)

    def go_back(self):
        self.manager.current = 'main'


class ViewPaymentsScreen(Screen):
    def on_enter(self):
        self.ids.table_container.clear_widgets()
        self.ids.summary_container.clear_widgets()

        payments = get_all_payments()
        if not payments:
            self.ids.table_container.add_widget(
                MDLabel(text="No payments found", halign="center")
            )
            return

        table = MDDataTable(
            size_hint=(1, 1),
            column_data=[
                ("PID", dp(30)),
                ("Student ID", dp(30)),
                ("Name", dp(50)),
                ("Aadhaar", dp(80)),
                ("Amount", dp(50)),
                ("Date", dp(80)),
            ],
            row_data=[
                (
                    str(p[0]), str(p[1]), p[2], p[3],
                    f"{p[4]:.2f}", p[5]
                )
                for p in payments
            ],
            use_pagination=True
        )
        self.ids.table_container.add_widget(table)

        
        totals = {}
        for p in payments:
            student_id = p[1]
            amount = p[4]
            totals[student_id] = totals.get(student_id, 0) + amount

        for sid, total in sorted(totals.items()):
            self.ids.summary_container.add_widget(
                MDLabel(
                    text=f"Total paid by Student ID {sid}: ₹{total:.2f}",
                    halign="left",
                    theme_text_color="Secondary"
                )
            )

    def go_back(self):
        self.manager.current = 'main'



class ExportScreen(Screen):
    def do_export(self):
        msg = export_data()
        MDDialog(
            title="Export Result",
            text=msg,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: self.close(x))]
        ).open()

    def close(self, obj):
        obj.parent.parent.dismiss()

    def go_back(self):
        self.manager.current = 'main'




KV = '''
ScreenManager:
    MainScreen:
    AddStudentScreen:
    AddPaymentScreen:
    ViewStudentsScreen:
    ViewPaymentsScreen:
    ExportScreen:

<MainScreen>:
    name: 'main'
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "Student Management"
            elevation: 10
            pos_hint: {"top": 1}
        Widget:
            size_hint_y: None
            height: dp(20)
        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: dp(20)
                spacing: dp(12)
                size_hint_y: None
                height: self.minimum_height

                MDRaisedButton:
                    text: "Add Student"
                    size_hint_x: 0.8
                    pos_hint: {"center_x": 0.5}
                    on_release: app.root.current = 'add_student'

                MDRaisedButton:
                    text: "Add Payment"
                    size_hint_x: 0.8
                    pos_hint: {"center_x": 0.5}
                    on_release: app.root.current = 'add_payment'

                MDRaisedButton:
                    text: "View Students"
                    size_hint_x: 0.8
                    pos_hint: {"center_x": 0.5}
                    on_release: app.root.current = 'view_students'

                MDRaisedButton:
                    text: "View Payments"
                    size_hint_x: 0.8
                    pos_hint: {"center_x": 0.5}
                    on_release: app.root.current = 'view_payments'

                MDRaisedButton:
                    text: "Export to Excel"
                    size_hint_x: 0.8
                    pos_hint: {"center_x": 0.5}
                    on_release: app.root.current = 'export'


<AddStudentScreen>:
    name: 'add_student'
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: "Add Student"
            elevation: 10
            left_action_items: [["arrow-left", lambda x: root.go_back()]]
        Widget:
            size_hint_y: None
            height: dp(20)
        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: dp(20)
                spacing: dp(15)
                size_hint_y: None
                height: self.minimum_height

                MDTextField:
                    id: name
                    hint_text: "Name"
                    size_hint_x: 0.9
                    pos_hint: {"center_x": 0.5}

                MDTextField:
                    id: aadhaar
                    hint_text: "Aadhaar"
                    size_hint_x: 0.9
                    pos_hint: {"center_x": 0.5}

                MDTextField:
                    id: qualification
                    hint_text: "Qualification"
                    size_hint_x: 0.9
                    pos_hint: {"center_x": 0.5}

                MDTextField:
                    id: course
                    hint_text: "Course Name"
                    size_hint_x: 0.9
                    pos_hint: {"center_x": 0.5}

                MDTextField:
                    id: phone
                    hint_text: "Phone No"
                    size_hint_x: 0.9
                    pos_hint: {"center_x": 0.5}

                MDTextField:
                    id: fees
                    hint_text: "Full Fees"
                    input_filter: 'float'
                    size_hint_x: 0.9
                    pos_hint: {"center_x": 0.5}

                MDTextField:
                    id: date
                    hint_text: "Date of Joining (YYYY-MM-DD)"
                    readonly: True
                    size_hint_x: 0.9
                    pos_hint: {"center_x": 0.5}
                    on_focus: if self.focus: root.show_date_picker()

                MDRaisedButton:
                    text: "Submit"
                    size_hint_x: 0.5
                    pos_hint: {"center_x": 0.5}
                    on_release: root.submit()


<AddPaymentScreen>:
    name: 'add_payment'
    MDScreen:
        MDTopAppBar:
            title: "Add Payment"
            pos_hint: {"top": 1}
            elevation: 10
            left_action_items: [["arrow-left", lambda x: root.go_back()]]

        MDBoxLayout:
            orientation: "vertical"
            padding: dp(20)
            spacing: dp(10)
            pos_hint: {"top": 0.9}
            size_hint_y: None
            height: self.minimum_height
            y: self.parent.height - self.height - dp(56)

            MDTextField:
                id: aadhaar_phone
                hint_text: "Aadhaar or Phone"
                input_type: "number"

            MDTextField:
                id: amount
                hint_text: "Amount Paid"
                input_filter: 'float'

            MDTextField:
                id: date
                hint_text: "Payment Date (YYYY-MM-DD)"
                readonly: True
                on_focus: if self.focus: root.show_date_picker()

            MDRaisedButton:
                text: "Submit"
                on_release: root.submit_payment()

<ViewStudentsScreen>:
    name: 'view_students'
    MDBoxLayout:
        orientation: 'vertical'
        MDTopAppBar:
            title: "All Students"
            left_action_items: [["arrow-left", lambda x: root.go_back()]]
        BoxLayout:
            id: box

<ViewPaymentsScreen>:
    name: 'view_payments'
    MDBoxLayout:
        orientation: 'vertical'
        MDTopAppBar:
            title: "All Payments"
            left_action_items: [["arrow-left", lambda x: root.go_back()]]
        BoxLayout:
            orientation: 'vertical'
            id: box
            BoxLayout:
                id: table_container
                size_hint_y: 0.8
            ScrollView:
                size_hint_y: 0.2
                MDBoxLayout:
                    id: summary_container
                    orientation: 'vertical'
                    padding: dp(10)
                    spacing: dp(5)

<ExportScreen>:
    name: 'export'
    MDScreen:
        MDTopAppBar:
            title: "Export to Excel"
            pos_hint: {"top": 1}
            elevation: 10
            left_action_items: [["arrow-left", lambda x: root.go_back()]]
        MDBoxLayout:
            orientation: "vertical"
            padding: dp(20)
            spacing: dp(20)
            size_hint_y: None
            height: self.minimum_height
            pos_hint: {"top": 0.9}
            y: self.parent.height - self.height - dp(56)

            MDRaisedButton:
                text: "Export Students & Payments"
                pos_hint: {"center_x": 0.5}
                on_release: root.do_export()
'''



class StudentApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Indigo"
        create_tables()
        return Builder.load_string(KV)


if __name__ == '__main__':
    StudentApp().run()
