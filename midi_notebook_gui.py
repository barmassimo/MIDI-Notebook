import threading
import sys
import time
import signal
import threading
import tkinter
from tkinter import ttk
from  midi_notebook.midi_notebook_context import MidiNotebookContext

# CONFIGURATION
configuration = { 
    'long_pause': None, # save automatically a new file if there are not new events for N seconds (None  = no autosave)
    'midi_file_name': 'midi_notebook_{0}.mid', # {0} = datetime
    'bpm': 120, # beats per minute
    'monitor': True, # print input midi messages
    'loop_toggle_message_signature': [176, 21, 127],
}
# /CONFIGURATION  

class Application():
    
    def __init__(self):
        self.update_lock = threading.Lock()
        self.update_messages = []
        
        self.root = tkinter.Tk()
        self.root.title('Midi Notebook')
        
        self.txt = tkinter.Text(self.root, height='20')
        self.txt.pack(fill=tkinter.BOTH)
        
        #
        #f = ttk.Frame(self.root).pack(expand=True, fill=tkinter.BOTH)
        
        #self.save2_button = ttk.Button(f, command=self.save, text='Save2').pack(anchor=tkinter.W)
        #self.save3_button = ttk.Button(f, command=self.save, text='Save3').pack(anchor=tkinter.E)
        #ttk.Button(self.root, command=self.insert_txt, text='Click Me').place(x=10, y=10)
        
        self.loop_button = ttk.Button(self.root, command=self.loop, text='Loop 1').pack(anchor=tkinter.W)
        #self.loop_button.size(height=100, width=100)
   
        self.save_button = ttk.Button(self.root, command=self.save, text='Save').pack(anchor=tkinter.W)
        
        
        ##
        f=ttk.Frame(self.root, height=30)#.pack()
        print ("002")
        f.grid(row=0)
        print ("003")
        b1 = ttk.Button(f, text="Button1").grid(row=0, column=0)
        print ("004")
        b2 = ttk.Button(f, text="Button2").grid(row=0, column=1)
        b3 = ttk.Button(f, text="Button3").grid(row=0, column=2)

        # use grid layout manager
        #   b1.grid(row=0, column=0, sticky='w')
        #b2.grid(row=1, column=0, columnspan=3)
        #b3.grid(row=2, column=0, rowspan=3, sticky='w')
        ##
        
        self.context = None
        self.midi_message_loop()
        
    def midi_message_loop(self):
        self.update_lock.acquire()
        while(len(self.update_messages)>0):
            msg = self.update_messages.pop(0)
            self.txt.insert(tkinter.INSERT, msg)
            self.txt.see(tkinter.END)
            self.root.update()
        self.update_lock.release()
        self.root.after(200, self.midi_message_loop)

    def save(self):
        self.context.save_midi_file()
        
    def loop(self):
        self.context.toggle_loop()
        
    def write_txt(self, txt):
        self.update_lock.acquire()
        self.update_messages.append(str(txt)+'\n')
        self.update_lock.release()
       
        
class Recorder(threading.Thread):
    def __init__(self, context):
        super().__init__()
        self.context = context
        
    def run(self):
        self.context.print_info()
        self.context.start_recording()
        self.context.start_main_loop()

def main():
    app = Application()
    
    configuration['write_message_function'] = app.write_txt
    context = MidiNotebookContext(configuration) # init
    
    app.context = context
    
    input_port = None
    for arg in sys.argv[1:]:
        if arg.startswith("-in"): context.input_port = int(arg[3:])
        if arg.startswith("-out"): context.output_port = int(arg[4:])
    
    recorder = Recorder(context)
    recorder.daemon = True 
    recorder.start()
    app.root.mainloop()

main()


