# MIDI-Notebook - A MIDI monitor, looper, and recorder written in Python.
# Copyright (C) 2014 Massimo Barbieri - http://www.massimobarbieri.it
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
    [[21, 127], [22, 127], [23, 127], [24, 127], ],
}
# /CONFIGURATION


def signal_handler(signal, frame):
    MidiNotebookContext().save_midi_file()
    MidiNotebookContext().write_message('Bye.')
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
    context.write_message('Press Ctrl+C to save and exit.')

    context.start_main_loop()

main()
