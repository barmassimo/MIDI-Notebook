MIDI-Notebook
=============
A prototypal MIDI monitor, looper, and recorder written in Python.
Inspired by Boomerang Looper pedals for guitarists - except that you don't need a MIDI pedal.

All you need is a MIDI keyboard for entering notes, and you can activate the loops via MIDI with a programmable CC message (sent by the keyboard itself or by another MIDI controller) or by mouse-clicking the buttons.

Tested mainly on Windows 7 64 bit. 

It seems that some dependencies aren't available via PIP - sorry about that, you need to install them manually.

If you have trouble, please contact me, an all-in-one executable version is available on request.

![screenshot](http://www.massimobarbieri.it/DjangoLab/ss_midi_notebook001.png)

## Usage
1. Select a MIDI out via menu
2. Click (or activate via MIDI CC) the first "Loop 0 master" button
3. Start playing with your keyboard - the recording begins when you press the first note
4. Click the first button again to stop recording and start playing the loop
5. Click on another loop button to start recording on a slave loop, click again when finished
6. At any moment, mute and restart a loop by clicking the corresponding button (slave loops 1, 2 and 3 are kept in sync with loop 0)
7. Export your performance to a MIDI file via menu or CTRL+S

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

