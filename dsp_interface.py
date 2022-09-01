import usb
import usb.core
import usb.util
import libusb_package
from FrequencyHandler import FrequencyHandler
from enum import Enum

class DSPCommands(Enum):
    StartTone = 1
    StopTone = 2
    Reset = 3
    SetVolume = 4

class DSPInterface:
    def __init__(self, numberOfChannels) -> None:
        self.currentTones = [0] * numberOfChannels
        self.freqHandler = FrequencyHandler("data/freq.txt")
        self.initUsb()
        self.resetDSP()
        
    def initUsb(self):
        be = libusb_package.get_libusb1_backend()

        for dev in libusb_package.find(find_all=True):
            pass
            
        # find our device
        self.dev = usb.core.find(idVendor=0x0c55, idProduct=0x1234)

        # was it found?
        if self.dev is None:
            raise ValueError('Device not found')

        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        self.dev.set_configuration()

        # get an endpoint instance
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0,0)]

        self.ep = usb.util.find_descriptor(
            intf,
            # match the first OUT endpoint
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_OUT)

    def startTone(self, tone, gain, channel):
        frequency = self.freqHandler.getFrequency(tone)
        data = channel + (frequency << 16) + (int(gain) << 32)
        self.sendCommand(DSPCommands.StartTone, data, 6)
        
    def stopTone(self, channel):
        data = channel
        self.sendCommand(DSPCommands.StopTone, data, 2)
        
    def setVolume(self, volume):
        data = volume
        self.sendCommand(DSPCommands.SetVolume, data, 2)

    def resetDSP(self):
        self.sendCommand(DSPCommands.Reset, 0, 0)

    def sendCommand(self, command, data, dataLength):
        out = command.value + (data << 16)
        self.ep.write(out.to_bytes(dataLength + 2,'little'))

class ChannelHandler:
    def __init__(self) -> None:
        self.maxChNmbr = 16
        self.volume = int(1023/16)
        #self.volume = 1
        self.tones = {} # format: tone:channel
        
        self.dspInterface = DSPInterface(self.maxChNmbr)


    def getKey(self, tone, channel):
        return str(tone) + "_" + str(channel)

    def startTone(self, tone, velocity, midiChannel):
        #select channel to use for tone
        for index in range(self.maxChNmbr):
            if index not in self.tones.values():

                if tone not in self.tones.keys():
                    # Channel free and tone not already played
                    key = self.getKey(tone, midiChannel)
                    self.tones[key] = index
                    break

                else:
                    # tone already played
                    print("Tone already active")
                    return
        else:
            # all channels are busy
            print("All channels busy")
            return

        channel = index
        
        # send start Tone on channel index
        gain = self.volume * velocity / 127
        self.dspInterface.startTone(tone, gain, channel)

    def stopTone(self, tone, midiChannel):
        key = self.getKey(tone, midiChannel)
        if key in self.tones.keys():
            channel = self.tones.pop(key)

            #send stop Tone
            self.dspInterface.stopTone(channel)
        
        
    def setVolume(self, volume):
        self.dspInterface.setVolume(volume)
