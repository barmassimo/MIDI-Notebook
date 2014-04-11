import os
import sys
import configparser
from .midi_notebook_context import MidiNotebookContext


class Configuration():

    CONFIG_FILE_NAME = "midi_notebook.config"

    def __init__(self):
        self.config_file_path = os.path.join(
            os.path.dirname(sys.argv[0]), self.CONFIG_FILE_NAME)

    def read(self, context):
        if not os.path.isfile(self.config_file_path):
            return

        config = configparser.RawConfigParser()
        config.read(self.config_file_path)

        context.input_port = config.getint('MIDI_PORTS', 'input')
        context.output_port = config.getint('MIDI_PORTS', 'output')

        config.getint('MIDI_PORTS', 'output')

        for n in range(context.n_loops):
            context.loop_toggle_message_signature[n] =\
                [
                    MidiNotebookContext.MidiEventTypes.CONTROL_CHANGE,
                    config.getint(
                        'LOOP_MIDI_TRIGGERS', 'loop_{0}_ccn'.format(n)),
                    config.getint(
                        'LOOP_MIDI_TRIGGERS', 'loop_{0}_value'.format(n)),
                ]

    def write(self, context):
        config = configparser.ConfigParser()
        config['MIDI_PORTS'] = {
            'input': context.input_port,
            'output': context.output_port,
        }

        config['LOOP_MIDI_TRIGGERS'] = {}

        for n, signature in enumerate(context.loop_toggle_message_signature):
            config['LOOP_MIDI_TRIGGERS'][
                'loop_{0}_ccn'.format(n)] = str(signature[1])
            config['LOOP_MIDI_TRIGGERS'][
                'loop_{0}_value'.format(n)] = str(signature[2])

        with open(self.config_file_path, 'w') as config_file:
            config.write(config_file)
