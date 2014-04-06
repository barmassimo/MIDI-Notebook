import time
import datetime
import os
import sys

import rtmidi_python as rtmidi
from midiutil.MidiFile3 import MIDIFile

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
        
        time.clock()
        self.last_event = time.clock()
        self.messages_captured = []
        self.midi_in_ports = []
        
    def write_message(self, message):
        if (not self.write_message_function is None):
            self.write_message_function(message)
            
    def print_info(self, input_port):
        self.write_message("MIDI IN PORTS:")
        for n, port_name in enumerate(self.get_input_ports()):
            selected = ""
            if n==input_port: selected = " [SELECTED] "
            self.write_message("({0}) {1}{2}".format(n, port_name, selected))    
            
        self.write_message("")

        if input_port is None:
            self.write_message("Usage: {0} [-inPORT]".format(os.path.basename(sys.argv[0])))
            self.write_message("Recording from ALL midi ports.")
            self.write_message("If you want to record from only one port, you can provide a PORT number.")   
        
    def get_input_ports(self):
        midi_in = rtmidi.MidiIn()
        ports = midi_in.ports
        return ports
        
    def start_recording(self, input_port):
        if not input_port is None:
            self._start_recording_from_port(input_port)
        else:
            for n in range(len(self.get_input_ports())):
                self._start_recording_from_port(n)
        
    def _start_recording_from_port(self, input_port):
        midi_in=rtmidi.MidiIn()
        midi_in.callback = self.capture_message
        midi_in.open_port(input_port)
        self.midi_in_ports.append(midi_in)
        
    def capture_message(self, message, time_stamp):
        self.last_event=time.clock()
        if len(self.messages_captured) == 0: time_stamp = 0
        message.append(time_stamp)
        self.messages_captured.append(message)
        if self.monitor: self.write_message(message)
        
    def is_time_to_save(self):
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
                
     
            