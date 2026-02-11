from collections import defaultdict
from datetime import datetime, timedelta, date, time
from models import Exam, Room, Placement
import random

class TimetableEngine:
    """
    The TimetableEngine class is responsible for generating examination timetables.
    It uses backtracking algorithms combined with a conflict graph to schedule
    exams while following many constraints.
    """
    def __init__(self, rooms, exams, student_names,
                 start_date=date.today(),
                 end_date=None,
                 start_time=time(9, 0),
                 end_time=time(15, 30),
                 max_exams_day=3,
                 min_gap=15,
                 exclude_weekends=True,
                 custom_time_slots=None,
                 excluded_dates=None,
                 min_days_between_exams=1,
                 spread_evenly=True):
        # Perform basic validation to ensure all data that is needed is provided
        if not rooms:
            raise ValueError("No rooms provided")
        if not exams:
            raise ValueError("No exams provided")
        if not student_names:
            raise ValueError("No student names provided")

        # Store the input data and configuration parameters
        self.rooms = rooms
        self.exams = exams
        self.student_names = student_names
        self.start_date = start_date
        self.end_date = end_date or (start_date + timedelta(days=14))
        self.start_time = start_time
        self.end_time = end_time
        self.max_exams_day = max_exams_day
        self.min_gap = min_gap
        self.exclude_weekends = exclude_weekends
        self.custom_time_slots = custom_time_slots or {}
        self.excluded_dates = set(excluded_dates or [])

        self.min_days_between_exams = min_days_between_exams
        self.spread_evenly = spread_evenly

        # Initialise internal state variables
        self.clash_log = []
        self.conflict_graph = self._build_exam_graph()
        self._slot_cache = {}  # Cache for _get_time_slot results
        self.backtrack_iterations = 0

    def _build_exam_graph(self):
        """
        Makes a conflict graph where exams are represented as a vertex.
        An edge between two vertices means that the corresponding exams cannot be
        scheduled at the same time because of shared students this identifies conflicts.
        """
        graph = defaultdict(set)
        for i, exam1 in enumerate(self.exams):
            for j, exam2 in enumerate(self.exams[i+1:], i+1):
                # Check if the two exams share any students, this shows if there is a conflict
                if set(exam1.student_ids) & set(exam2.student_ids):
                    graph[exam1.exam_id].add(exam2.exam_id)
                    graph[exam2.exam_id].add(exam1.exam_id)
        return graph

    def _is_valid_date(self, d):
        """
        Determines if a given date is suitable for scheduling examinations
        considering: exclusions, weekend restrictions, and the overall date range.
        """
        # Check if the date is explicitly excluded by the user
        if d.strftime('%Y-%m-%d') in self.excluded_dates:
            return False
        # Exclude weekends if the option is enabled
        if self.exclude_weekends and d.weekday() >= 5:
            return False
        # Ensure the date falls within the user-given start and end dates
        return self.start_date <= d <= self.end_date

    def _calculate_total_slots(self):
        """
        Calculates the total number of available time slots for scheduling examinations
        by counting valid days and multiplying by the maximum exams per day.
        """
        available_days = 0
        current_date = self.start_date
        # Iterates through each date in the range to count the valid days
        while current_date <= self.end_date:
            if self._is_valid_date(current_date):
                available_days += 1
            current_date += timedelta(days=1)
        return available_days * self.max_exams_day

    def _get_time_slot(self, slot_number):
        """
        Determines the specific date and time for a given slot number,
        it uses caching for efficiency and supporting custom time slots.
        """
        # Check if the result is already cached to avoid redoing it
        if slot_number in self._slot_cache:
            return self._slot_cache[slot_number]
        
        # Calculate which day and slot within the day this slot number represents
        days_passed = slot_number // self.max_exams_day
        slot_in_day = slot_number % self.max_exams_day
        
        current_date = self.start_date
        valid_days_found = 0
        
        # Jump/Advance to the correct date by counting valid days
        while valid_days_found <= days_passed:
            if self._is_valid_date(current_date):
                valid_days_found += 1
            if valid_days_found <= days_passed:
                current_date += timedelta(days=1)
        
        # Check if a custom time slot is defined for this date
        date_str = current_date.strftime('%Y-%m-%d')
        if date_str in self.custom_time_slots:
            start_str = self.custom_time_slots[date_str]['start']
            result = datetime.combine(current_date, 
                                  datetime.strptime(start_str, '%H:%M').time())
        else:
            # Calculate the regular time slot by dividing the day into equal parts
            total_minutes = (datetime.combine(date.min, self.end_time) - 
                            datetime.combine(date.min, self.start_time)).seconds // 60
            minutes_per_slot = total_minutes // self.max_exams_day
            slot_minutes = slot_in_day * minutes_per_slot
            
            slot_time = (datetime.combine(date.min, self.start_time) + 
                        timedelta(minutes=slot_minutes)).time()
            result = datetime.combine(current_date, slot_time)
        
        # Store the result in the cache for future use
        self._slot_cache[slot_number] = result
        return result

    def _find_room(self, exam, slot, solution):
        """
        Identifies an available room for a specific exam in a given time slot,
        making sure the room has enough capacity and is not already being used for an exam.
        """
        # Collect rooms that are already assigned to other exams in this slot
        used_rooms = {
            solution[e][1] for e in solution 
            if solution[e][0] == slot
        }
        
        # Search for a suitable room that meets capacity requirements and is free
        for room in self.rooms:
            if (room.capacity >= len(exam.student_ids) and 
                room.room_id not in used_rooms):
                return room.room_id
        return None

    def generate(self):
        """
        Generates the exam timetable by attempting to schedule all exams
        while respecting various constraints. Uses backtracking with fallback to greedy
        scheduling if needed and provides detailed logging of any issues encountered.
        """
        # Initialise the placements list and clash log
        self.placements = []
        self.clash_log = []
        
        # Construct the conflict graph to identify exam conflicts
        exam_graph = self._build_exam_graph()
        total_slots = self._calculate_total_slots()
        
        # Check if there are sufficient time slots for all exams
        if total_slots < len(self.exams):
            self.clash_log.append(f"IMPOSSIBLE: Not enough time slots")
            self.clash_log.append(f"  - Total exams to schedule: {len(self.exams)}")
            self.clash_log.append(f"  - Available time slots: {total_slots}")
            self.clash_log.append(f"  - Shortfall: {len(self.exams) - total_slots} slots")
            self.clash_log.append("\nReasons for insufficient slots:")
            
            # Provides a detailed breakdown of available days and slots
            available_days = 0
            current_date = self.start_date
            while current_date <= self.end_date:
                if self._is_valid_date(current_date):
                    available_days += 1
                current_date += timedelta(days=1)
            
            self.clash_log.append(f"  - Calendar period: {(self.end_date - self.start_date).days + 1} days")
            self.clash_log.append(f"  - Available days (after weekends/exclusions): {available_days} days")
            self.clash_log.append(f"  - Max exams per day: {self.max_exams_day}")
            self.clash_log.append(f"  - Calculation: {available_days} days x {self.max_exams_day} exams/day = {total_slots} slots")
            self.clash_log.append("\nSuggestions to fix:")
            self.clash_log.append("  1. Increase the exam period (extend end date)")
            self.clash_log.append("  2. Increase max exams per day")
            self.clash_log.append("  3. Remove excluded dates")
            self.clash_log.append("  4. Enable weekends if possible (uncheck 'Exclude Weekends')")
            return False
        
        # Sort examinations by their constraint complexity to prioritise the difficult ones
        sorted_exams = sorted(
            self.exams,
            key=lambda e: (len(exam_graph[e.exam_id]), len(e.student_ids)),
            reverse=True
        )
        
        # Adjust the maximum exams per day if necessary to accommodate conflicts
        max_conflicts = max(len(exam_graph[e.exam_id]) for e in self.exams)
        if max_conflicts >= self.max_exams_day:
            self.max_exams_day = max_conflicts + 1
            self.clash_log.append(f"Adjusted max exams per day to {self.max_exams_day} to handle conflicts")
        
        # Attempt to schedule using the backtracking algorithm
        solution = self._backtrack_schedule(sorted_exams, exam_graph, total_slots)
        
        if solution:
            # Convert the solution into placement objects
            self._convert_solution_to_placements(solution)
            self.clash_log.append("Successfully scheduled all exams")
            return True
        else:
            self.clash_log.append("IMPOSSIBLE: No valid schedule exists after exhausting all constraint combinations")
            # Provides detailed explanation of why scheduling failed
            self._explain_impossibility(sorted_exams, exam_graph, total_slots)
            return False

    def _backtrack_schedule(self, exams, graph, total_slots, partial_solution=None, depth=0):
        """
        Recursively attempts to schedule examinations using backtracking,
        with pruning to reduce search space and a timeout mechanism to prevent excessive computation.
        """
        if partial_solution is None:
            partial_solution = {}
            self.backtrack_iterations = 0
        
        self.backtrack_iterations += 1
        
        # Implement a timeout to avoid infinite loops in complex cases
        if self.backtrack_iterations > 10000:
            self.clash_log.append("Scheduling timed out - trying greedy approach instead")
            return self._greedy_schedule(exams, graph, total_slots)
        
        # Base case: if all exams have been scheduled, return the solution
        if depth == len(exams):
            return partial_solution
        
        current_exam = exams[depth]
        neighbors = graph[current_exam.exam_id]
        
        # Collect valid slots for this exam this limits the search to improve performance
        valid_slots = []
        for slot in range(min(total_slots, depth * 5 + 20)):  # Limit search range
            if self._is_valid_slot(slot, current_exam, neighbors, partial_solution):
                valid_slots.append(slot)
        
        # Attempt to place the exam in each valid slot
        for slot in valid_slots:
            room_id = self._find_room(current_exam, slot, partial_solution)
            if room_id:
                partial_solution[current_exam.exam_id] = (slot, room_id)
                
                # Recursively attempt to schedule the remaining exams
                result = self._backtrack_schedule(exams, graph, total_slots, partial_solution, depth + 1)
                if result:
                    return result
                
                # If scheduling failed remove this assignment and try the next slot
                del partial_solution[current_exam.exam_id]
        
        return None
    
    def _greedy_schedule(self, exams, graph, total_slots):
        """
        Gives a greedy fallback scheduling approach when backtracking becomes too slow.
        Attempts to place each exam in the first available valid slot without backtracking.
        """
        solution = {}
        
        for exam in exams:
            scheduled = False
            neighbors = graph[exam.exam_id]
            
            # Search through all slots to find the first available one for this exam
            for slot in range(total_slots):
                if self._is_valid_slot(slot, exam, neighbors, solution):
                    room_id = self._find_room(exam, slot, solution)
                    if room_id:
                        solution[exam.exam_id] = (slot, room_id)
                        scheduled = True
                        break
            
            # If no slot could be found the greedy approach has failed
            if not scheduled:
                self.clash_log.append(f"Could not schedule exam {exam.exam_id}")
                return None
        
        return solution

    def _is_valid_slot(self, slot, exam, neighbors, solution):
        """
        Verifies if a specific time slot is suitable for an examination, this considers
        considering room availability and constraints related to conflicting exams.
        """
        # First perform a quick check for room availability as it's the fastest validation
        if not self._find_room(exam, slot, solution):
            return False
        
        # Ensure no conflicting exams are scheduled too close together
        for neighbor in neighbors:
            if neighbor in solution:
                neighbor_slot = solution[neighbor][0]
                neighbor_date = self._get_time_slot(neighbor_slot).date()
                slot_date = self._get_time_slot(slot).date()
                
                # Enforce the minimum gap between related examinations
                days_gap = abs((slot_date - neighbor_date).days)
                if days_gap < self.min_days_between_exams:
                    return False
        
        return True

    def _convert_solution_to_placements(self, solution):
        """
        Transforms the internal solution dictionary into a list of Placement objects,
        calculating the exact start and end times for each examination.
        """
        for exam_id, (slot, room_id) in solution.items():
            exam = next(e for e in self.exams if e.exam_id == exam_id)
            start_time = self._get_time_slot(slot)
            end_time = start_time + timedelta(minutes=exam.duration)
            
            self.placements.append(
                Placement(
                    exam_id, #'E1'
                    exam.subject,  #'Maths'                  
                    room_id, #'R101'
                    start_time.strftime("%Y-%m-%d"), #'2023-12-01'
                    start_time.strftime("%H:%M"), #'09:00'
                    end_time.strftime("%H:%M"), #'11:00'
                    exam.student_ids #['S1', 'S2', 'S3']
                )
            )
        # Sort the placements by date and start time for a logical order
        self.placements.sort(key=lambda p: (p.date, p.start))

    def _explain_impossibility(self, exams, graph, total_slots):
        """
        Provides an analysis or diagnostic of why scheduling failed,
        identifying constraint violations and offering suggestions for resolution.
        """
        self.clash_log.append("\nDiagnostic Analysis:")
        
        # Verify that rooms are available for scheduling
        if not self.rooms:
            self.clash_log.append("  - CRITICAL: No rooms available for scheduling")
            return
        
        # Analyse room capacity constraints
        try:
            max_capacity = max(r.capacity for r in self.rooms)
            num_rooms = len(self.rooms)
            self.clash_log.append(f"  - Rooms available: {num_rooms} (max capacity: {max_capacity} students)")
            
            oversized_exams = []
            for exam in exams:
                if len(exam.student_ids) > max_capacity:
                    oversized_exams.append((exam.exam_id, len(exam.student_ids)))
            
            if oversized_exams:
                self.clash_log.append(f"  - Room capacity violations: {len(oversized_exams)} exam(s) exceed max capacity")
                for exam_id, num_students in oversized_exams[:3]:
                    self.clash_log.append(f"    * Exam {exam_id}: {num_students} students (max room: {max_capacity})")
                if len(oversized_exams) > 3:
                    self.clash_log.append(f"    * ... and {len(oversized_exams) - 3} more exams")
        except ValueError as e:
            self.clash_log.append("  - ERROR: Problem calculating room capacities")
            return
        
        # Reassess time slot availability with current configuration
        available_days = 0
        current_date = self.start_date
        while current_date <= self.end_date:
            if self._is_valid_date(current_date):
                available_days += 1
            current_date += timedelta(days=1)

        recalculated_slots = available_days * self.max_exams_day
        self.clash_log.append(f"  - Time slots (initial calc): {total_slots}")
        self.clash_log.append(f"  - Time slots (recalculated with current settings): {recalculated_slots}")
        self.clash_log.append(f"  - Exams to schedule: {len(exams)}")

        if recalculated_slots < len(exams):
            self.clash_log.append(
                f"  - TIME CONSTRAINT VIOLATION: Need {len(exams)} slots but only have {recalculated_slots}"
            )
        
        # Identify exams that are very constrained by conflicts
        highly_constrained = []
        for exam in exams:
            conflicts = len(graph[exam.exam_id])
            if conflicts >= self.max_exams_day:
                highly_constrained.append((exam.exam_id, conflicts))
        
        if highly_constrained:
            self.clash_log.append(f"  - Exam conflict violations: {len(highly_constrained)} exam(s) over-constrained")
            for exam_id, conflicts in highly_constrained[:3]:
                self.clash_log.append(
                    f"    * Exam {exam_id}: {conflicts} conflicts, but only {self.max_exams_day} slots/day allowed"
                )
            if len(highly_constrained) > 3:
                self.clash_log.append(f"    * ... and {len(highly_constrained) - 3} more exams")
        
        # Evaluate minimum gap constraints between related exams
        if self.min_days_between_exams > 1:
            self.clash_log.append(f"  - Minimum gap constraint: {self.min_days_between_exams} days between related exams")
            
            # Identify exams with numerous related exams within a short timeframe
            for exam in exams:
                neighbors = graph[exam.exam_id]
                if len(neighbors) > 2:
                    min_period_needed = self.min_days_between_exams * len(neighbors)
                    available_period = (self.end_date - self.start_date).days
                    if min_period_needed > available_period:
                        self.clash_log.append(
                            f"    * Exam {exam.exam_id} ({len(neighbors)} related exams): needs {min_period_needed} days "
                            f"but only {available_period} days available"
                        )
                        break
        
        # Provide suggestions for resolving the scheduling issues
        self.clash_log.append("\nTo resolve, try:")
        self.clash_log.append("  - Extend the exam period (increase end date)")
        self.clash_log.append("  - Increase max exams per day")
        self.clash_log.append("  - Remove excluded dates")
        self.clash_log.append("  - Enable weekends")
        self.clash_log.append("  - Reduce minimum gap between related exams")    