from dataclasses import dataclass

@dataclass
class Exam:
    exam_id: str
    subject: str
    duration: int  # in minutes
    student_ids: list

@dataclass
class Room:
    room_id: str
    capacity: int

@dataclass
class Placement:
    exam_id: str
    subject: str
    room_id: str
    date: str
    start: str
    end: str
    student_ids: list