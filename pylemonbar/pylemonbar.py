#!/usr/bin/env python3

import subprocess
import time
import sys
import select
import os
import math
import signal
import struct

from pylemonbar.core import *
from pylemonbar.hlwm import *
from pylemonbar.widgets import *
from pylemonbar.conky import ConkyWidget

def main(argv):
    # ---- configuration ---
    if len(argv) >= 2:
        monitor = int(argv[1])
    else:
        monitor = 0
    geometry = hc(['monitor_rect', str(monitor)]).split(' ')
    x = int(geometry[0])
    y = int(geometry[1])
    monitor_w = int(geometry[2])
    monitor_h = int(geometry[3])
    width = monitor_w
    height = 16
    hc(['pad', str(monitor), str(height)])

    bar = Lemonbar(geometry = (x,y,width,height))
    hc_idle = HLWMInput()

    # widgets
    #rofi = DropdownRofi(y+height,x,width)
    #
    #def session_menu(btn):
    #    rofi.spawn(['Switch User', 'Suspend', 'Logout'])
    #
    #session_button = Button('V')
    #session_button.callback = session_menu

    time_widget = DateTime()
    hlwm_windowtitle = HLWMWindowTitle(hc_idle)
    xkblayouts = [
        'us us -variant altgr-intl us'.split(' '),
        'de de de'.split(' '),
    ]
    setxkbmap = 'setxkbmap -option compose:menu -option ctrl:nocaps'
    setxkbmap += ' -option compose:ralt -option compose:rctrl'

    bar.widgets = [ RawLabel('%{l}'),
                HLWMTags(hc_idle, monitor),
                #Counter(),
                RawLabel('%{c}'),
                HLWMMonitorFocusLayout(hc_idle, monitor, hlwm_windowtitle, RawLabel('X')),
                RawLabel('%{r}'),
                ConkyWidget('${battery_percent} '),
                HLWMLayoutSwitcher(hc_idle, xkblayouts, command = setxkbmap.split(' ')),
                RawLabel(' '),
                time_widget,
    ]

    inputs = [ hc_idle,
               bar
             ]

    def nice_theme(widget):
        widget.pad_left  = '%{-o}%{B#303030} '
        widget.pad_right = ' %{-o}%{B-}'

    nice_theme(hlwm_windowtitle)
    nice_theme(time_widget)
    def request_shutdown(args):
        quit_main_loop()
    hc_idle.enhook('quit_panel', request_shutdown)
    main_loop(bar, inputs)

def quit_main_loop():
    main_loop.shutdown_requested = True

def main_loop(bar, inputs):
    for w in bar.widgets:
        inp = w.eventinput()
        if inp != None:
            inputs.append(inp)

    global_update = True
    main_loop.shutdown_requested = False
    def signal_quit(signal, frame):
        quit_main_loop()
    signal.signal(signal.SIGINT, signal_quit)
    signal.signal(signal.SIGTERM, signal_quit)

    # main loop
    while not main_loop.shutdown_requested and bar.is_running():
        now = time.clock_gettime(time.CLOCK_MONOTONIC)
        for w in bar.widgets:
            if w.maybe_timeout(now):
                global_update = True
        data_ready = []
        if global_update:
            text = ''
            for w in bar.widgets:
                text += w.render()
            text += '\n'
            data_ready = select.select(inputs,[],[], 0.00)[0]
            if not data_ready:
                #print("REDRAW: " + str(time.clock_gettime(time.CLOCK_MONOTONIC)))
                bar.write_flushed(text)
                global_update = False
            else:
                pass
                #print("more data already ready")
        if not data_ready:
            # wait for new data
            next_timeout = math.inf
            for w in bar.widgets:
                next_timeout = min(next_timeout, w.next_timeout())
            now = time.clock_gettime(time.CLOCK_MONOTONIC)
            next_timeout -= now
            next_timeout = max(next_timeout,0.1)
            #print("next timeout = " + str(next_timeout))
            if next_timeout != math.inf:
                data_ready = select.select(inputs,[],[], next_timeout)[0]
            else:
                data_ready = select.select(inputs,[],[], 18)[0]
            if main_loop.shutdown_requested:
                break
        if not data_ready:
            pass #print('timeout!')
        else:
            for x in data_ready:
                x.process()
                global_update = True
    bar.proc.kill()
    bar.proc.wait()

