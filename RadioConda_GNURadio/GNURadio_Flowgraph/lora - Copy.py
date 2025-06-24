#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: LoRa_Decoder
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio import gr
from gnuradio import blocks
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import gnuradio.lora_sdr as lora_sdr
import osmosdr
import time
import threading
import pmt

# Create a custom message sink block to print packet info
class lora_packet_sink(gr.sync_block):
    def __init__(self):
        gr.sync_block.__init__(
            self,
            name="LoRa Packet Sink",
            in_sig=None,
            out_sig=None
        )
        self.message_port_register_in(pmt.intern("packets"))
        self.set_msg_handler(pmt.intern("packets"), self.handle_packet)
    
    def safe_print(self, obj):
        """Safely print potentially binary data"""
        if isinstance(obj, bytes):
            return f"<binary data: {obj.hex()}>"
        try:
            return str(obj)
        except UnicodeDecodeError:
            return f"<unprintable data>"
    
    def handle_packet(self, msg):
        print("\n----- PACKET RECEIVED -----")
        
        # Print raw message type for debugging
        print(f"Message type: {type(msg)}")
        print(f"Is pair: {pmt.is_pair(msg)}")
        
        # Extract payload from message
        if pmt.is_pair(msg):
            metadata = pmt.car(msg)
            payload = pmt.cdr(msg)
            
            print(f"Metadata type: {type(metadata)}")
            print(f"Is metadata dict: {pmt.is_dict(metadata)}")
            
            # If metadata is a dictionary, try to get RSSI and SNR
            if pmt.is_dict(metadata):
                print("Metadata keys:")
                keys = pmt.dict_keys(metadata)
                for i in range(pmt.length(keys)):
                    key = pmt.nth(i, keys)
                    try:
                        key_str = pmt.symbol_to_string(key)
                        print(f"  - {key_str}")
                    except Exception as e:
                        print(f"  - <unprintable key>: {str(e)}")
                
                # Try to get RSSI
                if pmt.dict_has_key(metadata, pmt.intern("rssi")):
                    try:
                        rssi = pmt.to_float(pmt.dict_ref(metadata, pmt.intern("rssi"), pmt.PMT_NIL))
                        print(f"RSSI: {rssi:.2f} dBm")
                    except Exception as e:
                        print(f"Error getting RSSI: {str(e)}")
                else:
                    print("No RSSI field found")
                
                # Try to get SNR
                if pmt.dict_has_key(metadata, pmt.intern("snr")):
                    try:
                        snr = pmt.to_float(pmt.dict_ref(metadata, pmt.intern("snr"), pmt.PMT_NIL))
                        print(f"SNR: {snr:.2f} dB")
                    except Exception as e:
                        print(f"Error getting SNR: {str(e)}")
                else:
                    print("No SNR field found")
            
            # If not a dict, try alternative approaches
            else:
                print("Metadata is not a dictionary")
                print(f"Metadata: {self.safe_print(metadata)}")
                
                # Try to parse as a string if possible
                try:
                    if pmt.is_symbol(metadata):
                        print(f"Metadata symbol: {pmt.symbol_to_string(metadata)}")
                    elif pmt.is_number(metadata):
                        print(f"Metadata number: {pmt.to_float(metadata)}")
                except Exception as e:
                    print(f"Error parsing metadata: {e}")
            
            print("------------------------------")
        else:
            print("Message is not a PMT pair")
            
            # Safely print raw message
            try:
                if pmt.is_u8vector(msg):
                    data = bytearray(pmt.u8vector_elements(msg))
                    print(f"Raw message: <binary data of length {len(data)}>")
                    print(f"Hex representation: {data.hex()}")
                elif pmt.is_blob(msg):
                    data = pmt.blob_data(msg)
                    print(f"Raw message: <binary blob of length {len(data)}>")
                    print(f"Hex representation: {data.hex()}")
                else:
                    print(f"Raw message type: {type(msg)}")
            except Exception as e:
                print(f"Cannot print raw message: {str(e)}")
                
            print("------------------------------")


class lora(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "LoRa_Decoder", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("LoRa_Decoder")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "lora")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 1.5e6

        ##################################################
        # Blocks
        ##################################################

        self.osmosdr_source_0 = osmosdr.source(
            args="numchan=" + str(1) + " " + ""
        )
        self.osmosdr_source_0.set_time_unknown_pps(osmosdr.time_spec_t())
        self.osmosdr_source_0.set_sample_rate(samp_rate)
        self.osmosdr_source_0.set_center_freq((915*10**6), 0)
        self.osmosdr_source_0.set_freq_corr(0, 0)
        self.osmosdr_source_0.set_dc_offset_mode(0, 0)
        self.osmosdr_source_0.set_iq_balance_mode(0, 0)
        self.osmosdr_source_0.set_gain_mode(False, 0)
        self.osmosdr_source_0.set_gain(10, 0)
        self.osmosdr_source_0.set_if_gain(20, 0)
        self.osmosdr_source_0.set_bb_gain(20, 0)
        self.osmosdr_source_0.set_antenna('', 0)
        self.osmosdr_source_0.set_bandwidth(0, 0)
        
        self.lora_rx_0 = lora_sdr.lora_sdr_lora_rx(
            bw=125000,          # Correct: 125kHz
            cr=2,               # Changed from 1 to 2 (coding rate 4/6)
            has_crc=True,       # Correct: CRC is enabled
            impl_head=False,    # Correct: Explicit header
            pay_len=255,        # Maximum payload length
            samp_rate=int(samp_rate),
            sf=8,               # Correct: SF8
            sync_word=[0x12],   # Standard LoRa sync word
            soft_decoding=True, 
            ldro_mode=2,        
            print_rx=[True,True]  # Enable printing of received data
        )
        
        # Add a message debug block to find all ports
        self.debug = blocks.message_debug()
        
        # Create our custom packet sink to display RSSI/SNR
        self.packet_sink = lora_packet_sink()
        
        # Connect to the 'out' port (or try other port names used by lora_sdr)
        self.msg_connect((self.lora_rx_0, 'out'), (self.packet_sink, 'packets'))
        
        # Also try connecting to other potential ports to see what's available
        try:
            self.msg_connect((self.lora_rx_0, 'header'), (self.debug, 'print'))
            print("Found 'header' port on lora_rx_0")
        except:
            pass
            
        try:
            self.msg_connect((self.lora_rx_0, 'frame_info'), (self.debug, 'print'))
            print("Found 'frame_info' port on lora_rx_0")
        except:
            pass
            
        ##################################################
        # Connections
        ##################################################
        self.connect((self.osmosdr_source_0, 0), (self.lora_rx_0, 0))

    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "lora")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()
        event.accept()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.osmosdr_source_0.set_sample_rate(self.samp_rate)


def main(top_block_cls=lora, options=None):
    qapp = Qt.QApplication(sys.argv)
    tb = top_block_cls()
    tb.start()
    tb.flowgraph_started.set()
    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()
        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
