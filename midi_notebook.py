import threading
import sys
import time
import signal

from  midi_notebook.midi_notebook_context import MidiNotebookContext

# CONFIGURATION
configuration = { 
    'long_pause': 30, # save automatically a new file if there are not new events for 30 seconds
    'midi_file_name': 'midi_notebook_{0}.mid', # {0} = datetime
    'bpm': 120, # beats per minute
    'monitor': True, # print input midi messages
    'write_message_function': print # loggin function
}
# /CONFIGURATION

def signal_handler(signal, frame):
    MidiNotebookContext().save_midi_file()
    print('Bye.')
    sys.exit(0) 

def init_app():
    MidiNotebookContext(configuration) # init

    input_port = None
    for arg in sys.argv[1:]:
        if arg.startswith("-in"): input_port = int(arg[3:])
            
    MidiNotebookContext().print_info(input_port)
        
    MidiNotebookContext().start_recording(input_port)
    
    signal.signal(signal.SIGINT, signal_handler)
    print('Press Ctrl+C to save and exit.')

def main_app():
    while (True):
        try:
            time.sleep(1)
            if (MidiNotebookContext().is_time_to_save()): 
                MidiNotebookContext().save_midi_file()
        except IOError: 
            pass

init_app()
main_app()