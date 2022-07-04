from gettext import ngettext
import mido
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import colorConverter
import matplotlib.patches as mpatches
import os

from time import sleep


# inherit the origin mido class
class MidiVisualizer(mido.MidiFile):

    def __init__(self):
        #self.sr = 10
        self.meta = {}
        self.msgCounter = 0
        self.totalTimeSeconds = 0
        self.stepSize = 0

    def loadFile(self, filename):
        self.filename = filename
        self.events, trackCount = self.get_events(filename)
        self.draw_midiImage()
        self.draw_Lines()
        return trackCount
        

    def initFigure(self):
        px = 1/plt.rcParams['figure.dpi']  # pixel to inches
        self.xLength = 620*px # size of the diagram in x
        self.fig = plt.figure(figsize=(self.xLength, 320*px), tight_layout=True) 
        self.fig.tight_layout()
        self.fig.patch.set_facecolor('none')
        return self.fig

    def getSizeInPixels(self):
        inch = plt.rcParams['figure.dpi']  # inches to pixel
        return [int(self.xLength *inch), 320]

    def getMessageCount(self):
        return self.msgCounter

    def get_events(self, file):
        mid = mido.MidiFile(file)
        self.ticks_per_beat = mid.ticks_per_beat
        # There is > 16 channel in midi.tracks. However there is only 16 channel related to "music" events.
        # We store music events of 16 channel in the list "events" with form [[ch1],[ch2]....[ch16]]
        # Lyrics and meta data used a extra channel which is not include in "events"

        events = [[] for x in range(16)]

        # Iterate all event in the midi and extract to 16 channel form
        for track in mid.tracks:
            for msg in track:
                try:
                    channel = msg.channel
                    events[channel].append(msg)
                except AttributeError:
                    try:
                        if type(msg) != type(mido.UnknownMetaMessage):
                            self.meta[msg.type] = msg.dict()
                        else:
                            pass
                    except:
                        print("error",type(msg))

        return events, len(mid.tracks)

    def getMidiInformation(self):
        # Identify events, then translate to piano midiInformation

        #count total number of msgs (only note_on, note_off)
        self.msgCounter = 0

        # compute total length in tick unit
        length = self.get_total_ticks()

        # allocate memory to numpy array
        midiInformation = np.zeros((16, 128, length), dtype="int8")

        # use a register array to save the state(no/off) for each key
        note_register = [int(-1) for x in range(128)]

        # use a register array to save the state(program_change) for each channel
        timbre_register = [1 for x in range(16)]


        for idx, channel in enumerate(self.events):

            time_counter = 0
            volume = 100

            for msg in channel:
                if msg.type == "control_change":
                    if msg.control == 7:
                        volume = msg.value
                    if msg.control == 11:
                        volume = volume * msg.value // 127

                if msg.type == "program_change":
                    timbre_register[idx] = msg.program

                if msg.type == "note_on":
                    self.msgCounter += 1
                    note_on_start_time = time_counter
                    note_on_end_time = (time_counter + msg.time)
                    intensity = volume * msg.velocity // 127
					# When a note_on event *ends* the note start to be play 
					# Record end time of note_on event if there is no value in register
					# When note_off event happens, we fill in the color
                    if note_register[msg.note] == -1:
                        note_register[msg.note] = (note_on_end_time,intensity)
                    else:
					# When note_on event happens again, we also fill in the color
                        old_end_time = note_register[msg.note][0]
                        old_intensity = note_register[msg.note][1]
                        midiInformation[idx, msg.note, old_end_time: note_on_end_time] = old_intensity
                        note_register[msg.note] = (note_on_end_time,intensity)

                if msg.type == "note_off":
                    # otherwise crashing if note_off is send before note_on
                    if note_register[msg.note] != -1:
                        note_off_start_time = time_counter
                        note_off_end_time = (time_counter + msg.time)
                        note_on_end_time = note_register[msg.note][0]
                        intensity = note_register[msg.note][1]
					    # fill in color
                        midiInformation[idx, msg.note, note_on_end_time:note_off_end_time] = intensity

                        note_register[msg.note] = -1  # reinitialize register

                time_counter += msg.time

            # if there is a note not closed at the end of a channel, close it
            for key, data in enumerate(note_register):
                if data != -1:
                    note_on_end_time = data[0]
                    intensity = data[1]
                    # print(key, note_on_end_time)
                    note_off_start_time = time_counter
                    midiInformation[idx, key, note_on_end_time:] = intensity
                note_register[idx] = -1

        return midiInformation

    def draw_midiImage(self):
        visualizationFile =  "data/previews/" + os.path.basename(self.filename)[:-4] + ".png"
        midiInformation = self.getMidiInformation() #get data from midi file
        plt.clf()
        plt.subplots_adjust(left=0.045, right=1, top=1, bottom=0.09) #shift plot to corner
        # add a new subplot
        a1 = self.fig.add_subplot(111)      
        # remove backgroud for current plot
        a1.set_facecolor('none')            
        #reading total ticks of track
        totalTicks = self.get_total_ticks()
        # calculate total track duration
        self.totalTimeSeconds = mido.tick2second(totalTicks, self.ticks_per_beat, self.get_tempo()) 
        # set interval to 5000 ticks
        x_label_interval = 5000
        # calculate period of description
        x_label_period_sec = mido.tick2second(x_label_interval, self.ticks_per_beat, self.get_tempo())
        # increment number of total ticks until a full intervall is reached
        while(totalTicks % 5000 != 0):
            totalTicks += 1
        px = 1/plt.rcParams['figure.dpi']  # pixel to inches TODO rename and move to top
        # increase diagramm if track is longer than 8 seconds otherwise set size to 800 pixels
        if self.totalTimeSeconds > 8:
            x = self.totalTimeSeconds - 8
            self.xLength = 620*px + (int)(np.ceil(x))*25*px
            # set the new figure size
            self.fig.set_size_inches(self.xLength, 320*px, forward=True)
        # calculate the description unit steps
        countSteps = len(list(range(0,totalTicks,(int)(np.ceil(x_label_interval)))))
        # add the desciption to the plot
        plt.xticks(list(range(0,totalTicks,(int)(np.ceil(x_label_interval)))), [round(x * x_label_period_sec, 2) for x in range(countSteps)])
        
        # dynamic scale of the y axes depending on used channels
        maxTone = 0
        minTone = 120
        for channel in midiInformation:
            #find minimum tone occured over all channels
            for idx, tone in enumerate(channel):
                if np.any(tone) and minTone > idx -1:
                    minTone = idx - 1
                    break
                
            #find maximum tone occured over all channels
            reversed_channel = channel[::-1]
            for idx, tone in enumerate(reversed_channel):
                if np.any(tone) and maxTone < 128 - idx -1:
                    maxTone = 128 - idx -1
                    break
            
        # round up to full octave
        while minTone % 8 != 0 and minTone > 0:
            minTone -= 1
        while maxTone % 8 != 0 and maxTone < 128:
            maxTone += 1
        # add the scaled y-axes desciption to the plot
        ax = plt.gca()
        ax.set_ylim([minTone, maxTone])

        # check if current file is already generated, skip repeated work
        if os.path.exists(visualizationFile): #skip plot generation if file already exists
            print("File already exists, skipping gneration")
            return plt.xticks(), plt.yticks()

        # build colors for differnt channels
        channel_nb = 16
        transparent = colorConverter.to_rgba('black')
        colors = [mpl.colors.to_rgba(mpl.colors.hsv_to_rgb((i / channel_nb, 1, 1)), alpha=1) for i in range(channel_nb)]
        cmaps = [mpl.colors.LinearSegmentedColormap.from_list('my_cmap', [transparent, colors[i]], 128) for i in range(channel_nb)]
        # build color maps
        for i in range(channel_nb):
            cmaps[i]._init()
            # create your alpha array and fill the colormap with them.
            alphas = np.linspace(0, 1, cmaps[i].N + 3)
            # create the _lut array, with rgba values
            cmaps[i]._lut[:, -1] = alphas

        # draw midiInformation and stack image on a1
        for i in range(channel_nb):
            try:
                a1.imshow(midiInformation[i], origin="lower", interpolation='nearest', cmap=cmaps[i], aspect='auto')
            except IndexError:
                pass
        # show midiInformation and save figure 
        # !!! don't write any code between the next two lines !!!
        plt.draw()
        plt.savefig(visualizationFile,bbox_inches='tight')

    def draw_Lines(self):
        plt.clf()
        #plt.subplots_adjust(left=0.0, right=1, top=0.995, bottom=0.0)
        # load generated file and set it as background
        visualizationFile = "data/previews/" + os.path.basename(self.filename)[:-4] +".png"
        img = plt.imread(visualizationFile)
        a2 = self.fig.add_subplot(111)
        #a2.set_axis_off()
        a2.set_anchor('W')
        a2.set_facecolor('none')    
        a2.imshow(img)
        a2.set_axis_off()
        # Turn off tick labels
        self.fig.add_axes(a2)
        plt.draw()

    def get_tempo(self):
        try:
            return self.meta["set_tempo"]["tempo"]
        except:
            return 500000

    def get_total_ticks(self):
        max_ticks = 0
        for channel in range(16):
            ticks = sum(msg.time for msg in self.events[channel])
            if ticks > max_ticks:
                max_ticks = ticks
        return max_ticks

    def clearAll(self):
        plt.clf()
        