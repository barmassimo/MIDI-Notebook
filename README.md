MIDI-Notebook
=============
A prototypal MIDI monitor, looper, and recorder written in Python.
Inspired by Boomerang Looper pedals for guitarist - except that you don't need a MIDI pedal.

All you need is a MIDI keyboard for entering notes, and you can activate the loops via MIDI with a programmable CC message (sent by the keyboard itself or by another MIDI controller) or by mouse-clicking the buttons.

Tested mainly on Windows 7 64 bit. 

It seems that some dependencies aren't available via PIP - sorry about that, you need to install them manually.

If you have trouble, please contact me, an all-in-one executable version is available on request.

![screenshot](http://www.massimobarbieri.it/DjangoLab/ss_midi_notebook001.png)

## License
GNU GENERAL PUBLIC LICENSE V 3

## Current environment
* Python 3.x
* [rtmidi-python 0.2.2](https://pypi.python.org/pypi/rtmidi-python)
* [MIDIUtil 0.89](http://code.google.com/p/midiutil)

## Todo
* MIDI clock support
* Better GUI with another toolkit

## About me
[massimobarbieri.it](http://www.massimobarbieri.it)

