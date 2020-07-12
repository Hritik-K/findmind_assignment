# findmind_assignment
Assignment provided by findmind for backend development wfh internship
Assignment instructions:
    Create a task assignment rest Api  having the ability to:-
    1) Add Task  (Add task name & due date)
    2) Delete Task  
    3) Update a Task (This can include marking the task as complete or  updating the due date)
    4) View a Task 
    5) Share task with another user using their email (Only view acces)
    Note: Use FastAPI as framework (https://fastapi.tiangolo.com/) and Motor (https://motor.readthedocs.io/en/stable/index.html) as MongoDb Driver.

Note: instead of sharing via mail, view access has been provided to another user, which they can view on their system

to test if everything is working as expected:
  download main.py
  make sure following libraries are installed on your system (with the dependencies that should be automatically installed with them):
    fastapi, uvicorn, motor, python-multipart, python-jose[cryptography], passlib[bcrypt]
    
