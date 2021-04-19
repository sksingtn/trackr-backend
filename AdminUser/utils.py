
#Centralised error messages , to be used in tests too.

class ApiErrors:
    START_TIME_GREATER = 'start time cant be greater than end time!'
    NO_OWNERSHIP = 'The requested {resource} was not {action} by current admin!'
    SLOT_OVERLAP = 'Requested timing overlaps with {title} ({start_time} - {end_time})'
    FACULTY_SLOT_OVERLAP = '{faculty} already has a class in {batch} at ({start_time} - {end_time})'

