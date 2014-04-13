# MIDI-Notebook - A prototypal MIDI monitor, looper, and recorder written in Python.
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
import os
import functools
import tkinter
from midi_notebook.midi_notebook_context import MidiNotebookContext
from midi_notebook.midi_notebook_config import Configuration

CONFIGURATION = {

    # save automatically a new file if there are not new events for N seconds
    # (None  = no autosave)
    'long_pause': None,

    # MIDI export file pattern ({0} = datetime)
    'midi_file_name': 'midi_notebook_{0}.mid',

    # beats per minute for MIDI files
    'bpm': 120,

    # print input MIDI messages if True
    'monitor': True,

    # signatures for loop control special messages
    'loop_toggle_message_signature':
    [[21, 127], [22, 127], [23, 127], [24, 127], ],
}
# /CONFIGURATION


class Application():

    """The ugly tkinter Application"""

    def __init__(self, context):
        self.blink = 0

        self.context = context
        context.write_message_function = self.write_txt

        self.update_lock = threading.Lock()
        self.update_messages = []
        self.midi_config_changing = False

        self.build_gui()
        self.midi_message_loop()

    def build_gui(self):
        self.root = tkinter.Tk()
        self.root.title('MIDI Notebook')
        self.root.wm_iconbitmap(
            os.path.join(os.path.dirname(sys.argv[0]), 'favicon.ico'))

        # menu
        self.menubar = tkinter.Menu(self.root)

        # menu/file
        self.file = tkinter.Menu(self.menubar, tearoff=0)

        self.file.add_command(
            label="Save MIDI file", command=self.save, accelerator="Ctrl+S")

        self.file.add_separator()

        self.file.add_command(
            label="Exit", command=self.root.quit, accelerator="Ctrl+Q")

        # menu/tools
        self.tools = tkinter.Menu(self.menubar, tearoff=0)

        ports = tkinter.Menu(self.tools, tearoff=0)
        self.output_port = tkinter.IntVar()
        self.output_port.set(self.context.output_port)

        for n, port_name in enumerate(self.context.get_output_ports()):
            ports.add_radiobutton(label="[{0}] {1}".format(n, port_name.decode('utf-8')), variable=self.output_port,
                                  value=n, command=functools.partial(self.set_output_port, value=n))

        self.tools.add_cascade(label="Select MIDI out port", menu=ports)

        self.tools.add_command(label="Reset song and loops",
                               command=self.clean_all)

        self.menubar.add_cascade(label="File", menu=self.file)
        self.menubar.add_cascade(label="Tools", menu=self.tools)
        self.root.config(menu=self.menubar)

        self.root.bind_all("<Control-q>", self.quit)
        self.root.bind_all("<Control-s>", self.save)

        # grid
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0, minsize=140)
        self.root.rowconfigure(2, weight=0, minsize=2)

        self.txt = tkinter.Text(
            self.root, height='20', width='90', bg='black', fg='#33ff33')
        self.txt.grid(row=0, column=0, columnspan=self.context.n_loops,
                      sticky=tkinter.W + tkinter.E + tkinter.N + tkinter.S)

        self.loop_buttons = []
        self.loop_midi_ccn = []
        self.loop_midi_values = []

        for n in range(0, self.context.n_loops):
            loop_n = functools.partial(self.loop, n)

            # big button
            btn = tkinter.Button(self.root, command=loop_n)

            self.loop_buttons.append(btn)
            btn.config(font=("Helvetica", 12))
            btn.grid(row=1, column=n,
                     sticky=tkinter.W + tkinter.E + tkinter.N + tkinter.S)

            # MIDI ccn and val
            frame = tkinter.Frame(self.root)

            tkinter.Label(frame, text="MIDI CCn").pack(side=tkinter.LEFT)

            intVar = tkinter.IntVar()
            intVar.set(0)
            self.loop_midi_ccn.append(intVar)
            entry = tkinter.Entry(frame, textvariable=intVar, width=4)
            entry.pack(side=tkinter.LEFT)
            entry.bind('<Key>', self.updating_midi_config)
            entry.bind(
                '<FocusOut>', functools.partial(self.update_midi_config, n))

            tkinter.Label(frame, text="Val").pack(side=tkinter.LEFT)

            intVar = tkinter.IntVar()
            intVar.set(0)
            self.loop_midi_values.append(intVar)
            entry = tkinter.Entry(frame, textvariable=intVar, width=4)
            entry.pack(side=tkinter.LEFT)
            entry.bind('<Key>', self.updating_midi_config)
            entry.bind(
                '<FocusOut>', functools.partial(self.update_midi_config, n))

            frame.grid(row=2, column=n, sticky=tkinter.E + tkinter.W)

            self.root.columnconfigure(n, weight=1)

        self.default_button_colors = (self.loop_buttons[0]['fg'],
                                      self.loop_buttons[0]['bg'])

        self.record_button_colors = ('red', 'white')

    def updating_midi_config(self, evt):
        self.midi_config_changing = True

    def update_midi_config(self, n, evt):
        self.context.loop_toggle_message_signature[n] = [
            self.loop_midi_ccn[n].get(), self.loop_midi_values[n].get()]
        self.midi_config_changing = False
        conf = Configuration()
        conf.write(self.context)

    def midi_message_loop(self):
        self.blink = 1 - self.blink

        self.playback_colors = [self.default_button_colors,
                                self.default_button_colors[::-1]]

        self.record_colors = [self.record_button_colors,
                              self.record_button_colors[::-1]]

        self.update_lock.acquire()
        while len(self.update_messages) > 0:
            msg = self.update_messages.pop(0)
            self.txt.insert(tkinter.INSERT, msg)
            self.txt.see(tkinter.END)
        self.update_lock.release()

        for n, l in enumerate(self.context.loops):
            # status and blinking

            self.loop_buttons[n][
                'text'] = 'Loop ' + str(n) + (' master' if n == 0 else '') + '\n' + l.status

            if l.is_recording and l.start_recording_time is None:
                self.loop_buttons[n]['fg'], self.loop_buttons[n]['bg'], =\
                    self.record_colors[self.blink][0],\
                    self.record_colors[self.blink][1]
            elif l.is_recording:
                self.loop_buttons[n]['fg'], self.loop_buttons[n]['bg'], =\
                    self.record_button_colors[1],\
                    self.record_button_colors[0]
            elif l.is_playback:
                if l.waiting_for_sync:
                    self.loop_buttons[n]['fg'], self.loop_buttons[n]['bg'] =\
                        self.playback_colors[self.blink][0],\
                        self.playback_colors[self.blink][1]
                else:
                    self.loop_buttons[n]['fg'], self.loop_buttons[n]['bg'] =\
                        self.default_button_colors[1],\
                        self.default_button_colors[0]
            else:
                self.loop_buttons[n].configure(
                    fg=self.default_button_colors[0],
                    bg=self.default_button_colors[1])

            # MIDI ccn and values config
            if not self.midi_config_changing:
                self.loop_midi_ccn[n].set(
                    self.context.loop_toggle_message_signature[n][0])
                self.loop_midi_values[n].set(
                    self.context.loop_toggle_message_signature[n][1])

        self.root.update()

        self.root.after(300, self.midi_message_loop)

    def save(self, unused=None):
        self.context.save_midi_file()

    def quit(self, unused):
        self.root.quit()

    def clean_all(self):
        self.context.clean_all()

    def loop(self, n):
        self.context.toggle_loop(n)

    def set_output_port(self, value):
        self.context.output_port = value
        conf = Configuration()
        conf.write(self.context)

    def write_txt(self, txt):
        self.update_lock.acquire()
        self.update_messages.append(str(txt) + '\n')
        self.update_lock.release()


class Recorder(threading.Thread):

    def __init__(self, context):
        super().__init__()
        self.context = context

    def run(self):
        self.context.print_info(show_usage=False)
        self.context.start_recording()
        self.context.start_main_loop()


def main():
    context = MidiNotebookContext(CONFIGURATION)  # init

    # read config if exists
    conf = Configuration()
    conf.read(context)

    for arg in sys.argv[1:]:
        if arg.startswith("-in"):
            context.input_port = int(arg[3:])
        if arg.startswith("-out"):
            context.output_port = int(arg[4:])

    app = Application(context)

    recorder = Recorder(context)
    recorder.daemon = True
    recorder.start()
    app.root.mainloop()

main()
