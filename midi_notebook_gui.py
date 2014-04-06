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
    'long_pause': 30, # save automatically a new file if there are not new events for 30 seconds
    'midi_file_name': 'midi_notebook_{0}.mid', # {0} = datetime
    'bpm': 120, # beats per minute
    'monitor': True, # print input midi messages
}
# /CONFIGURATION  

class Application():
    
    def __init__(self):
        self.update_lock = threading.Lock()
        self.update_messages = []
        
        self.root = tkinter.Tk()
        self.root.title('Midi Notebook')
        #ttk.Frame(self.root, width=500, height=3).pack()
        
        #ttk.Button(self.root, command=self.insert_txt, text='Click Me').place(x=10, y=10)
        self.txt = tkinter.Text(self.root, height='20')
        self.txt.pack(fill=tkinter.BOTH)
        self.save_button = ttk.Button(self.root, command=self.save, text='Save').pack(anchor=tkinter.W)
        self.my_app_loop()
    
    def my_app_loop(self):
        self.update_lock.acquire()
        while(len(self.update_messages)>0):
            msg = self.update_messages.pop(0)
            self.txt.insert(tkinter.INSERT, msg)
            self.txt.see(tkinter.END)
            self.root.update()
        self.update_lock.release()
        self.root.after(100,self.my_app_loop)

        
    def save(self):
        MidiNotebookContext().save_midi_file()
        
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
    
    input_port = None
    for arg in sys.argv[1:]:
        if arg.startswith("-in"): input_port = int(arg[3:])
    
    context.input_port = input_port
    
    recorder = Recorder(context)
    recorder.daemon = True 
    recorder.start()
    app.root.mainloop()
    


main()


