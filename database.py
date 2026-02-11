"""
Database Module for Timetable Persistence

This module provides database functionality for storing and retrieving
generated timetables. It uses SQLite to persist timetable
metadata and individual exam placements, allowing users to save and
load their scheduling results.
"""

import sqlite3
from datetime import datetime
from models import Placement

class TimetableDatabase:
    """
    Handles all database operations.
    """
    def __init__(self, db_file="timetables.db"):
        self.db_file = db_file
        self.conn = sqlite3.connect(self.db_file)
        self.create_tables()
    
    def close(self):
        """Close the database connection if it is open"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_tables(self):
        """Creates the necessary database tables if they do not exist"""
        cursor = self.conn.cursor()
        
        # Create table for storing timetable metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS timetables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_date TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                description TEXT
            )
        ''')
        
        # Create table for individual exam placements which are linked to timetables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS placements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timetable_id INTEGER,
                exam_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                room_id TEXT NOT NULL,
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                student_ids TEXT NOT NULL,
                FOREIGN KEY (timetable_id) REFERENCES timetables (id)
            )
        ''')
        
        self.conn.commit()

    def save_timetable(self, name, description, placements, start_date, end_date):
        """
        Saves a complete timetable to the database which includes metadata and all placements.
        Creates a new timetable entry and associates all exam placements with it.
        """
        cursor = self.conn.cursor()
        
        # Insert timetable metadata into the main table
        cursor.execute('''
            INSERT INTO timetables (name, created_date, start_date, end_date, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             start_date, end_date, description))
        
        timetable_id = cursor.lastrowid
        
        # Insert each placement record linked to the timetable
        for p in placements:
            cursor.execute('''
                INSERT INTO placements (
                    timetable_id, exam_id, subject, room_id,
                    date, start_time, end_time, student_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timetable_id, p.exam_id, p.subject, p.room_id,
                  p.date, p.start, p.end, ";".join(p.student_ids)))
        
        self.conn.commit()

    def get_saved_timetables(self):
        """
        Gets a list of all saved timetables with their metadata.
        Returns tuples of (id, name, created_date, description) ordered by creation date.
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, name, created_date, description FROM timetables ORDER BY created_date DESC')
        return cursor.fetchall()

    def load_timetable(self, timetable_id):
        """
        Loads all placements for a specific timetable from the database.
        Reconstructs Placement objects from the stored data.
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT exam_id, subject, room_id, date, start_time, end_time, student_ids FROM placements WHERE timetable_id = ?', (timetable_id,))
        rows = cursor.fetchall()
        
        # Reconstruct Placement objects from database records
        placements = []
        for row in rows:
            exam_id, subject, room_id, date, start_time, end_time, student_ids = row
            placement = Placement(
                exam_id=exam_id,
                subject=subject,
                room_id=room_id,
                date=date,
                start=start_time,
                end=end_time,
                student_ids=student_ids.split(';')
            )
            placements.append(placement)
        return placements