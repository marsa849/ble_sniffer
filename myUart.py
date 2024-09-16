import serial
import time
from threading import Thread

from myType import *

class MyUart:
    def __init__(self, port=None, baudrate=None):
        self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                rtscts=True,
                exclusive=True
            )
        self.recv_bytes = bytearray()
        self.recv_packet = []
        self.recv_state = RECV_IDLE

        self.worker_thread = Thread(target=self._read_worker)
        self.reading = True
        self.worker_thread.setDaemon(True)
        self.worker_thread.start()

    def getSerialByte(self):
        if len(self.recv_bytes) > 0:
            return self.recv_bytes.pop(0)
        else:
            return None
        
    def decodeFromSLIP(self):

        if self.recv_state == RECV_IDLE:
            while True:
                res = self.getSerialByte()
                if res is None:
                    return self.recv_state
                if res == SLIP_START:
                    self.recv_state = RECV_START
                    break

        while True:
            if self.recv_state != RECV_ESC:
                serialByte = self.getSerialByte()
                if serialByte is None:
                    return self.recv_state
                if serialByte == SLIP_END:
                    self.recv_state = RECV_IDLE
                    break
                elif serialByte == SLIP_ESC:
                    serialByte = self.getSerialByte()
                    if serialByte is None:
                        self.recv_state = RECV_ESC
                        return self.recv_state
                    if serialByte == SLIP_ESC_START:
                        self.recv_packet.append(SLIP_START)
                    elif serialByte == SLIP_ESC_END:
                        self.recv_packet.append(SLIP_END)
                    elif serialByte == SLIP_ESC_ESC:
                        self.recv_packet.append(SLIP_ESC)
                    else:
                        self.recv_packet.append(SLIP_END)
                else:
                    self.recv_packet.append(serialByte)
            else:
                    serialByte = self.getSerialByte()
                    if serialByte is None:
                        self.recv_state = RECV_ESC
                        return self.recv_state
                    self.recv_state = RECV_START
                    if serialByte == SLIP_ESC_START:
                        self.recv_packet.append(SLIP_START)
                    elif serialByte == SLIP_ESC_END:
                        self.recv_packet.append(SLIP_END)
                    elif serialByte == SLIP_ESC_ESC:
                        self.recv_packet.append(SLIP_ESC)
                    else:
                        self.recv_packet.append(SLIP_END)
        return self.recv_packet
    
    def _read_worker(self):
        self.ser.reset_input_buffer()
        
        while True:
            self.recv_bytes.extend( self.ser.read(self.ser.in_waiting or 1) )
            while True:
                self.pkt = self.decodeFromSLIP()
                if type(self.pkt) != int:
                    if set([0x90, 0x7b, 0xc6, 0x20, 0x58, 0x03]).issubset(set(self.pkt)):
                        hex_list = [f'{x:02x}' for x in self.pkt]
                        hex_string = ' '.join(hex_list)
                        print(f'time {time.time()}, recv data{hex_string}, bytes in recv_buff{self.ser.in_waiting}')
                        print()
                    self.recv_packet = []
                else:
                    #print(self.pkt)
                    break

if __name__ == "__main__":
    uart = MyUart(port='COM10', baudrate= 1_000_000)
    #uart.ser.set_buffer_size(rx_size=100000,tx_size=10000)
    target = 1
    if target == 1:
        while True:
            print(f'serial data len {uart.ser.in_waiting}')
            time.sleep(1)
