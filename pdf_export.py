"""
PDF Export Module

This module provides functionality for exporting examination timetables to PDF format.
It utilises the ReportLab library to generate professional-looking documents with tables
and styling, supporting both full timetables and filtered views for individual students.
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

def export_to_pdf(placements, filename="timetable.pdf", student_names=None, filter_student=None):
    """
    Exports the given placements to a PDF file with a formatted table.
    Optionally filters the timetable to show only exams for a specific student.
    """
    try:
        # Create a landscape A4 document
        doc = SimpleDocTemplate(filename, pagesize=landscape(A4))
        elements = []
        styles = getSampleStyleSheet()
        
        # Set the title, appending student name if filtering
        title = "Exam Timetable"
        if filter_student:
            title += f" - {student_names.get(filter_student, filter_student)}"
        elements.append(Paragraph(title, styles['Title']))
        elements.append(Spacer(1, 12))

        # Prepare table data with headers
        data = [["Exam ID", "Subject", "Room", "Date", "Start", "End"]]
        for p in placements:
            # Skip placements not involving the filtered student
            if filter_student and filter_student not in p.student_ids:
                continue
            data.append([p.exam_id, p.subject, p.room_id, p.date, p.start, p.end])

        # Generate table only if there is data beyond headers
        if len(data) > 1:
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#4F81BD")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.lightgrey])
            ]))
            elements.append(table)
        else:
            # Show message if no exams for this student
            elements.append(Paragraph("No exams assigned to this student.", styles['Normal']))
        
        doc.build(elements)
    except Exception as e:
        raise Exception(f"Failed to create PDF '{filename}': {str(e)}")