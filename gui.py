import csv
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta, date
from tkcalendar import Calendar
from models import Room, Exam
from engine import TimetableEngine
from pdf_export import export_to_pdf
import tkinter.simpledialog
from database import TimetableDatabase
from types import SimpleNamespace

import csv
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta, date
from tkcalendar import Calendar
from models import Room, Exam
from engine import TimetableEngine
from pdf_export import export_to_pdf
import tkinter.simpledialog
from database import TimetableDatabase
from types import SimpleNamespace

class TimetableApp:
    def __init__(self, root):
        """
        Initialises the timetable app with the main window and sets up all UI components.
        Configures file selection, settings inputs, treeview for results, and action buttons.
        """
        self.root = root
        self.root.title("Exam Timetable Generator")

        # Create frame for CSV file selection inputs
        file_frame = tk.LabelFrame(root, text="CSV Files", padx=10, pady=10)
        file_frame.pack(fill="x", padx=10, pady=5)
        # Initialise string variables for file paths
        self.rooms_var = tk.StringVar()
        self.exams_var = tk.StringVar()
        self.students_var = tk.StringVar()
        # Add labels, entries, and browse buttons for each CSV file type
        tk.Label(file_frame, text="Rooms CSV:").grid(row=0, column=0, sticky="e")
        tk.Entry(file_frame, textvariable=self.rooms_var, width=40).grid(row=0, column=1, padx=5)
        tk.Button(file_frame, text="Browse", command=lambda: self.browse_file(self.rooms_var)).grid(row=0, column=2)
        tk.Label(file_frame, text="Exams CSV:").grid(row=1, column=0, sticky="e")
        tk.Entry(file_frame, textvariable=self.exams_var, width=40).grid(row=1, column=1, padx=5)
        tk.Button(file_frame, text="Browse", command=lambda: self.browse_file(self.exams_var)).grid(row=1, column=2)
        tk.Label(file_frame, text="Students CSV:").grid(row=2, column=0, sticky="e")
        tk.Entry(file_frame, textvariable=self.students_var, width=40).grid(row=2, column=1, padx=5)
        tk.Button(file_frame, text="Browse", command=lambda: self.browse_file(self.students_var)).grid(row=2, column=2)

        # Create frame for basic scheduling settings
        settings_frame = tk.LabelFrame(root, text="Basic Settings", padx=10, pady=10)
        settings_frame.pack(fill="x", padx=10, pady=5)
        # Date and time configuration inputs
        tk.Label(settings_frame, text="Start Date (YYYY-MM-DD):").grid(row=0, column=0)
        self.start_date_var = tk.StringVar(value=str(date.today()))
        tk.Entry(settings_frame, textvariable=self.start_date_var, width=12).grid(row=0, column=1)
        tk.Label(settings_frame, text="End Date (YYYY-MM-DD):").grid(row=0, column=2)
        self.end_date_var = tk.StringVar(value=str(date.today() + timedelta(days=7)))
        tk.Entry(settings_frame, textvariable=self.end_date_var, width=12).grid(row=0, column=3)
        tk.Label(settings_frame, text="Start Time (HH:MM):").grid(row=1, column=0)
        self.start_time_var = tk.StringVar(value="09:00")
        tk.Entry(settings_frame, textvariable=self.start_time_var, width=6).grid(row=1, column=1)
        tk.Label(settings_frame, text="End Time (HH:MM):").grid(row=1, column=2)
        self.end_time_var = tk.StringVar(value="15:30")
        tk.Entry(settings_frame, textvariable=self.end_time_var, width=6).grid(row=1, column=3)
        # Capacity and timing constraints
        tk.Label(settings_frame, text="Max Exams/Day:").grid(row=2, column=0)
        self.max_exams_var = tk.IntVar(value=3)
        tk.Spinbox(settings_frame, from_=1, to=10, textvariable=self.max_exams_var, width=5).grid(row=2, column=1)
        tk.Label(settings_frame, text="Min Gap (minutes):").grid(row=2, column=2)
        self.min_gap_var = tk.IntVar(value=15)
        tk.Spinbox(settings_frame, from_=0, to=120, textvariable=self.min_gap_var, width=5).grid(row=2, column=3)
        self.exclude_weekends_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Exclude Weekends", variable=self.exclude_weekends_var).grid(row=2, column=4, columnspan=2)

        # Advanced Settings Frame
        advanced_frame = tk.LabelFrame(root, text="Advanced Settings", padx=10, pady=10)
        advanced_frame.pack(fill="x", padx=10, pady=5)

        # Spreading control
        spreading_frame = tk.Frame(advanced_frame)
        spreading_frame.pack(fill="x", pady=5)
        tk.Label(spreading_frame, text="Minimum days between related exams:").pack(side="left")
        self.spreading_var = tk.IntVar(value=1)
        spreading_spin = tk.Spinbox(spreading_frame, from_=1, to=5, textvariable=self.spreading_var, width=5)
        spreading_spin.pack(side="left", padx=5)

        # Even spreading checkbox
        self.spread_evenly_var = tk.BooleanVar(value=True)
        spread_check = tk.Checkbutton(advanced_frame, text="Try to spread exams evenly", 
                                    variable=self.spread_evenly_var)
        spread_check.pack(anchor="w")

        # Date exclusion and custom times buttons
        button_frame = tk.Frame(advanced_frame)
        button_frame.pack(fill="x", pady=5)
        
        tk.Button(button_frame, text="Exclude Dates", 
                 command=self.show_date_exclusion).pack(side="left", padx=5)
        tk.Button(button_frame, text="Custom Time Slots", 
                 command=self.show_time_slots).pack(side="left", padx=5)

        # Initialize variables for storing excluded dates and custom times
        # `self.excluded_dates` holds YYYY-MM-DD strings that the engine
        # should not schedule on. Stored as a set for fast membership
        # checks and easy add/remove operations from the UI.
        self.excluded_dates = set()

        # `self.custom_time_slots` maps date strings to a dict with
        # 'start' and 'end' times. These override the global start/end
        # times for specific dates when present.
        self.custom_time_slots = {}

        # Treeview
        self.tree = ttk.Treeview(root, columns=("Exam ID", "Subject", "Room", "Date", "Start", "End"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Generate Timetable", command=self.load_and_generate).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Export PDF", command=self.export_pdf).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Export Individual PDFs", command=self.export_individual_pdfs).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Search Student", command=self.search_student).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="View Clash Log", command=self.view_clash_log).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Saved Timetables", 
                 command=self.show_saved_timetables).pack(side=tk.LEFT, padx=5)

        self.placements = []
        self.student_names = {}
        self.engine = None
        # Persistent database object used for saving/loading timetables.
        # Exposed on the app instance so dialogs can call `get_saved_timetables`,
        # `save_timetable` and `load_timetable` directly.
        self.db = TimetableDatabase()

    def browse_file(self, var):
        """
        Opens a file dialog for selecting CSV files and updates the given StringVar
        with the selected file path. Used for rooms, exams, and students CSV selection.
        """
        file = filedialog.askopenfilename(filetypes=[("CSV Files","*.csv")])
        if file:
            var.set(file)

    def load_and_generate(self):
        """
        Loads data from the selected CSV files, configures the scheduling engine
        with user settings, generates the timetable, and updates the UI with results.
        Handles errors and displays appropriate messages to the user.
        """
        try:
            # Retrieve file paths from UI variables
            rooms_file = self.rooms_var.get()
            exams_file = self.exams_var.get()
            students_file = self.students_var.get()
            # Validate that all required files are selected
            if not rooms_file or not exams_file or not students_file:
                messagebox.showwarning("Warning", "Please select all CSV files")
                return

            # Load room data from CSV
            rooms = []
            with open(rooms_file, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rooms.append(Room(row["room_id"], int(row["capacity"])))

            # If no rooms were loaded, provide a useful clash_log entry
            if not rooms:
                self.engine = SimpleNamespace(clash_log=[f"ERROR: No rooms loaded from {rooms_file}"])
                messagebox.showerror("Error", f"No rooms found in {rooms_file}. Please check the CSV file.")
                return

            # Load students
            self.student_names = {}
            with open(students_file, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.student_names[row["student_id"]] = row["full_name"]

            # If no students were loaded, provide clash_log entry
            if not self.student_names:
                self.engine = SimpleNamespace(clash_log=[f"ERROR: No students loaded from {students_file}"])
                messagebox.showerror("Error", f"No students found in {students_file}. Please check the CSV file.")
                return

            # Load exams
            exams = []
            with open(exams_file, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    students = row["student_ids"].split(";")
                    exams.append(Exam(row["exam_id"], row["subject"], int(row["duration_minutes"]), students))

            # If no exams were loaded, provide clash_log entry
            if not exams:
                self.engine = SimpleNamespace(clash_log=[f"ERROR: No exams loaded from {exams_file}"])
                messagebox.showerror("Error", f"No exams found in {exams_file}. Please check the CSV file.")
                return

            # Settings
            start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d").date()
            end_date = datetime.strptime(self.end_date_var.get(), "%Y-%m-%d").date()
            start_time = datetime.strptime(self.start_time_var.get(), "%H:%M").time()
            end_time = datetime.strptime(self.end_time_var.get(), "%H:%M").time()
            max_exams = self.max_exams_var.get()
            min_gap = self.min_gap_var.get()
            exclude_weekends = self.exclude_weekends_var.get()

            self.engine = TimetableEngine(
                rooms, exams, self.student_names,
                start_date=start_date, 
                end_date=end_date,
                start_time=start_time, 
                end_time=end_time,
                max_exams_day=max_exams, 
                min_gap=min_gap,
                exclude_weekends=exclude_weekends,
                min_days_between_exams=self.spreading_var.get(),  # New parameter
                spread_evenly=self.spread_evenly_var.get(),      # New parameter
                excluded_dates=self.excluded_dates,              # New parameter
                custom_time_slots=self.custom_time_slots        # New parameter
            )
            success = self.engine.generate()
            self.placements = self.engine.placements
            self.update_treeview(self.placements)

            # Check if scheduling was successful
            if not success:
                # Extract the main reason from clash log
                error_details = "\n".join(self.engine.clash_log[:10])  # Show first 10 log entries
                messagebox.showerror("Scheduling Failed", 
                           f"Cannot create valid timetable with current constraints.\n\n"
                           f"Reason:\n{error_details}")
            elif self.engine.clash_log and "Successfully" in self.engine.clash_log[-1]:
                messagebox.showinfo("Success", "Timetable generated successfully!")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_treeview(self, placements):
        # Clear existing items
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        # Add new placements
        for p in placements:
            self.tree.insert("", tk.END, values=(
                p.exam_id,
                p.subject,
                p.room_id,
                p.date,
                p.start,
                p.end
            ))
        # The Treeview lists current placements. Use this method to refresh
        # the display after generation, loading, or filtering.

    def export_pdf(self):
        if not self.placements:
            messagebox.showwarning("Warning", "No timetable generated yet")
            return
        file = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files","*.pdf")])
        if file:
            export_to_pdf(self.placements, file, self.student_names)

    def export_individual_pdfs(self):
        if not self.placements:
            messagebox.showwarning("Warning", "No timetable generated yet")
            return
        folder = filedialog.askdirectory(title="Select folder to save student PDFs")
        if not folder:
            return
        
        try:
            if not self.student_names:
                messagebox.showwarning("Warning", "No students loaded. Please load the students CSV file first.")
                return
            
            created_count = 0
            failed_count = 0
            errors = []
            
            for sid, name in self.student_names.items():
                try:
                    filename = os.path.join(folder, f"{sid}_{name.replace(' ', '_')}.pdf")
                    export_to_pdf(self.placements, filename, self.student_names, filter_student=sid)
                    created_count += 1
                except Exception as e:
                    failed_count += 1
                    errors.append(f"  {sid}: {str(e)}")
            
            if created_count > 0:
                msg = f"Successfully created {created_count} PDF files in {folder}"
                if failed_count > 0:
                    msg += f"\n\n{failed_count} students failed:\n" + "\n".join(errors[:5])
                    if len(errors) > 5:
                        msg += f"\n... and {len(errors) - 5} more"
                messagebox.showinfo("Success", msg)
            else:
                messagebox.showerror("Error", f"Failed to create any PDFs.\n\nErrors:\n" + "\n".join(errors))
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error during PDF export: {str(e)}")

    def search_student(self):
        def show_student():
            sid = student_entry.get().strip()
            if not sid:
                return
            filtered = [p for p in self.placements if sid in p.student_ids]
            self.update_treeview(filtered)
            student_win.destroy()

        student_win = tk.Toplevel(self.root)
        student_win.title("Search Student")
        tk.Label(student_win, text="Enter Student ID:").pack(side=tk.LEFT, padx=5, pady=5)
        student_entry = tk.Entry(student_win)
        student_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(student_win, text="Show Timetable", command=show_student).pack(side=tk.LEFT, padx=5)

    def view_clash_log(self):
        if not self.engine or not self.engine.clash_log:
            messagebox.showinfo("Clash Log", "No clashes detected.")
            return

        log_win = tk.Toplevel(self.root)
        log_win.title("Clash/Error Log")
        text = tk.Text(log_win, width=100, height=30)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(log_win, command=text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.configure(yscrollcommand=scrollbar.set)
        for entry in self.engine.clash_log:
            text.insert(tk.END, entry + "\n")
        text.config(state=tk.DISABLED)

        def save_log():
            file = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files","*.txt")])
            if file:
                with open(file, "w") as f:
                    f.write("\n".join(self.engine.clash_log))
                messagebox.showinfo("Saved", f"Clash log saved to {file}")

        tk.Button(log_win, text="Export Log", command=save_log).pack(pady=5)

    def clear_all(self):
        self.rooms_var.set("")
        self.exams_var.set("")
        self.students_var.set("")
        self.start_date_var.set(str(date.today()))
        self.end_date_var.set(str(date.today() + timedelta(days=7)))
        self.start_time_var.set("09:00")
        self.end_time_var.set("15:30")
        self.max_exams_var.set(3)
        self.min_gap_var.set(15)
        self.exclude_weekends_var.set(True)
        self.spreading_var.set(1)
        self.spread_evenly_var.set(True)
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.placements = []
        self.student_names = {}
        self.engine = None

    def show_date_exclusion(self):
        """Show window for entering dates to exclude"""
        ex_window = tk.Toplevel(self.root)
        ex_window.title("Exclude Dates")
        ex_window.grab_set()

        frame = tk.Frame(ex_window)
        frame.pack(padx=10, pady=10)

        # Calendar widget for date selection
        tk.Label(frame, text="Select Date to Exclude:").pack(anchor="w", pady=(0,5))
        cal = Calendar(frame, selectmode='day', date_pattern='yyyy-mm-dd')
        cal.pack(pady=5)

        # Listbox for showing excluded dates
        tk.Label(frame, text="Excluded Dates:").pack(anchor="w", pady=(10,5))
        listbox = tk.Listbox(frame, width=30, height=10)
        listbox.pack(fill="both", expand=True)
        
        # Add current excluded dates to listbox
        for date_str in sorted(self.excluded_dates):
            listbox.insert(tk.END, date_str)

        def add_date():
            try:
                date_str = cal.get_date()
                if date_str not in self.excluded_dates:
                    self.excluded_dates.add(date_str)
                    # Clear and repopulate listbox to keep it sorted
                    listbox.delete(0, tk.END)
                    for d in sorted(self.excluded_dates):
                        listbox.insert(tk.END, d)
                    messagebox.showinfo("Success", f"Date {date_str} excluded")
                else:
                    messagebox.showinfo("Info", f"Date {date_str} is already excluded")
            except Exception as e:
                messagebox.showerror("Error", f"Error adding date: {str(e)}")

        # The date exclusion dialog keeps a local Listbox for UX while the
        # authoritative set is `self.excluded_dates`. The engine will read
        # this set directly when `load_and_generate()` is called.

        def remove_selected():
            selection = listbox.curselection()
            if selection:
                date_str = listbox.get(selection[0])
                self.excluded_dates.remove(date_str)
                listbox.delete(selection[0])

        # Buttons
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="Add Selected Date", command=add_date).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Remove Selected", command=remove_selected).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Close", command=ex_window.destroy).pack(side="right", padx=5)

    def show_time_slots(self):
        """Show window for managing custom time slots"""
        ts_window = tk.Toplevel(self.root)
        ts_window.title("Custom Time Slots")
        ts_window.grab_set()

        main_frame = tk.Frame(ts_window)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Entry frame
        entry_frame = tk.LabelFrame(main_frame, text="Add Time Slot")
        entry_frame.pack(fill="x", pady=5)

        # Date entry
        date_frame = tk.Frame(entry_frame)
        date_frame.pack(fill="x", pady=5)
        tk.Label(date_frame, text="Date (YYYY-MM-DD):").pack(side="left", padx=5)
        date_var = tk.StringVar()
        tk.Entry(date_frame, textvariable=date_var, width=12).pack(side="left", padx=5)

        # Time entries
        time_frame = tk.Frame(entry_frame)
        time_frame.pack(fill="x", pady=5)
        tk.Label(time_frame, text="Start Time (HH:MM):").pack(side="left", padx=5)
        start_var = tk.StringVar()
        tk.Entry(time_frame, textvariable=start_var, width=8).pack(side="left", padx=5)
        tk.Label(time_frame, text="End Time (HH:MM):").pack(side="left", padx=5)
        end_var = tk.StringVar()
        tk.Entry(time_frame, textvariable=end_var, width=8).pack(side="left", padx=5)

        # List of time slots
        tk.Label(main_frame, text="Custom Time Slots:").pack(anchor="w")
        tree = ttk.Treeview(main_frame, columns=("Date", "Start", "End"), show="headings")
        for col in ("Date", "Start", "End"):
            tree.heading(col, text=col)
            tree.column(col, width=100)
        tree.pack(fill="both", expand=True, pady=5)

        def add_slot():
            try:
                date_str = date_var.get().strip()
                start_str = start_var.get().strip()
                end_str = end_var.get().strip()

                if not all([date_str, start_str, end_str]):
                    raise ValueError("Please fill all fields")

                # Validate formats
                datetime.strptime(date_str, "%Y-%m-%d")
                datetime.strptime(start_str, "%H:%M")
                datetime.strptime(end_str, "%H:%M")

                # Check for overlapping time slots (same date)
                if date_str in self.custom_time_slots:
                    messagebox.showerror("Error", 
                        f"A custom time slot already exists for {date_str}.\n"
                        f"Please remove the existing slot first or choose a different date.")
                    return

                tree.insert("", "end", values=(date_str, start_var.get(), end_var.get()))
                self.custom_time_slots[date_str] = {"start": start_var.get(), "end": end_var.get()}

                # Clear entries
                date_var.set("")
                start_var.set("")
                end_var.set("")
                
                messagebox.showinfo("Success", f"Custom time slot added for {date_str}")

            except ValueError as e:
                messagebox.showerror("Error", "Invalid format. Use YYYY-MM-DD for date and HH:MM for time")

        # Custom time slots allow per-date overrides of the global start/
        # end times. They are stored in `self.custom_time_slots` and
        # consumed by the scheduling engine when present.

        def remove_selected():
            selected = tree.selection()
            if selected:
                item = selected[0]
                date_str = tree.item(item)['values'][0]
                if date_str in self.custom_time_slots:
                    del self.custom_time_slots[date_str]
                tree.delete(item)

        # Buttons
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="Add", command=add_slot).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Remove Selected", command=remove_selected).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Close", command=ts_window.destroy).pack(side="right", padx=5)

        # Load existing time slots
        for date_str, times in self.custom_time_slots.items():
            tree.insert("", "end", values=(date_str, times["start"], times["end"]))

    def show_saved_timetables(self):
        saved_window = tk.Toplevel(self.root)
        saved_window.title("Saved Timetables")
        saved_window.geometry("600x400")

        # Treeview for saved timetables
        tree = ttk.Treeview(saved_window, 
                           columns=("ID", "Name", "Created", "Description"),
                           show="headings")
        
        for col in tree["columns"]:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Load saved timetables
        saved = self.db.get_saved_timetables()
        for timetable in saved:
            tree.insert("", tk.END, values=timetable)

        def load_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a timetable to load")
                return
            
            timetable_id = tree.item(selected[0])['values'][0]
            loaded_placements = self.db.load_timetable(timetable_id)
            
            # Store the loaded placements
            self.placements = loaded_placements
            
            # Update the main treeview
            self.update_treeview(self.placements)
            
            # Show confirmation
            messagebox.showinfo("Success", "Timetable loaded successfully")
            saved_window.destroy()

        def save_current():
            if not self.placements:
                messagebox.showwarning("Warning", "No timetable to save")
                return
                
            name = tk.simpledialog.askstring("Save Timetable", 
                                           "Enter name for this timetable:")
            if name:
                description = tk.simpledialog.askstring("Save Timetable", 
                                                      "Enter description (optional):")
                self.db.save_timetable(
                    name, description, self.placements,
                    self.start_date_var.get(),
                    self.end_date_var.get()
                )
                tree.delete(*tree.get_children())
                for timetable in self.db.get_saved_timetables():
                    tree.insert("", tk.END, values=timetable)
                # After saving, refresh the saved list so the user sees the
                # newly persisted timetable immediately.

        # Buttons
        btn_frame = tk.Frame(saved_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(btn_frame, text="Load Selected", 
                 command=load_selected).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Save Current", 
                 command=save_current).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Close", 
                 command=saved_window.destroy).pack(side=tk.RIGHT, padx=5)