import threading
import sys
import time
import signal
import threading
import functools
import tkinter

from  midi_notebook.midi_notebook_context import MidiNotebookContext

# CONFIGURATION
configuration = { 
    'long_pause': None, # save automatically a new file if there are not new events for N seconds (None  = no autosave)
    'midi_file_name': 'midi_notebook_{0}.mid', # {0} = datetime
    'bpm': 120, # beats per minute
    'monitor': False, # print input midi messages if True
    'loop_toggle_message_signature': [[176, 21, 127], [176, 22, 127], [176, 23, 127], [176, 24, 127],], # signatures for loop control special messages
}
# /CONFIGURATION  

class Application():
    
    def __init__(self, context):
        self.context = context
        context.write_message_function = self.write_txt
    
        self.update_lock = threading.Lock()
        self.update_messages = []
        
        self.build_gui()
        
        self.midi_message_loop()
        
    def build_gui(self):
        self.root = tkinter.Tk()
        self.root.title('Midi Notebook')
 
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0, minsize=120)
        self.root.rowconfigure(2, weight=0, minsize = 2)
        
        self.txt = tkinter.Text(self.root, height='20')
        self.txt.grid(row=0, column=0, columnspan=self.context.n_loops+1, sticky=tkinter.W+tkinter.E+tkinter.N+tkinter.S)
        
        self.loop_buttons = []
        self.loop_status_lbl = []
        for n in range(0, self.context.n_loops):
            loopN = functools.partial(self.loop, n)    
            
            btn = tkinter.Button(self.root, command=loopN, text='Loop '+str(n)+("\n- master -" if n==0 else "") )
            self.loop_buttons.append(btn)
            btn.config(font='bold')
            btn.grid(row=1, column=n, sticky=tkinter.W+tkinter.E+tkinter.N+tkinter.S )
            
            var = tkinter.StringVar()
            lbl = tkinter.Label(self.root, height='1', width=1, textvariable=var)
            self.loop_status_lbl.append(var)
            lbl.grid(row=2, column=n, sticky=tkinter.W+tkinter.E+tkinter.N+tkinter.S )
            
            self.root.columnconfigure(n, weight=1)
            
        n += 1
        self.save_button = tkinter.Button(self.root, command=self.save, text='Save')
        self.save_button.config(font='bold' )
        self.save_button.grid(row=1, column=n, sticky=tkinter.W+tkinter.E+tkinter.N+tkinter.S )
        self.root.columnconfigure(n, weight=1)

    def midi_message_loop(self):
    
        self.update_lock.acquire()
        while(len(self.update_messages)>0):
            msg = self.update_messages.pop(0)
            self.txt.insert(tkinter.INSERT, msg)
            self.txt.see(tkinter.END)
        self.update_lock.release()
        
        for n, l in enumerate(self.context.loops):
            self.loop_status_lbl[n].set(l.status)
        
        self.root.update()
        
        self.root.after(200, self.midi_message_loop)

    def save(self):
        self.context.save_midi_file()
        
    def loop(self, n):
        self.context.toggle_loop(n)
        
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
    context = MidiNotebookContext(configuration) # init
    app = Application(context)
    
    input_port = None
    for arg in sys.argv[1:]:
        if arg.startswith("-in"): context.input_port = int(arg[3:])
        if arg.startswith("-out"): context.output_port = int(arg[4:])
    
    recorder = Recorder(context)
    recorder.daemon = True 
    recorder.start()
    app.root.mainloop()

main()


