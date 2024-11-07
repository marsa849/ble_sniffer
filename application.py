from myUart import *
import os

filter_mac = mac_convert( ['ed476a985627', 'f0484214f832','c7cb89b6057b', 'f6ce537ff58b', 'cb2584dd4d8a', 'e25ea6899e78'] )

last_time = 0

def proces(pkt):
        local_time = time.localtime(pkt.time)
        local_time = time.strftime("%Y-%m-%d_%H:%M:%S", local_time)
        mac = ''.join([f'{x:02x}' for x in pkt.address])
        payload = ' '.join([f'{x:02x}' for x in pkt.payload[:]])
        with open(f'hexin/{mac}_{local_time[0:10]}.txt', 'a') as f:
            f.write(f'{local_time}, vol{pkt.payload[17]/255*6.6:.3f} ,data {payload}\n')
if __name__ == "__main__":
    uart = MyUart(port='/dev/ttyUSB0', baudrate= 1_000_000)
    #uart.set_filter(rssi=-80, mac=filter_mac)
    while True:
        pkt = uart.ble_packets.get()
        if pkt.address in filter_mac:
            dict_key = tuple(pkt.address)
            if dict_key not in pkt.device_record_st or pkt.time - pkt.device_record_st[dict_key] >= 10:
                pkt.device_record_st[dict_key] = time.time()
                process(pkt)
