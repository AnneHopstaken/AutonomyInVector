import anki_vector
from anki_vector.events import Events
import datetime
from datetime import date
import time

#Toggle variable used to give Vector autonomy when a wake word (voice command) is heard
wake_word = False

#Waiting intervals for different processes (in seconds):
VECTOR_CONTROL_INTERVAL = 1
SDK_CONTROL_INTERVAL = 0.5
ANIMATION_CHECK_INTERVAL = 2
RECONNECT_INTERVAL = 10
AWAIT_QUESTION_INTERVAL = 25
RESET_SUBROUTINE_INTERVAL = 300
HIGH_AUTONOMY_INTERVAL = 300

#Dates on which Vector's autonomy should be low:
low_days = [
    datetime.datetime(2022,1,1).date(),
    #datetime.datetime(year,month,day).date(),
    #datetime.datetime(year,month,day).date()
]

#Loop that waits until Vector is done executing the action related to the voice command
def check_animation(robot: anki_vector.Robot):
    while robot.status.is_animating:
        time.sleep(ANIMATION_CHECK_INTERVAL)
    global wake_word
    wake_word = False

#Loop that is triggered when the wake word is heard
def on_wake_word(robot: anki_vector.Robot, event_type, event):
    eventinfo = str(event)
    global wake_word
    if eventinfo.startswith('wake_word_begin'): 
        #'Hey Vector' heard, allow Vector the control to listen to the actual command
        wake_word = True
    elif eventinfo.startswith('wake_word_end') and 'intent_json' in eventinfo:
        #Actual command heard, Vector has control to execute it 
        robot.conn.release_control()
        if 'knowledge_question' in eventinfo: 
            #A question was asked. Since Vector answering is not classified as an animation, this interval gives Vector the time to answer
            time.sleep(AWAIT_QUESTION_INTERVAL)
        else:
            #The command was not a question, Vector will get some time to start the associated animation
            time.sleep(ANIMATION_CHECK_INTERVAL) 
        check_animation(robot)
    else:
        wake_word = False

#Loop that evaluates whether Vector should be reset already
#Used to go back to the connect loop in case Vector is turned off, or as an emergency in case Vector keeps its autonomy after executing a voice command
def subroutine(robot: anki_vector.Robot):
    start_time = time.time()
    end_time = start_time + RESET_SUBROUTINE_INTERVAL
    global wake_word
    while time.time() < end_time:
        #The reset timer has not expired, so the low autonomy loop is started. Vector will lose and gain control rapidly to ensure he stands still, but can still respond to voice commands
        if not wake_word:
            robot.conn.request_control()
            time.sleep(SDK_CONTROL_INTERVAL)
            robot.conn.release_control()
            time.sleep(VECTOR_CONTROL_INTERVAL)

#Establishes a connection with Vector on high autonomy days and subscribes to the wake word event 
#Needed to give Vector control to execute a voice command
def connect():
    with anki_vector.Robot(behavior_control_level = None) as robot:
        robot.events.subscribe(on_wake_word, Events.wake_word)
        subroutine(robot)

#Checks the date. On high autonomy days, the code sleeps for 5 minutes. On low autonomy days, a connection with Vector will be established to take control of the robot
def attempt_connection():
    while True:
        try:
            if date.today() in low_days:
                global wake_word
                wake_word = False
                connect()
            else:
                print('High autonomy day') 
                time.sleep(HIGH_AUTONOMY_INTERVAL) 
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            print(e)
        time.sleep(RECONNECT_INTERVAL)

#Main loop, allows the code to run continuously
if __name__ == "__main__":
    attempt_connection()