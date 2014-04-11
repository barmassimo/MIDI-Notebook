import threading
import sys
import time
import signal

from midi_notebook.midi_notebook_context import MidiNotebookContext

# CONFIGURATION
configuration = {
    # save automatically a new file if there are not new events for N seconds
    # (None  = no autosave)
    'long_pause': 60,
    'midi_file_name': 'midi_notebook_{0}.mid',  # {0} = datetime
    'bpm': 120,  # beats per minute for MIDI files
    'monitor': True,  # print input midi messages
    'write_message_function': print,  # loggin function
    'loop_toggle_message_signature':
    [[MidiNotebookContext.MidiEventTypes.CONTROL_CHANGE, 21, 127], [MidiNotebookContext.MidiEventTypes.CONTROL_CHANGE, 22, 127], [
        MidiNotebookContext.MidiEventTypes.CONTROL_CHANGE, 23, 127], [MidiNotebookContext.MidiEventTypes.CONTROL_CHANGE, 24, 127], ],
}
# /CONFIGURATION


def signal_handler(signal, frame):
    MidiNotebookContext().save_midi_file()
    print('Bye.')
    sys.exit(0)


def main():
    context = MidiNotebookContext(configuration)  # init

    for arg in sys.argv[1:]:
        if arg.startswith("-in"):
            context.input_port = int(arg[3:])
        if arg.startswith("-out"):
            context.output_port = int(arg[4:])

    context.print_info()
    context.start_recording()

    signal.signal(signal.SIGINT, signal_handler)
    print('Press Ctrl+C to save and exit.')

    context.start_main_loop()

main()
