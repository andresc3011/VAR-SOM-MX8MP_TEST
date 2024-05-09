import os
import struct
import subprocess
import sys
import threading
import tkinter as tk
import serial
import time
#from monitorcontrol import get_monitors
if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
    from ads1015 import ADS1015
if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
    import fcntl
    from watchdogdev import *
import socket

"""monitor = get_monitors()
try:
    monitor = monitor[0]
except:
    print(monitor)"""

class MainApp(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.wm_title("Test HW")

        #self.attributes('-fullscreen', True)

        container = tk.Frame(self)
        container.pack(side = "top", fill = "both", expand = True) 

        container.grid_rowconfigure(0, weight = 1)
        container.grid_columnconfigure(0, weight = 1)

        buttons_frame = tk.Frame(self)
        buttons_frame.pack(side=tk.BOTTOM)

        back_button = tk.Button(buttons_frame, text="Back", command=lambda:self.show_frame(MainView))
        back_button.pack(side=tk.LEFT)

        #back_button = tk.Button(buttons_frame, text="Shutdown", command=self.shutdown)
        #back_button.pack(side=tk.RIGHT, padx=(50,0))

        ###GPIO###

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.gpio_list = {"name": [], "abs_num": [], "direction": [], "value": [], "active_low": []}

        file = open("gpios_list.txt", 'r')
        cond = lambda line: line[0] == 'G'
        for line in filter(cond, file):
            self.gpio_list["name"].append(line[0:line.find(",")])
            if "in" in line:
                self.gpio_list["direction"].append("in")
            elif "out" in line:
                self.gpio_list["direction"].append("out")
            self.gpio_list["abs_num"].append(str((int(line[4])-1)*32+int(line[8:10])))
            self.gpio_list["active_low"].append(str(line[-2]))

        file.close()

        #print(self.gpio_list)

        """for i in range(len(self.gpio_list['abs_num'])):
            if sys.platform.startswith('linux'): 
                os.system("echo " + self.gpio_list['abs_num'][i] + " > /sys/class/gpio/export")
                os.system("echo " + self.gpio_list['direction'][i] + " > /sys/class/gpio/gpio"+self.gpio_list['abs_num'][i]+"/direction")
                os.system("echo " + self.gpio_list['active_low'][i] + " > /sys/class/gpio/gpio"+self.gpio_list['abs_num'][i]+"/active_low")
        
            print(self.gpio_list['abs_num'][i], self.gpio_list['direction'][i], self.gpio_list['active_low'][i])"""


        ##Frames
        
        self.frames = {}  

        for F in (MainView, RS232View, TFTView, EthView, USBView, GPIOView, ADCView, WDView):
  
            frame = F(container, self)
            self.frames[F] = frame 
            frame.grid(row = 0, column = 0, sticky ="nsew")

        self.show_frame(MainView)
    
    def on_closing(self):

        """if sys.platform.startswith('linux'): 
            for i in range(len(self.gpio_list['abs_num'])):
                os.system("echo " + self.gpio_list['abs_num'][i] + " > /sys/class/gpio/unexport")"""

        self.frames[ADCView].stop = True
        self.frames[GPIOView].stop = True

        while((self.frames[ADCView].stopped_thread==False) or (self.frames[GPIOView].stopped_thread==False)):
            time.sleep(0.5)
        self.destroy()

    def shutdown(self):
        os.system("shutdown now")

    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()
        if cont == ADCView:
            frame.start_thread()
        elif cont == GPIOView:
            frame.start_thread()
        elif cont == WDView:
            frame.start_thread()
        elif cont == MainView:
            self.frames[ADCView].stop = True
            self.frames[GPIOView].stop = True
            self.frames[WDView].stop = True
        elif cont == USBView:
            self.frames[USBView].label_message.config(text="")           

class MainView(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        self.config(bg="#000F1E")

        #button_test_tft = tk.Button(self, text="TFT", font=("Arial", 15), command=lambda:controller.show_frame(TFTView))
        #button_test_tft.pack(pady=(20,10))

        button_test_rs232 = tk.Button(self, text="RS232", font=("Arial", 15), command=lambda:controller.show_frame(RS232View))
        button_test_rs232.pack(pady=(20,10))

        button_test_eth = tk.Button(self, text="Ethernet", font=("Arial", 15), command=lambda:controller.show_frame(EthView))
        button_test_eth.pack(pady=(10,10))

        button_test_usb = tk.Button(self, text="USB", font=("Arial", 15), command=lambda:controller.show_frame(USBView))
        button_test_usb.pack(pady=(10,10))

        button_test_on_off = tk.Button(self, text="GPIO", font=("Arial", 15), command=lambda:controller.show_frame(GPIOView))
        button_test_on_off.pack(pady=(10,10))

        button_test_adc = tk.Button(self, text="ADC", font=("Arial", 15), command=lambda:controller.show_frame(ADCView))
        button_test_adc.pack(pady=(10,10))

        #button_test_wd = tk.Button(self, text="WD", font=("Arial", 15), command=lambda:controller.show_frame(WDView))
        #button_test_adc.pack(pady=(10,20))

class TFTView(tk.Frame):
   
    def __init__(self, parent, controller):

        tk.Frame.__init__(self, parent)

        self.bright_control = tk.Scale(self, from_=0, to=100, orient="horizontal", command=lambda value:self.bright(value))
        self.bright_control.pack()

        self.bright_value = 80

    def bright(self, value):
        self.bright_value = int(value)
        monitor = object()
        with monitor:
            monitor.set_luminance(self.bright_value)
    
class RS232View(tk.Frame):
   
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        frame_1 = tk.Frame(self)
        frame_2 = tk.Frame(self)
        frame_1.pack()
        frame_2.pack()
        frame_buttons = tk.Frame(frame_1)
        frame_labels = tk.Frame(frame_1)
        frame_buttons.pack(side=tk.LEFT)
        frame_labels.pack(side=tk.LEFT)

        button_test_rs2323_1 = tk.Button(frame_buttons, text="RS232 1", command=lambda:self.test_rs232(0))
        button_test_rs2323_1.pack()
        button_test_rs2323_2 = tk.Button(frame_buttons, text="RS232 2", command=lambda:self.test_rs232(1))
        button_test_rs2323_2.pack()
        button_test_rs2323_3 = tk.Button(frame_buttons, text="RS232 3", command=lambda:self.test_rs232(2))
        button_test_rs2323_3.pack()
        button_test_rs2323_4 = tk.Button(frame_buttons, text="RS232 4", command=lambda:self.test_rs232(3))
        button_test_rs2323_4.pack()
        button_test_rs2323_5 = tk.Button(frame_buttons, text="RS232 5", command=lambda:self.test_rs232(4))
        button_test_rs2323_5.pack()
        button_test_rs2323_6 = tk.Button(frame_buttons, text="RS232 6", command=lambda:self.test_rs232(5))
        button_test_rs2323_6.pack()
        button_test_rs2323_7 = tk.Button(frame_buttons, text="RS232 7", command=lambda:self.test_rs232(6))
        button_test_rs2323_7.pack()
        button_test_rs2323_8 = tk.Button(frame_buttons, text="RS232 8", command=lambda:self.test_rs232(7))
        button_test_rs2323_8.pack()

        self.label_test_rs2323 = [None, None, None, None, None, None, None, None]
        self.label_test_rs2323[0] = tk.Label(frame_labels, text="RS232 1")
        self.label_test_rs2323[0].pack(pady=(4,3))
        self.label_test_rs2323[1] = tk.Label(frame_labels, text="RS232 2")
        self.label_test_rs2323[1].pack(pady=(3))
        self.label_test_rs2323[2] = tk.Label(frame_labels, text="RS232 3")
        self.label_test_rs2323[2].pack(pady=(3))
        self.label_test_rs2323[3] = tk.Label(frame_labels, text="RS232 4")
        self.label_test_rs2323[3].pack(pady=(3))
        self.label_test_rs2323[4] = tk.Label(frame_labels, text="RS232 5")
        self.label_test_rs2323[4].pack(pady=(3))
        self.label_test_rs2323[5] = tk.Label(frame_labels, text="RS232 6")
        self.label_test_rs2323[5].pack(pady=(3))
        self.label_test_rs2323[6] = tk.Label(frame_labels, text="RS232 7")
        self.label_test_rs2323[6].pack(pady=(3))
        self.label_test_rs2323[7] = tk.Label(frame_labels, text="RS232 8")
        self.label_test_rs2323[7].pack()


    def test_rs232(self, port):

        #Init rs232 port
        self.device = serial.Serial()
        self.device.port = "/dev/ttyUSB"+str(port)
        print(self.device.port)
        self.device.baudrate = 9600
        self.device.bytesize = serial.EIGHTBITS
        self.device.parity = serial.PARITY_NONE
        self.device.stopbits = serial.STOPBITS_ONE
        self.device.timeout = 1
        #print(serial_port)
        try:
            self.device.open()
            print('Initialized port')
            self.stopped = False

            #Send message
            message_send = "ttyUSB"+str(port)+"\n"
            self.device.write(message_send.encode())
            print(message_send)

            time.sleep(1)

            #receive message
            message_received = self.device.readline().decode()
            print(message_received)
            if message_send == message_received:
                self.label_test_rs2323[port].configure(text="OK")
            else:
                self.label_test_rs2323[port].configure(text="Error")

        except serial.SerialException:
            print("Error in port")
            self.label_test_rs2323[port].configure(text="Error")


        self.device.close()
    
class EthView(tk.Frame):
   
    def __init__(self, parent, controller):

        tk.Frame.__init__(self, parent)

        if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):

            ifname='eth0'
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ip_address = socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s',  bytes(ifname[:15], 'utf-8'))
            )[20:24])


            self.label = tk.Label(self, text="IP eth0: "+str(ip_address))
            self.label.pack(pady=(20,20))

            self.label1 = tk.Label(self, text="Destination")
            self.label1.pack()

            self.entry = tk.Entry(self)
            self.entry.pack(pady=(0,20))
            self.entry.insert(0, "www.google.com")

            self.button = tk.Button(self, text="Ping", command=self.do_ping)
            self.button.pack()

            self.label2 = tk.Label(self, text="Result: ")
            self.label2.pack()
    
    def do_ping(self):

        destino = self.entry.get()
        intentos = 3
        comando = ["ping", "-c", str(intentos), destino]
        proceso = subprocess.Popen(comando, stdout=subprocess.PIPE)
        salida, _ = proceso.communicate()

        self.label2.config(text=salida.decode())

class USBView(tk.Frame):
   
    def __init__(self, parent, controller):

        tk.Frame.__init__(self, parent)

        button_test1 = tk.Button(self, text="List USB", command=self.print_list)
        button_test1.pack()

        self.label_list = tk.Label(self, text="")
        self.label_list.pack()

        button_test2 = tk.Button(self, text="Try read USB Storage", command=self.test)
        button_test2.pack()

        self.label_message = tk.Label(self, text="")
        self.label_message.pack()

    def print_list(self):

        if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            comando = ["lsusb"]
            proceso = subprocess.Popen(comando, stdout=subprocess.PIPE)
            salida, _ = proceso.communicate()

            self.label_list.config(text=salida.decode())

    def test(self):

        if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):

            os.system("mount /dev/sda1 /mnt")

            f = open("/mnt/test.txt", "r")
            received = f.readline()
            f.close()

            os.system("umount /dev/sda1")

            if received == "OK":
                self.label_message.config(text="USB OK")
            else:
                self.label_message.config(text="USB ERROR")

class GPIOView(tk.Frame):
   
    def __init__(self, parent, controller):

        tk.Frame.__init__(self, parent)

        self.controller = controller

        self.stop = False
        self.stopped_thread = True

        frame1 = tk.Frame(self)
        frame1.pack()

        self.names_label = []
        self.buttons_set_1 = []
        self.buttons_set_0 = []
        self.values_label = []

        for i in range(len(controller.gpio_list['name'])):

            self.names_label.append(tk.Label(frame1, text=controller.gpio_list['name'][i], font=("Arial", "15")))
            if controller.gpio_list['direction'][i] == "out":
                self.buttons_set_1.append(tk.Button(frame1, text="Set 1", font=("Arial", "15"), command=lambda i=i: self.gpio_set(controller.gpio_list['abs_num'][i], "1")))
                self.buttons_set_0.append(tk.Button(frame1, text="Set 0", font=("Arial", "15"), command=lambda i=i: self.gpio_set(controller.gpio_list['abs_num'][i], "0")))
            else:
                self.buttons_set_1.append(tk.Label(frame1, text="Input is been reading"))
                self.buttons_set_0.append(tk.Label(frame1, text=""))
            self.values_label.append(tk.Label(frame1, text="0", font=("Arial", "20")))

        frame_aux = tk.Frame(frame1, bg="#000F1E", height=40)

        label1 = tk.Label(frame_aux, text="GPIO name")
        label2 = tk.Label(frame_aux, text="Set")
        label3 = tk.Label(frame_aux, text="Value")
        label1.place(relx=0.12, rely=0.23)
        label2.place(relx=0.60, rely=0.23)
        label3.place(relx=0.88, rely=0.23)

        frame_aux.grid(row=0, columnspan=4, sticky='nwse')
        
        for i in range(len(self.names_label)):

            self.names_label[i].grid(row=i+1, column=0, padx=(20,20), pady=(5,5))
            if controller.gpio_list['direction'][i] == "out":
                self.buttons_set_1[i].grid(row=i+1, column=1, padx=(20,5), pady=(5,5))
                self.buttons_set_0[i].grid(row=i+1, column=2, padx=(5,20), pady=(5,5))
            else:
                self.buttons_set_1[i].grid(row=i+1, column=1, columnspan=2, pady=(5,5))
            self.values_label[i].grid(row=i+1, column=3, padx=(20,20), pady=(5,5))

        self.inputs = {"i":[], "gpio":[]}
        for i in range(len(self.names_label)):
            if controller.gpio_list['direction'][i] == "in":
                self.inputs["i"].append(i)
                self.inputs["gpio"].append(controller.gpio_list['abs_num'][i])
    
    def start_thread(self):
        self.stop = self.stopped_thread = False
        self.thread = threading.Thread(target=self.read_gpio)
        self.thread.start()

    def gpio_set(self, gpio, value):
        if sys.platform.startswith('linux'): 
            os.system("echo "+value+" > /sys/class/gpio/gpio"+gpio+"/value")

        if gpio in self.controller.gpio_list['abs_num']:
            self.values_label[self.controller.gpio_list['abs_num'].index(gpio)].config(text=value)
    
    def read_gpio(self):

        while True:
            if self.stop:
                self.stopped_thread = True
                print("GPIO thread end")
                break
            else:
                if sys.platform.startswith('linux'): 
                    #print(self.inputs["i"])
                    for i in range(len(self.inputs["i"])):
                        self.values_label[self.inputs["i"][i]].config(text=str(subprocess.getoutput("cat /sys/class/gpio/gpio"+self.inputs["gpio"][i]+"/value")))

            time.sleep(0.1)

class ADCView(tk.Frame):

    def __init__(self, parent, controller):

        tk.Frame.__init__(self, parent)

        frameaux = tk.Frame(self)
        frameaux.pack(expand=True)

        self.label1 = tk.Label(frameaux, text="Vbat", font=("Arial, 15"))
        self.label2 = tk.Label(frameaux, text="Vin", font=("Arial, 15"))
        self.label3 = tk.Label(frameaux, text="T Sense U60", font=("Arial, 15"))
        self.label4 = tk.Label(frameaux, text="T Sense U56", font=("Arial, 15"))

        self.label_value1 = tk.Label(frameaux, text="0.0v", font=("Arial, 20"))
        self.label_value2 = tk.Label(frameaux, text="0.0v", font=("Arial, 20"))
        self.label_value3 = tk.Label(frameaux, text="0.0v", font=("Arial, 20"))
        self.label_value4 = tk.Label(frameaux, text="0.0v", font=("Arial, 20"))

        self.label1.grid(column=0, row=0)
        self.label2.grid(column=0, row=1)
        self.label3.grid(column=0, row=2)
        self.label4.grid(column=0, row=3)

        self.label_value1.grid(column=1, row=0, padx=(30,0))
        self.label_value2.grid(column=1, row=1, padx=(30,0))
        self.label_value3.grid(column=1, row=2, padx=(30,0))
        self.label_value4.grid(column=1, row=3, padx=(30,0))

        self.stop = False
        self.stopped_thread = True
        self.CHANNELS = ["in0/gnd", "in1/gnd", "in2/gnd", "in3/gnd"]

    def start_thread(self):

        if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            self.ads1015 = ADS1015(i2c_bus=3)
            chip_type = self.ads1015.detect_chip_type()

            print("Found: {}".format(chip_type))

            self.ads1015.set_mode("single")
            self.ads1015.set_programmable_gain(4.096)

            if chip_type == "ADS1015":
                self.ads1015.set_sample_rate(1600)
            else:
                self.ads1015.set_sample_rate(860)
            
            #self.reference = self.ads1015.get_reference_voltage()

        self.stop = self.stopped_thread = False
        self.thread = threading.Thread(target=self.read_values)
        self.thread.start()

    def read_values(self):

        while True:
            if self.stop:
                self.stopped_thread = True
                print("ADC thread end")
                break
            else:
                if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
                    for channel in self.CHANNELS:
                        value, value_raw = self.ads1015.get_voltage(channel)
                        #value = self.ads1015.get_conversion_value()
                        #print("{}: {:6.3f}v, raw: {}".format(channel, value, value_raw))
                        #print("{}: {:6.3f}v, raw: {}, compensated: {:6.3f}v".format(channel, value, value_raw, self.ads1015.get_compensated_voltage(channel, reference_voltage=self.reference)))
                        if channel == "in0/gnd":
                            self.label_value1.config(text="{:6.3f}v".format(value))
                        if channel == "in1/gnd":
                            self.label_value2.config(text="{:6.3f}v".format(value))
                        if channel == "in2/gnd":
                            self.label_value3.config(text="{:6.3f}v".format(value))
                        if channel == "in3/gnd":
                            self.label_value4.config(text="{:6.3f}v".format(value))
            
            time.sleep(0.5)

class WDView(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):

            self.stop = False
            self.stopped_thread = True
            self.label = tk.Label(self, text="")
            self.label.pack(pady=(20,20))

            self.label_ticks = tk.Label(self, text="")
            self.label_ticks.pack(pady=(20,20))

            self.ticks=""

    def start_thread(self):

        if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):

            self.wd = watchdog('/dev/watchdog')
            self.wd.set_timeout(10)

            self.label.config(text="Watch Dog activated!\nTimeout: "+str(self.wd.get_timeout()))

            self.stop = self.stopped_thread = False
            self.thread = threading.Thread(target=self.send_tick)
            self.thread.start()
    
    def send_tick(self):

        while True:
            if self.stop:
                self.stopped_thread = True
                print("WD thread end")
                break
            else:
                self.wd.keep_alive()
                self.ticks=self.ticks+"."
                self.label_ticks.config(text=str(self.ticks))

            time.sleep(5)

if __name__ == "__main__":
  app = MainApp()
  app.mainloop()