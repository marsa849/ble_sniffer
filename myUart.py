import serial
import time
from threading import Thread

from myType import *
import queue

class MyUart:
    def __init__(self, port=None, baudrate=None):
        self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                rtscts=True,
                exclusive=True
            )
        self.recv_bytes = bytearray()
        self.recv_buffer = []
        self.recv_state = RECV_IDLE

        self.worker_thread = Thread(target=self._read_worker)
        self.reading = True
        self.worker_thread.setDaemon(True)
        self.worker_thread.start()
        self.ble_packets = queue.Queue()

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
                        self.recv_buffer.append(SLIP_START)
                    elif serialByte == SLIP_ESC_END:
                        self.recv_buffer.append(SLIP_END)
                    elif serialByte == SLIP_ESC_ESC:
                        self.recv_buffer.append(SLIP_ESC)
                    else:
                        self.recv_buffer.append(SLIP_END)
                else:
                    self.recv_buffer.append(serialByte)
            else:
                    serialByte = self.getSerialByte()
                    if serialByte is None:
                        self.recv_state = RECV_ESC
                        return self.recv_state
                    self.recv_state = RECV_START
                    if serialByte == SLIP_ESC_START:
                        self.recv_buffer.append(SLIP_START)
                    elif serialByte == SLIP_ESC_END:
                        self.recv_buffer.append(SLIP_END)
                    elif serialByte == SLIP_ESC_ESC:
                        self.recv_buffer.append(SLIP_ESC)
                    else:
                        self.recv_buffer.append(SLIP_END)
        return self.recv_buffer
    
    def set_filter(self, rssi=None, mac=None):
        if rssi is not None:
            self.filter_rssi = rssi
        if mac is not None:
            self.filter_mac = mac

    def _packet_filter(self,packet):
        if packet[0]+6 != len(packet):
            return None
        if packet[5] != 0x02:
            return None
        if hasattr(self, 'filter_rssi') and  0-self.filter_rssi < packet[9]:
            return None
        if hasattr(self, 'filter_mac') and self.filter_mac != packet[23:29]:
            return None
        self.ble_packets.put((time.time(),packet))

    def _read_worker(self):
        self.ser.reset_input_buffer()
        
        while True:
            self.recv_bytes.extend( self.ser.read(self.ser.in_waiting or 1) )
            while True:
                packet = self.decodeFromSLIP()
                if type(packet) == list:
                    self._packet_filter(packet)
                    self.recv_buffer = []
                else:
                    break

if __name__ == "__main__":
    uart = MyUart(port='COM10', baudrate= 1_000_000)
    uart.set_filter(rssi=-80,mac=[0x03,0x58,0x20,0xc6,0x7b,0x90])
    #uart.ser.set_buffer_size(rx_size=100000,tx_size=10000)
    target = 1
    if target == 1:
        while True:
            recv_time,pkt = uart.ble_packets.get()

            hex_list = [f'{x:02x}' for x in pkt]
            hex_string = ' '.join(hex_list)
            print(f' recv data{hex_string}, bytes in recv_buff{uart.ser.in_waiting}  time {recv_time}')
            print()