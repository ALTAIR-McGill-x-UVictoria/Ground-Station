import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import serial.tools.list_ports
from serial import Serial
import xml.etree.ElementTree as ET
import csv
import threading
import datetime
import numpy as np

class SerialMonitor:
    
    
    
    def __init__(self, master):
        self.master = master
        self.master.title("Ground station")
        # self.master.geometry("1600x900")
        self.master.geometry("1920x1080")
        self.master.resizable('True','True')

        self.create_widgets()

        # Flag to indicate if the serial connection is active
        self.connection_active = False
        
        

    def create_widgets(self):
        
        # self.datalistFC = [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(),tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(),tk.StringVar(), tk.StringVar()]
        self.datalistFC = [tk.StringVar() for _ in range(30)]
        self.datalistGS = [tk.StringVar(), tk.StringVar()]
    
        self.port_combobox_label = ttk.Label(self.master, text="Select Port:")
        self.port_combobox_label.grid(row=0, column=0, padx=10, pady=10)

        self.populate_ports()

        self.baud_combobox_label = ttk.Label(self.master, text="Select Baud Rate:")
        self.baud_combobox_label.grid(row=0, column=1, padx=10, pady=10)
        
        self.baud_combobox = ttk.Combobox(self.master, values=["2400","4800","9600","14400", "115200"], state="readonly")
        self.baud_combobox.set("115200")
        self.baud_combobox.grid(row=0, column=2, padx=10, pady=10)

        self.connect_button = ttk.Button(self.master, text="Connect", command=self.connect)
        self.connect_button.grid(row=0, column=3, padx=10, pady=10)

        self.disconnect_button = ttk.Button(self.master, text="Disconnect", command=self.disconnect, state=tk.DISABLED)
        self.disconnect_button.grid(row=0, column=4, padx=10, pady=10)

        self.export_txt_button = ttk.Button(self.master, text="Export as TXT", command=self.export_txt, state=tk.DISABLED)
        self.export_txt_button.grid(row=0, column=5, padx=10, pady=10)

        self.export_csv_button = ttk.Button(self.master, text="Export as CSV", command=self.export_csv, state=tk.DISABLED)
        self.export_csv_button.grid(row=0, column=6, padx=10, pady=10)

        self.export_xml_button = ttk.Button(self.master, text="Export as XML", command=self.export_xml, state=tk.DISABLED)
        self.export_xml_button.grid(row=0, column=7, padx=10, pady=10)

        self.log_text = scrolledtext.ScrolledText(self.master, wrap=tk.WORD, width=80, height=30)
        self.log_text.grid(row=2, column=0, columnspan=6, padx=0, pady=15, rowspan=5)
        
        self.command_text = tk.Entry(self.master) 
        self.command_text.grid(row=1, column=1) 
        
        
        self.send_command_button = ttk.Button(self.master, text="Send", command = self.write_to_port)
        self.send_command_button.grid(row=1, column=0, padx=10, pady=10)
        
        self.ping_button = ttk.Button(self.master, text="Ping", command = self.ping)
        self.ping_button.grid(row=1, column=3, padx=10, pady=10)
        
        
        
        #DATA PARSING
        
        self.datacolumn = ttk.LabelFrame(self.master, text="Parsed Data")
        self.datacolumn.grid(row=1, column=6, padx=5, pady=5, rowspan=2)
        
        
        #FC signal data
        self.fcrssi_label = ttk.Label(self.datacolumn, text="FC RSSI: ")
        self.fcrssi_label.grid(row=0, column=1, padx=5, pady=5)
        
        self.fcrssi_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[1])
        self.fcrssi_value.grid(row=0, column=2, padx=5, pady=5)
        
        self.fcsnr_label = ttk.Label(self.datacolumn, text="FC SNR: ")
        self.fcsnr_label.grid(row=0, column=3, padx=5, pady=5)
        
        self.fcsnr_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[2])
        self.fcsnr_value.grid(row=0, column=4, padx=5, pady=5)
        
        #GS signal data
        self.gsrssi_label = ttk.Label(self.datacolumn, text="GS RSSI: ")
        self.gsrssi_label.grid(row=1, column=1, padx=5, pady=5)
        
        self.gsrssi_value = ttk.Label(self.datacolumn, textvariable=self.datalistGS[0])
        self.gsrssi_value.grid(row=1, column=2, padx=5, pady=5)
        
        self.gssnr_label = ttk.Label(self.datacolumn, text="GS SNR:")
        self.gssnr_label.grid(row=1, column=3, padx=5, pady=5)
        
        self.gssnr_value = ttk.Label(self.datacolumn, textvariable=self.datalistGS[1])
        self.gssnr_value.grid(row=1, column=4, padx=5, pady=5)
        
        #FC battery voltage
        self.voltage_label = ttk.Label(self.datacolumn, text="Battery Voltage: ")
        self.voltage_label.grid(row=2, column=2, padx=5, pady=5)
        
        self.voltage_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[3])
        self.voltage_value.grid(row=2, column=3, padx=5, pady=5)
        
        #FC angle data
        self.pitch_label = ttk.Label(self.datacolumn, text="Roll:")
        self.pitch_label.grid(row=3, column=0, padx=5, pady=5)
        
        self.pitch_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[4])
        self.pitch_value.grid(row=3, column=1, padx=5, pady=5)
        
        self.pitch_label = ttk.Label(self.datacolumn, text="Pitch:")
        self.pitch_label.grid(row=3, column=2, padx=5, pady=5)
        
        self.pitch_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[5])
        self.pitch_value.grid(row=3, column=3, padx=5, pady=5)
        
        self.yaw_label = ttk.Label(self.datacolumn, text="Yaw:")
        self.yaw_label.grid(row=3, column=4, padx=5, pady=5)
        
        self.yaw_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[6])
        self.yaw_value.grid(row=3, column=5, padx=5, pady=5)
        
        #FC Acc Data
        self.accx_label = ttk.Label(self.datacolumn, text="AccX:")
        self.accx_label.grid(row=4, column=0, padx=5, pady=5)
        
        self.accx_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[7])
        self.accx_value.grid(row=4, column=1, padx=5, pady=5)
        
        self.accy_label = ttk.Label(self.datacolumn, text="AccY:")
        self.accy_label.grid(row=4, column=2, padx=5, pady=5)
        
        self.accy_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[8])
        self.accy_value.grid(row=4, column=3, padx=5, pady=5)
        
        self.accz_label = ttk.Label(self.datacolumn, text="AccZ:")
        self.accz_label.grid(row=4, column=4, padx=5, pady=5)
        
        self.accz_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[9])
        self.accz_value.grid(row=4, column=5, padx=5, pady=5)
        
        #FC Ambient and altitude data
        self.pressure_label = ttk.Label(self.datacolumn, text="Pressure:")
        self.pressure_label.grid(row=4, column=0, padx=5, pady=5)
        
        self.pressure_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[10])
        self.pressure_value.grid(row=4, column=1, padx=5, pady=5)
        
        self.altitude_label = ttk.Label(self.datacolumn, text="Altitude:")
        self.altitude_label.grid(row=4, column=2, padx=5, pady=5)
        
        self.altitude_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[11])
        self.altitude_value.grid(row=4, column=3, padx=5, pady=5)
        
        self.temperature_label = ttk.Label(self.datacolumn, text="Temperature:")
        self.temperature_label.grid(row=4, column=4, padx=5, pady=5)
        
        self.temperature_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[12])
        self.temperature_value.grid(row=4, column=5, padx=5, pady=5)
        
        #LED statuses
        self.led1_label = ttk.Label(self.datacolumn, text="LED #1:")
        self.led1_label.grid(row=5, column=0, padx=5, pady=5)
        
        self.led1_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[13])
        self.led1_value.grid(row=5, column=1, padx=5, pady=5)
        
        self.led2_label = ttk.Label(self.datacolumn, text="LED #2:")
        self.led2_label.grid(row=5, column=2, padx=5, pady=5)
        
        self.led2_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[14])
        self.led2_value.grid(row=5, column=3, padx=5, pady=5)
        
        self.led3_label = ttk.Label(self.datacolumn, text="LED #3:")
        self.led3_label.grid(row=5, column=4, padx=5, pady=5)
        
        self.led3_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[15])
        self.led3_value.grid(row=5, column=5, padx=5, pady=5)
        
        self.sd_label = ttk.Label(self.datacolumn, text="LED Brightness:")
        self.sd_label.grid(row=6, column=1, padx=5, pady=5)
        
        self.sd_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[16])
        self.sd_value.grid(row=6, column=2, padx=5, pady=5)
        
        #SD status
        self.sd_label = ttk.Label(self.datacolumn, text="SD Write:")
        self.sd_label.grid(row=6, column=3, padx=5, pady=5)
        
        self.sd_value = ttk.Label(self.datacolumn, textvariable=self.datalistFC[17])
        self.sd_value.grid(row=6, column=4, padx=5, pady=5)
        
        #CONTROL COMMAND BUTTONS
        
        self.commandcolumn = ttk.LabelFrame(self.master, text="Control")
        self.commandcolumn.grid(row=3, column=6, padx=5, pady=5, rowspan=2)
        
        self.led1_toggle = ttk.Button(self.commandcolumn, text="LED #1", command=self.led1)
        self.led1_toggle.grid(row=0, column=0, padx=5, pady=3)
        
        self.led2_toggle = ttk.Button(self.commandcolumn, text="LED #2", command=self.led2)
        self.led2_toggle.grid(row=0, column=1, padx=5, pady=3)
        
        self.led3_toggle = ttk.Button(self.commandcolumn, text="LED #3", command=self.led3)
        self.led3_toggle.grid(row=0, column=2, padx=5, pady=3)
        
        self.ledbright_label = ttk.Label(self.commandcolumn, text="Brightness:")
        self.ledbright_label.grid(row=1, column=0, padx=0, pady=3)
        
        self.ledbright_value = ttk.Entry(self.commandcolumn)
        self.ledbright_value.grid(row=1, column=1, padx=1, pady=3, columnspan=1)
        
        self.ledbright_set = ttk.Button(self.commandcolumn, text="Set", command=self.setledbright)
        self.ledbright_set.grid(row=1, column=2, padx=0, pady=3, columnspan=1)
        
        # self.ledblink = ttk.Button(self.commandcolumn, text="Toggle Blinking", command=self.toggleblink)
        # self.ledblink.grid(row=2, column=0, padx=20, pady=3, columnspan=3, sticky = tk.W+tk.E)
        
        self.ledblink_label = ttk.Label(self.commandcolumn, text="Blink Delay:")
        self.ledblink_label.grid(row=2, column=0, padx=0, pady=3)
        
        self.ledblink_value = ttk.Entry(self.commandcolumn)
        self.ledblink_value.grid(row=2, column=1, padx=1, pady=3, columnspan=1)
        
        self.ledblink_set = ttk.Button(self.commandcolumn, text="Set", command=self.toggleblink)
        self.ledblink_set.grid(row=2, column=2, padx=0, pady=3, columnspan=1)
        
        self.ledoff = ttk.Button(self.commandcolumn, text="LEDs OFF", command=self.ledoff)
        self.ledoff.grid(row=3, column=0, padx=20, pady=3, columnspan=3, sticky = tk.W+tk.E)
        
        self.stepperangle_label = ttk.Label(self.commandcolumn, text="Stepper Angle:")
        self.stepperangle_label.grid(row=4, column=0, padx=0, pady=3)
        
        self.stepperangle_value = ttk.Entry(self.commandcolumn)
        self.stepperangle_value.grid(row=4, column=1, padx=1, pady=3, columnspan=1)
        
        self.stepperangle_set = ttk.Button(self.commandcolumn, text="Set", command=self.setdriverangle)
        self.stepperangle_set.grid(row=4, column=2, padx=0, pady=3, columnspan=1)
        
        self.zeroangle = ttk.Button(self.commandcolumn, text="Zero Angle", command=self.zeroangle)
        self.zeroangle.grid(row=5, column=0, padx=5, pady=3, columnspan=1, sticky = tk.W+tk.E)
        
        self.togglestab = ttk.Button(self.commandcolumn, text="Toggle Stabilization", command=self.togglestabilization)
        self.togglestab.grid(row=5, column=1, padx=5, pady=3, columnspan=2, sticky = tk.W+tk.E)
        
        
        #COMMUNICATION COMMAND BUTTONS
        
        self.commcolumn = ttk.LabelFrame(self.master, text="Communication")
        self.commcolumn.grid(row=0, column=9, padx=5, pady=5, rowspan=3)
        
        self.clearqueue_button = ttk.Button(self.commcolumn, text="Clear Command Queue", command=self.clearqueue)
        self.clearqueue_button.grid(row=0, column=0, padx=10, pady=3, columnspan=3, sticky = tk.W+tk.E)
        
        self.flightmode_toggle = ttk.Button(self.commcolumn, text="Toggle Flight Mode", command=self.toggleFlightMode)
        self.flightmode_toggle.grid(row=1, column=0, padx=10, pady=3, columnspan=3, sticky = tk.W+tk.E)
        
        self.resetfc_button = ttk.Button(self.commcolumn, text="Reset Flight Computer", command=self.resetFC)
        self.resetfc_button.grid(row=2, column=0, padx=10, pady=3, columnspan=3, sticky = tk.W+tk.E)
        
        self.togglepacket_button = ttk.Button(self.commcolumn, text="Toggle Packet Size", command=self.togglepacketsize)
        self.togglepacket_button.grid(row=3, column=0, padx=10, pady=3, columnspan=3, sticky = tk.W+tk.E)
        
        
        #SD COMMAND BUTTONS
        
        self.sdcolumn = ttk.LabelFrame(self.master, text="SD Card")
        self.sdcolumn.grid(row=2, column=9, padx=5, pady=5, rowspan=5, columnspan=2)
        
        self.sdenable_button = ttk.Button(self.sdcolumn, text="Write", command=self.sdwrite)
        self.sdenable_button.grid(row=0, column=0, padx=10, pady=3, columnspan=1, sticky = tk.W+tk.E)
        
        self.sddisable_button = ttk.Button(self.sdcolumn, text="Stop", command=self.sdstop)
        self.sddisable_button.grid(row=0, column=2, padx=10, pady=3, columnspan=1, sticky = tk.W+tk.E)
        
        
        
        
        

    def populate_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combobox = ttk.Combobox(self.master, values=ports, state="readonly")
        self.port_combobox.grid(row=0, column=0, padx=10, pady=10)

    def connect(self):
        port = self.port_combobox.get()
        baud = int(self.baud_combobox.get())
        try:
            self.ser = Serial(port, baud, timeout=1)
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, f"Connected to {port} at {baud} baud\n")
            self.disconnect_button["state"] = tk.NORMAL
            self.connect_button["state"] = tk.DISABLED
            self.export_txt_button["state"] = tk.NORMAL
            self.export_csv_button["state"] = tk.NORMAL
            self.export_xml_button["state"] = tk.NORMAL

            self.connection_active = True

            self.read_thread = threading.Thread(target=self.read_from_port)
            # self.thread = threading.Thread(target=self.readwrite_handler)
            self.read_thread.start()
            
            # self.write_thread = threading.Thread(target=self.)
            

        except Exception as e:
            self.log_text.insert(tk.END, f"Error: {str(e)}\n")

    def disconnect(self):
        self.connection_active = False  # Set the flag to False to stop the reading thread
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()
        self.connect_button["state"] = tk.NORMAL
        self.disconnect_button["state"] = tk.DISABLED
        self.export_txt_button["state"] = tk.DISABLED
        self.export_csv_button["state"] = tk.DISABLED
        self.export_xml_button["state"] = tk.DISABLED
        self.log_text.insert(tk.END, "Disconnected\n")

    def read_from_port(self):
        while self.connection_active:  # Check the flag in the reading loop
            try:
                line = self.ser.readline().decode("utf-8")
                if line:
                    self.log_text.insert(tk.END, line)
                    self.log_text.see(tk.END)
                    stringdatalist = line.split(',')
                    
                    if(len(stringdatalist) > 2):
                        
                        for index,item in enumerate(stringdatalist[0:13]):
                            self.datalistFC[index].set(item)
                        
                        self.datalistFC[13].set(stringdatalist[13][0])
                        self.datalistFC[14].set(stringdatalist[13][1])
                        self.datalistFC[15].set(stringdatalist[13][2])
                        
                        self.datalistFC[16].set(stringdatalist[14])
                        self.datalistFC[17].set(stringdatalist[15])
                        
                        
                    elif (len(stringdatalist) == 2):
                        self.datalistGS[0].set(stringdatalist[0])
                        self.datalistGS[1].set(stringdatalist[1].strip())
                        
                    
            except Exception as e:
                if self.connection_active:  # Only log errors if the connection is still active
                    self.log_text.insert(tk.END, f"Error reading from port: {str(e)}\n")
                break
            
    def write_to_port(self):

        try:
            # input = self.command_text.get(1.0, "end-1c")
            input = self.command_text.get()
            self.ser.write(f"{input}\n".encode("utf-8"))  
            # self.log_text.insert(tk.END, f"{input}\n")              
                
        except Exception as e:
            
            self.log_text.insert(tk.END, f"Error writing to port: {str(e)}\n")
                    
    
    def write_command_to_port(self, input): #tried to make it work
        
        try:
            self.ser.write((input + '\n').encode("utf-8"))  
            
        except Exception as e:
            self.log_text.insert(tk.END, f"Error writing to port: {str(e)}\n")
        


    def export_txt(self):
        data = self.log_text.get(1.0, tk.END)
        filename = f"serial_log_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        with open(filename, "w") as file:
            file.write(data)
        self.log_text.insert(tk.END, f"Log exported as TXT: {filename}\n")

    def export_csv(self):
        data = self.log_text.get(1.0, tk.END)
        filename = f"serial_log_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        with open(filename, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerows([line.split() for line in data.splitlines()])
        self.log_text.insert(tk.END, f"Log exported as CSV: {filename}\n")

    def export_xml(self):
        data = self.log_text.get(1.0, tk.END)
        filename = f"serial_log_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.xml"
        root = ET.Element("LogData")
        lines = data.splitlines()
        for line in lines:
            entry = ET.SubElement(root, "Entry")
            ET.SubElement(entry, "Data").text = line
        tree = ET.ElementTree(root)
        tree.write(filename)
        self.log_text.insert(tk.END, f"Log exported as XML: {filename}\n")
        
    
    
####### Command Functions #######
    def ping(self):
        try:
            self.ser.write(f"ping\n".encode("utf-8"))  
                
        except Exception as e:
            return
            

    def led1(self):
        try:
            self.ser.write(f"led1\n".encode("utf-8"))  
                
        except Exception as e:
            return

    def led2(self):
        try:
            self.ser.write(f"led2\n".encode("utf-8"))  
                
        except Exception as e:
            return

    def led3(self):
        try:
            self.ser.write(f"led3\n".encode("utf-8"))  
                
        except Exception as e:
            return

    def setledbright(self):
        try:
            self.ser.write(f"ledbright {self.ledbright_value.get()}\n".encode("utf-8"))  
                
        except Exception as e:
            return
        
    def toggleblink(self):
        try:
            self.ser.write(f"ledblink {self.ledblink_value.get()}\n".encode("utf-8"))  
                
        except Exception as e:
            return

    def ledoff(self):
        try:
            self.ser.write(f"ledoff\n".encode("utf-8"))  
                
        except Exception as e:
            return
        
    def setdriverangle(self):
        try:
            self.ser.write(f"dangle {self.stepperangle_value.get()}\n".encode("utf-8"))  
                
        except Exception as e:
            return
        
    def zeroangle(self):
        try:
            self.ser.write(f"zeromotor\n".encode("utf-8"))  
                
        except Exception as e:
            return
        
    def togglestabilization(self):
        try:
            self.ser.write(f"togglestab\n".encode("utf-8"))  
                
        except Exception as e:
            return
        
    def clearqueue(self):
        try:
            self.ser.write(f"clearq\n".encode("utf-8"))  
                
        except Exception as e:
            return
        
    def toggleFlightMode(self):
        try:
            self.ser.write(f"toggleflightmode\n".encode("utf-8"))  
                
        except Exception as e:
            return
        
    def resetFC(self):
        try:
            self.ser.write(f"resetfc\n".encode("utf-8"))  
                
        except Exception as e:
            return
        
    def togglepacketsize(self):
        try:
            self.ser.write(f"togglelong\n".encode("utf-8"))  
                
        except Exception as e:
            return
    
    def sdwrite(self):
        try:
            self.ser.write(f"sdwrite\n".encode("utf-8"))  
                
        except Exception as e:
            return
        
    def sdstop(self):
        try:
            self.ser.write(f"sdstop\n".encode("utf-8"))  
                
        except Exception as e:
            return
    
    
        
if __name__ == "__main__":
    root = tk.Tk()
    app = SerialMonitor(root)
    root.mainloop()
