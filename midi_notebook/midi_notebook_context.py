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
    
    @property
    def is_clean(self):
        return self.duration is None
        
    def start_recording(self):
        self.is_playback = False
        self.is_recording = True
        self.start_recording_time = None
        self.messages_captured = []
        self.duration = None
        
    def stop_recording(self):
        self.is_playback = False
        self.is_recording = False
        self.duration = None
        if not self.start_recording_time is None: self.duration = time.clock() - self.start_recording_time

class LoopPlayer(threading.Thread):
    def __init__(self, context):
        super().__init__()
        self.context = context
        
    def run(self):
        loop_messages_captured = self.context.loop.messages_captured[:] # avoid concurrency
        if len(loop_messages_captured)<2:
            self.context.write_message("NOTHING TO PLAY. :-(");
            return
        
        if self.context.midi_out is None:
            self.context.midi_out = rtmidi.MidiOut()
            self.context.midi_out.open_port(self.context.output_port)
            
        first_event_time = float(loop_messages_captured[0][-1])
        
        while (True):
            first = True
            elapsed_time=0
            total_time = sum(float(m[-1]) for m in loop_messages_captured[1:])
            
            for m in loop_messages_captured:
                
                if first: 
                    pause = 0
                    first = False
                else:
                    pause = float(m[-1])
                    
                if not self.context.loop.is_playback: 
                    return
                    
                time.sleep(pause)
                self.context.midi_out.send_message(m[:-1])
                self.context.capture_message(m[:-1], float(m[-1]), loopback=True) # loopback!
            
            time.sleep(self.context.loop.duration-total_time)
                
class MetaSingleton(type):
    instance = None
    def __call__(self, *args, **kw):
        if self.instance == None:
            self.instance = super(MetaSingleton, self).__call__(*args, **kw)
        return self.instance

class MidiNotebookContext(metaclass = MetaSingleton):
    
    def __init__(self, configuration):
        
        self.long_pause = configuration['long_pause']
        self.midi_file_name = configuration['midi_file_name']
        self.bpm = configuration['bpm']
        self.monitor = configuration['monitor']
        self.write_message_function = configuration.get('write_message_function', None)
        self.loop_toggle_message_signature = configuration['loop_toggle_message_signature']
        
        time.clock()
        self.last_event = time.clock()
        self.messages_captured = []
        self.midi_in_ports = []
        self.input_port = None
        self.output_port = None
        self.midi_out = None
        self.loop = Loop()
        self.last_toggle_loop = 0
        
    def write_message(self, message):
        if (not self.write_message_function is None):
            self.write_message_function(message)
            
    def print_info(self):
        self.write_message("MIDI IN PORTS:")
        for n, port_name in enumerate(self.get_input_ports()):
            selected = ""
            if n==self.input_port: selected = " [SELECTED] "
            self.write_message("({0}) {1}{2}".format(n, port_name, selected))   
            
        self.write_message("")

        self.write_message("MIDI OUT PORTS:")
        for n, port_name in enumerate(self.get_output_ports()):
            selected = ""
            if n==self.output_port: selected = " [SELECTED] "
            self.write_message("({0}) {1}{2}".format(n, port_name, selected))               
            
        self.write_message("")

        if self.input_port is None:
            self.write_message("Usage: {0} [-inPORT] [-outPORT]".format(os.path.basename(sys.argv[0])))
            self.write_message("Recording from ALL midi ports.")
            self.write_message("If you want to record from only one port, you can provide a -inPORT number.")   
            self.write_message("If you want to use playback (loop), use -outPORT number.")   
            
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
        if not self.input_port is None:
            self._start_recording_from_port(self.input_port)
        else:
            for n in range(len(self.get_input_ports())):
                self._start_recording_from_port(n)
        
    def _start_recording_from_port(self, input_port):
        midi_in=rtmidi.MidiIn()
        midi_in.callback = self.capture_message
        midi_in.open_port(input_port)
        self.midi_in_ports.append(midi_in)
        
    def start_loop_recording(self):
        self.write_message("START RECORDING.")
        self.loop.start_recording()
        
    def stop_loop_recording(self):
        self.write_message("STOP RECORDING.")
        self.loop.stop_recording()

    def play_loop(self):        
        self.write_message("PLAY LOOP.");
        self.loop.is_playback = True
        player = LoopPlayer(self)
        player.daemon = True 
        player.start()
        
    def stop_loop(self):
        self.write_message("STOP LOOP.");
        self.loop.is_playback = False
        
    def clean_loop(self):
        self.write_message("CLEAN LOOP.")
        self.loop.clean()
        
    def toggle_loop(self):
        if time.clock() - self.last_toggle_loop < 0.5: # double tap/click
            self.clean_loop()
            self.start_loop_recording()
            return 
            
        self.last_toggle_loop = time.clock()
        
        if self.loop.is_playback:
            self.stop_loop()
        elif self.loop.is_recording:
            self.stop_loop_recording()
            self.play_loop()
        elif self.loop.is_clean:
            self.start_loop_recording()
        else:
            self.play_loop()
            
    def check_loop_toggle_message_signature(self, message):
        signature = self.loop_toggle_message_signature
        if len(message)<len(signature): return False
        
        for n in range(len(signature)):
            if message[n] != signature[n]: return False
            
        return True
        
    def capture_message(self, message, time_stamp, loopback=False):
        
        if self.check_loop_toggle_message_signature(message):
            self.toggle_loop()
            return
        
        self.last_event=time.clock()
        if len(self.messages_captured) == 0: time_stamp = 0
        message.append(time_stamp)
        self.messages_captured.append(message)
        if self.monitor: self.write_message(message)
        
        if not loopback and self.loop.is_recording: 
            self.handle_message_loop(message)
        
    def handle_message_loop(self, message):
        if self.loop.start_recording_time == None:
            if message[0]!=144: return # note on is the trigger
            self.loop.start_recording_time = self.last_event
        self.loop.messages_captured.append(message)
        
    def is_time_to_save(self):
        if (self.long_pause==None): return False # no autosave
        return time.clock()-self.last_event > self.long_pause
        
    def save_midi_file(self):
        if len(self.messages_captured)==0: return
        
        MyMIDI = MIDIFile(2)
        track = 0

        MyMIDI.addTrackName(track, 0, "Tempo track")
        MyMIDI.addTempo(track, 0, self.bpm)
        
        track += 1
        MyMIDI.addTrackName(track, 0, "Song track")
        
        total_time=0
        midi_messages_on=[]
        midi_messages_off=[]
        midi_messages_controller=[]
             
        for message in self.messages_captured:
            if len(message)!=4:
                self.write_message("wrong length: skipping " + str(message))
                continue

            total_time += float(message[3])
            total_time_adjusted = total_time * float(self.bpm) / float(60) # seconds -> beat conversion
            if message[0]==144: # note on
                midi_messages_on.append({'note': message[1], 'velocity': message[2], 'time': total_time_adjusted})
            elif message[0]==128: # note off
                midi_messages_off.append({'note': message[1], 'velocity': message[2], 'time': total_time_adjusted})
            elif message[0]==176: # pedal
                midi_messages_controller.append({'type': message[1], 'value': message[2], 'time': total_time_adjusted})
            else:
                self.write_message("unknown message: skipping " + str(message))
                continue
                
            
        for m_on in midi_messages_on:
            for m_off in midi_messages_off:
                if m_off['note']==m_on['note'] and m_off['time'] > m_on['time']:
                    m_on['duration'] = m_off['time'] - m_on['time']
                    m_off['note']=-1
                    break
            else:
                m_on['duration'] = float(15)* float(self.bpm) / float(60) # suspended

        channel = 0
        
        for m in midi_messages_on:
            MyMIDI.addNote(track,channel, m['note'], m['time'], m['duration'], m['velocity'])

        for m in midi_messages_controller:
            MyMIDI.addControllerEvent(track, channel, m['time'], m['type'], m['value'])
        
        file_name=self.midi_file_name.format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        self.write_message("Saving {0} MIDI messages to {1}...".format(len(self.messages_captured), file_name))
        binfile = open(file_name, 'wb')
        MyMIDI.writeFile(binfile)
        binfile.close()
        self.messages_captured=[]
        self.write_message("Saved.")      

    def start_main_loop(self):
        while (True):
            try:
                time.sleep(1)
                if (self.is_time_to_save()): 
                    self.save_midi_file()
            except IOError: 
                pass
                
     
            