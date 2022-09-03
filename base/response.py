
#TODO: Add more
def overlappedSlotResponse(title,startTime,endTime):
    return f"Requested timing overlaps with '{title}' ({startTime} - {endTime})!"

def overlappedFacultyResponse(facultyName,batchName,startTime,endTime):
    return f"{facultyName} already has a class in {batchName} at ({startTime} - {endTime})!"

def noFacultyOwnershipResponse():
    return 'The requested faculty was not invited/added by you!'

def noBatchOwnershipResponse():
    return 'The requested batch was not created by you!'

def startTimeGreaterResponse():
    return 'Start time cant be greater than or equal to End time!'
