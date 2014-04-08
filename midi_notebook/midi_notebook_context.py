import time
import threading
import datetime
import os
import sys

import rtmidi_python as rtmidi
from midiutil.MidiFile3 import MIDIFile

class Loop():

    def __init__(self):
        self.clean()

    def clean(self):
        self.is_playback = False
        self.is_recording = False
        self.start_recording_time = None
        self.messages_captured = []
        self.duration = None
        self.sync_delay = None
        self.waiting_for_sync = False

    @property
    def status(self):
        if self.is_recording:
            return "recording"
        elif self.is_playback:
            return "play - {0:.1f}sec".format(self.duration)
        elif self.duration is not None:
            return "stop - {0:.1f}sec".format(self.duration)
        else:
            return ""

    @property
    def is_clean(self):
        return self.duration is None

    @property
    def is_playable(self):
        return len(self.messages_captured) >= 2

    def start_recording(self):
        self.is_playback = False
        self.is_recording = True
        self.start_recording_time = None
        self.messages_captured = []
        self.duration = None
        self.sync_delay = None

    def stop_recording(self):
        if not self.is_recording:
            return
        self.is_recording = False
        self.duration = None
        if self.start_recording_time is not None:
            self.duration = time.time() - self.start_recording_time


class LoopPlayer(threading.Thread):

    def __init__(self, context, n):
        super().__init__()
        self.context = context
        self.loop = context.loops[n]
        self.is_master_loop = n == 0
        self.force_exit_activated = False

    def run(self):

        # avoid concurrency
        loop_messages_captured = self.loop.messages_captured[:]
        loop_duration = self.loop.duration
        loop_sync_delay = self.loop.sync_delay

        if len(loop_messages_captured) < 2:
            self.context.write_message("NOTHING TO PLAY. :-(")
            return

        if loop_sync_delay is None or not self.context.is_sync_active:
            loop_messages_captured[0][-1] = 0
            self.loop.waiting_for_sync = False
        else:
            loop_messages_captured[0][-1] = loop_sync_delay
            self.loop.waiting_for_sync = True

        if self.context.midi_out is None:
            self.context.midi_out = rtmidi.MidiOut()
            self.context.midi_out.open_port(self.context.output_port)

        while (True):
            self.context.loop_sync.acquire()
            if (self.is_master_loop):
                self.context.last_loop_sync = time.time()
                self.context.loop_sync.notify_all()
            else:
                if self.context.is_sync_active:
                    self.context.loop_sync.wait()
                    self.loop.waiting_for_sync = False

            self.context.loop_sync.release()

            total_time = sum(float(m[-1]) for m in loop_messages_captured[1:])

            for m in loop_messages_captured:

                if not self.loop.is_playback:
                    if not self.is_master_loop:
                        return  # master loop is never ended, only muted

                if self.force_exit_activated:
                    return

                time.sleep(float(m[-1]))

                if self.loop.is_playback:
                    self.context.midi_out.send_message(m[:-1])
                    self.context.capture_message(
                        m[:-1], float(m[-1]), loopback=True)  # loopback!

            time.sleep(loop_duration - total_time)

    def force_exit(self):
        self.force_exit_activated = True


class MetaSingleton(type):
    instance = None

    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(MetaSingleton, cls).__call__(*args, **kw)
        return cls.instance


class MidiNotebookContext(metaclass=MetaSingleton):

    class MidiEventTypes():
        NOTE_ON = 144
        NOTE_OFF = 128
        CONTROL_CHANGE = 176

    def __init__(self, configuration):

        self.long_pause = configuration['long_pause']
        self.midi_file_name = configuration['midi_file_name']
        self.bpm = configuration['bpm']
        self.monitor = configuration['monitor']
        self.write_message_function = configuration.get(
            'write_message_function', None)
        self.loop_toggle_message_signature = configuration[
            'loop_toggle_message_signature']

        self.last_event = time.time()
        self.messages_captured = []
        self.midi_in_ports = []
        self.input_port = None
        self.output_port = None
        self.midi_out = None

        self.n_loops = 4
        self.loops = [Loop() for n in range(self.n_loops)]
        self.last_toggle_loop = [0 for n in range(self.n_loops)]

        self.loop_sync = threading.Condition()
        self.last_loop_sync = None
        self.loop_threads = [None for n in range(self.n_loops)]

    def clean_all(self):
        self.last_event = time.time()
        self.messages_captured = []

        for n, l in enumerate(self.loops):
            self.clean_loop(n)
            if not self.loop_threads[n] is None:
                self.loop_threads[n].force_exit()
                self.loop_threads[n] = None

        self.last_toggle_loop = [0 for n in range(self.n_loops)]
        self.loop_sync = threading.Condition()
        self.last_loop_sync = None
        self.loop_threads = [None for n in range(self.n_loops)]

    @property
    def is_sync_active(self):
        return self.last_loop_sync is not None

    def write_message(self, message):
        if (self.write_message_function is not None):
            self.write_message_function(message)

    def print_info(self):
        self.write_message("MIDI IN PORTS:")
        for n, port_name in enumerate(self.get_input_ports()):
            selected = ""
            if n == self.input_port:
                selected = " [SELECTED] "
            self.write_message("({0}) {1}{2}".format(n, port_name, selected))

        self.write_message("")

        self.write_message("MIDI OUT PORTS:")
        for n, port_name in enumerate(self.get_output_ports()):
            selected = ""
            if n == self.output_port:
                selected = " [SELECTED] "
            self.write_message("({0}) {1}{2}".format(n, port_name, selected))

        self.write_message("")

        if self.input_port is None:
            self.write_message(
                "Usage: {0} [-inPORT] [-outPORT]".format(os.path.basename(sys.argv[0])))
            self.write_message("Recording from ALL MIDI ports.")
            self.write_message(
                "If you want to record from only one port, you can provide a -inPORT number.")
            self.write_message(
                "If you want to use playback (loop), use -outPORT number.")

        self.write_message("")

    def get_input_ports(self):
        midi_in = rtmidi.MidiIn()
        ports = midi_in.ports
        return ports

    def get_output_ports(self):
        midi_out = rtmidi.MidiOut()
        ports = midi_out.ports
        return ports

    def start_recording(self):
        if self.input_port is not None:
            self._start_recording_from_port(self.input_port)
        else:
            for n in range(len(self.get_input_ports())):
                self._start_recording_from_port(n)

    def _start_recording_from_port(self, input_port):
        midi_in = rtmidi.MidiIn()
        midi_in.callback = self.capture_message
        midi_in.open_port(input_port)
        self.midi_in_ports.append(midi_in)

    def start_loop_recording(self, n):
        # one loop a time
        for l in self.loops:
            l.stop_recording()

        self.loops[n].is_playback = False
        if not self.loop_threads[n] is None:
            self.loop_threads[n].force_exit()

        self.loops[n].start_recording()

    def stop_loop_recording(self, n):
        self.loops[n].stop_recording()

    def play_loop(self, n):
        non_master_loop_in_play_count = len(
            [l for l in self.loops[1:] if l.is_playback])

        self.loops[n].is_playback = True

        # master loop is reset only if slave loops are not playing
        need_resume_master_loop = (
            n == 0 and non_master_loop_in_play_count > 0 and not self.loop_threads[n] is None)
        if not need_resume_master_loop:
            player = LoopPlayer(self, n)
            player.daemon = True
            player.start()
            if not self.loop_threads[n] is None:
                self.loop_threads[n].force_exit()
            self.loop_threads[n] = player

    def stop_loop(self, n):
        self.loops[n].is_playback = False

    def clean_loop(self, n):
        self.loops[n].clean()
        if n == 0:
            self.last_loop_sync = None  # stop sync

    def toggle_loop(self, n):
        if time.time() - self.last_toggle_loop[n] < 0.5:  # double tap/click
            self.clean_loop(n)
            self.start_loop_recording(n)
            return

        self.last_toggle_loop[n] = time.time()

        if self.loops[n].is_playback:
            self.stop_loop(n)
        elif self.loops[n].is_recording:
            self.stop_loop_recording(n)
            if self.loops[n].is_playable:
                self.play_loop(n)
            else:
                self.loops[n].clean()
                self.start_loop_recording(n)
        elif self.loops[n].is_clean:
            self.start_loop_recording(n)
        else:
            self.play_loop(n)

    def check_loop_toggle_message_signature(self, message, n):
        signature = self.loop_toggle_message_signature[n]
        if len(message) < len(signature):
            return False

        for n2 in range(len(signature)):
            if message[n2] != signature[n2]:
                return False

        return True

    def capture_message(self, message, time_stamp, loopback=False):

        for n in range(len(self.loop_toggle_message_signature)):
            if self.check_loop_toggle_message_signature(message, n):
                self.toggle_loop(n)
                return

        # if not loopback:  # adjusting loopback messages timing
        #    time_stamp = time.time() - self.last_event
        #    print("ADJUSTED: "+str(time_stamp))

        self.last_event = time.time()
        if len(self.messages_captured) == 0:
            time_stamp = 0
        message.append(time_stamp)
        self.messages_captured.append(message)

        if self.monitor:
            self.write_message(message)

        for n in range(self.n_loops):
            if not loopback and self.loops[n].is_recording:
                self.handle_message_loop(message, n)

    def handle_message_loop(self, message, n):
        if self.loops[n].start_recording_time is None:
            if message[0] != MidiNotebookContext.MidiEventTypes.NOTE_ON:
                return  # note on is the trigger
            self.loops[n].start_recording_time = self.last_event
            if (self.is_sync_active and n > 0):
                self.loops[n].sync_delay = self.last_event - \
                    self.last_loop_sync

        self.loops[n].messages_captured.append(message)

    def is_time_to_save(self):
        if self.long_pause is None:
            return False  # no autosave
        return time.time() - self.last_event > self.long_pause

    def save_midi_file(self):
        if len(self.messages_captured) == 0:
            return

        my_midi = MIDIFile(2)
        track = 0

        my_midi.addTrackName(track, 0, "Tempo track")
        my_midi.addTempo(track, 0, self.bpm)

        track += 1
        my_midi.addTrackName(track, 0, "Song track")

        total_time = 0
        midi_messages_on = []
        midi_messages_off = []
        midi_messages_controller = []

        for message in self.messages_captured:
            if len(message) != 4:
                self.write_message("wrong length: skipping " + str(message))
                continue

            total_time += float(message[3])
            # seconds -> beat conversion
            total_time_adjusted = total_time * float(self.bpm) / float(60)
            if message[0] == MidiNotebookContext.MidiEventTypes.NOTE_ON:
                midi_messages_on.append(
                    {'note': message[1], 'velocity': message[2], 'time': total_time_adjusted})
            elif message[0] == MidiNotebookContext.MidiEventTypes.NOTE_OFF:
                midi_messages_off.append(
                    {'note': message[1], 'velocity': message[2], 'time': total_time_adjusted})
            elif message[0] == MidiNotebookContext.MidiEventTypes.CONTROL_CHANGE:
                midi_messages_controller.append(
                    {'type': message[1], 'value': message[2], 'time': total_time_adjusted})
            else:
                self.write_message("unknown message: skipping " + str(message))
                continue

        for m_on in midi_messages_on:
            for m_off in midi_messages_off:
                if m_off['note'] == m_on['note'] and m_off['time'] > m_on['time']:
                    m_on['duration'] = m_off['time'] - m_on['time']
                    m_off['note'] = -1
                    break
            else:
                m_on['duration'] = float(
                    15) * float(self.bpm) / float(60)  # suspended

        channel = 0

        for m in midi_messages_on:
            my_midi.addNote(
                track, channel, m['note'], m['time'], m['duration'], m['velocity'])

        for m in midi_messages_controller:
            my_midi.addControllerEvent(
                track, channel, m['time'], m['type'], m['value'])

        file_name = self.midi_file_name.format(
            datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        self.write_message("Saving {0} MIDI messages to {1}...".format(
            len(self.messages_captured), file_name))
        binfile = open(file_name, 'wb')
        my_midi.writeFile(binfile)
        binfile.close()
        self.messages_captured = []
        self.write_message("Saved.")

    def start_main_loop(self):
        while (True):
            try:
                time.sleep(1)
                if (self.is_time_to_save()):
                    self.save_midi_file()
            except IOError:
                pass
