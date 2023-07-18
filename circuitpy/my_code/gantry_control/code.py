# add estop for the gantry, or have estop stop the gantry too

from busio import UART
from canio import Message
from farm_ng.utils.cobid import CanOpenObject
from farm_ng.utils.general import TickRepeater
from farm_ng.utils.main_loop import MainLoop
from gantry import GANTRY_ID
from gantry import GantryControlState
from gantry import GantryTpdo1
from gantry import GantryRpdo1
from gantry import make_gantry_rpdo1_proto
import board
# from gantry import parse_gantry_tpdo1_proto
from usb_cdc import console


class GantryControlApp:
    def __init__(self, main_loop: MainLoop, can, node_id) -> None:
        self.can = can
        self.node_id = node_id
        self.main_loop = main_loop
        self.main_loop.show_debug = True
        self.cmd_repeater = TickRepeater(ticks_period_ms=50)

        self.cmd_feed = 1000
        self.cmd_x = 0
        self.cmd_y = 0
        self.relative = True
        self.jog = True
        self.request_state = GantryControlState.STATE_AUTO_READY

        uart = UART(board.TX, board.RX, baudrate = 115200)
        
        self._register_message_handlers()

    def _register_message_handlers(self):
        self.main_loop.command_handlers[CanOpenObject.TPDO1 | GANTRY_ID] = self._handle_gantry_tpdo1

    def _handle_gantry_tpdo1(self, message):
        self.gantry_tpdo1 = GantryTpdo1.from_can_data(message.data)
        if self.gantry_tpdo1.state != GantryControlState.STATE_AUTO_ACTIVE:
            self.cmd_feed = 0
            self.cmd_x = 0
            self.cmd_y = 0
            self.request_state = GantryControlState.STATE_AUTO_READY
        print(self.gantry_tpdo1, end="\r")

    #/// change this. takes char, turns into self.inc
    #/// you'll take in purple center and turn into g-code
    def parse_gantry_response(self, str):
        if str.find("ALARM") == -1:
            pass
        else:
            # find out what error it is, display to the monitor, 
            # pause the program, ask to home the gantry
            pass
        

    # serial reading from computer, maybe reading in any alarm codes
    # if alarm, deal with it. If not, pass.
    def serial_read(self):
        while console.in_waiting > 0:
            self.parse_gantry_response((console.readline().decode()))

    def send_cmd(self):
        if self.request_state is GantryControlState.STATE_AUTO_ACTIVE or GantryControlState.STATE_AUTO_READY:
            if self.jog:
                uart.write("$J=G91 G21 X" + 
                        str(self.cmd_x) + 
                        " Y" + str(self.cmd_y) + 
                        " F" + str(self.cmd_feed) + 
                        "\n")
            else: # uncomment if you plan on ever using G01
                pass
                # uart.write("G01 G21 G17 G9" + 
                #            self.relative + 
                #            "X" + str(self.cmd_x) + 
                #            " Y" + str(self.cmd_y) + 
                #            " F" + str(self.cmd_feed) + 
                #            "\n")
    
        
    def iter(self):
        # instead of serial read here will be sending gantry commands and reading in any errors
        self.serial_read()
        self.send_cmd

        if self.cmd_repeater.check():
            self.can.send(
                Message(
                    id=CanOpenObject.RPDO1 | GANTRY_ID,
                    data=GantryRpdo1(
                        state_req=self.request_state, 
                        cmd_feed=self.cmd_feed, 
                        cmd_x=self.cmd_x, 
                        cmd_y = self.cmd_y, 
                        relative = self.relative, 
                        jog = self.jog
                    ).encode(),
                )
            )


def main():
    MainLoop(AppClass=GantryControlApp, has_display=False).loop()


main()
