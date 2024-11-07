import serial
import time
from threading import Thread

from myType import *
import queue

def mac_convert(str_list):
    mac_list = []
    for i in str_list:
        mac = []
        for j in range(6):
            mac.append(eval('0x'+i[2*(5-j):2*(5-j)+2]))
        mac_list.append(mac)
    return mac_list

class blePkt:
    device_record_st = {}
    def __init__(self, data_list):
        self.time = time.time()
        self.address = data_list[23:29]
        self.channel = data_list[8]
        self.rssi = 0 - data_list[9]
        self.payload = data_list[20:]


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
        if hasattr(self, 'filter_mac') and packet[23:29] not in self.filter_mac:
            return None
        if packet[7] & 0x01 == 0:#CRC ERROR
            return None
        self.ble_packets.put(blePkt(packet))

    def _read_worker(self):
        self.ser.reset_input_buffer()
        
        while True:
            data = self.ser.read(self.ser.in_waiting or 1)
            if(len(data) > 4000):
                raise Exception('uart buffer overflow')
            self.recv_bytes.extend(data)
            while True:
                packet = self.decodeFromSLIP()
                if type(packet) == list:
                    self._packet_filter(packet)
                    self.recv_buffer = []
                else:
                    break

if __name__ == "__main__":
    uart = MyUart(port='/dev/ttyUSB0', baudrate= 1_000_000)
    uart.set_filter(rssi=-80, mac=[0xc6, 0x05, 0x04, 0x79, 0x27, 0xcd])
    #uart.ser.set_buffer_size(rx_size=100000,tx_size=10000)
    target = 1
    if target == 1:
        last_time = 0
        while True:
            recv_time,pkt = uart.ble_packets.get()
            if recv_time - last_time >= 1:
                last_time = recv_time
                hex_list = [f'{x:02x}' for x in pkt[23:]]
                hex_string = ' '.join(hex_list)
                local_time = time.localtime(recv_time)
                local_time = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
                with open('log.txt', 'a') as f:
                    f.write(f'{local_time}, date {hex_string}\n')
