from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
    QStackedWidget, QGridLayout, QLabel, QFrame
)
from PyQt5.QtCore import Qt
import pyqtgraph as pg
import time # For time data

class PlotPanel(QWidget):
    """Panel for displaying telemetry data plots, based on gui.py structure"""
    
    def __init__(self, telemetry_model, settings_model, parent=None): # Added settings_model if needed
        super().__init__(parent)
        self.telemetry_model = telemetry_model
        self.settings_model = settings_model # Store if needed for plot configurations
        self.start_time = time.time() # For x-axis time data

        # Data storage for plots
        self.time_data = []
        self.altitude_gps_data = []
        self.altitude_baro_data = []
        self.ground_speed_data = []
        self.vertical_speed_data = [] # Calculated
        self.temperature_data = []
        self.pressure_data = []
        self.rssi_data = []
        self.snr_data = []
        
        # Last values for vertical speed calculation
        self.last_plot_altitude = None
        self.last_plot_altitude_time = None


        self.setup_ui()

        # Connect to model signals
        self.telemetry_model.data_updated.connect(self.update_plots_from_model)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Plot selector
        self.plot_selector = QComboBox()
        self.plot_selector.addItems(["Flight Data", "Signal Strength", "All Plots"])
        self.plot_selector.setStyleSheet("QComboBox { background-color: #2a2a2a; color: #ffffff; padding: 5px; border: 1px solid #3a3a3a; border-radius: 4px; min-width: 150px; }")
        self.plot_selector.currentIndexChanged.connect(self.switch_plot_view)
        main_layout.addWidget(self.plot_selector)
        
        # Stacked widget for plot pages
        self.plot_stack = QStackedWidget()
        main_layout.addWidget(self.plot_stack)
        
        # Create plot pages
        self.create_flight_data_page()
        self.create_signal_strength_page()
        self.create_all_plots_page()

    def create_flight_data_page(self):
        page = QWidget()
        layout = QGridLayout(page)
        
        # Altitude plot (GPS vs Baro)
        self.altitude_plot_flight = pg.PlotWidget(title="Altitude")
        self.altitude_plot_flight.setLabel('left', 'Altitude', units='m')
        self.altitude_plot_flight.setLabel('bottom', 'Time', units='s')
        self.altitude_plot_flight.showGrid(x=True, y=True)
        self.altitude_plot_flight.addLegend()
        self.altitude_gps_curve_flight = self.altitude_plot_flight.plot(pen='g', name='GPS Altitude')
        self.altitude_baro_curve_flight = self.altitude_plot_flight.plot(pen='y', name='Baro Altitude')
        layout.addWidget(self.altitude_plot_flight, 0, 0)
        
        # Speed plot (Ground vs Vertical)
        self.speed_plot_flight = pg.PlotWidget(title="Speed")
        self.speed_plot_flight.setLabel('left', 'Speed', units='m/s')
        self.speed_plot_flight.setLabel('bottom', 'Time', units='s')
        self.speed_plot_flight.showGrid(x=True, y=True)
        self.speed_plot_flight.addLegend()
        self.ground_speed_curve_flight = self.speed_plot_flight.plot(pen='y', name='Ground Speed')
        self.vertical_speed_curve_flight = self.speed_plot_flight.plot(pen='c', name='Vertical Speed')
        layout.addWidget(self.speed_plot_flight, 0, 1)
        
        # Temperature plot
        self.temp_plot_flight = pg.PlotWidget(title="Temperature")
        self.temp_plot_flight.setLabel('left', 'Temperature', units='°C')
        self.temp_plot_flight.setLabel('bottom', 'Time', units='s')
        self.temp_plot_flight.showGrid(x=True, y=True)
        self.temp_curve_flight = self.temp_plot_flight.plot(pen='r')
        layout.addWidget(self.temp_plot_flight, 1, 0)
        
        # Pressure plot
        self.press_plot_flight = pg.PlotWidget(title="Pressure")
        self.press_plot_flight.setLabel('left', 'Pressure', units='hPa')
        self.press_plot_flight.setLabel('bottom', 'Time', units='s')
        self.press_plot_flight.showGrid(x=True, y=True)
        self.press_curve_flight = self.press_plot_flight.plot(pen='b')
        layout.addWidget(self.press_plot_flight, 1, 1)
        
        self.plot_stack.addWidget(page)

    def create_signal_strength_page(self):
        page = QWidget()
        layout = QGridLayout(page) # Changed to QGridLayout
        
        self.rssi_plot_signal = pg.PlotWidget(title="RSSI")
        self.rssi_plot_signal.setLabel('left', 'RSSI', units='dBm')
        self.rssi_plot_signal.setLabel('bottom', 'Time', units='s')
        self.rssi_plot_signal.showGrid(x=True, y=True)
        self.rssi_curve_signal = self.rssi_plot_signal.plot(pen='r')
        layout.addWidget(self.rssi_plot_signal, 0, 0)
        
        self.snr_plot_signal = pg.PlotWidget(title="SNR")
        self.snr_plot_signal.setLabel('left', 'SNR', units='dB')
        self.snr_plot_signal.setLabel('bottom', 'Time', units='s')
        self.snr_plot_signal.showGrid(x=True, y=True)
        self.snr_curve_signal = self.snr_plot_signal.plot(pen='b')
        layout.addWidget(self.snr_plot_signal, 1, 0) # Place below RSSI
        
        self.plot_stack.addWidget(page)

    def create_all_plots_page(self):
        page = QWidget()
        layout = QGridLayout(page)
        
        # Altitude (Combined)
        self.altitude_plot_all = pg.PlotWidget(title="Altitude (GPS vs Baro)")
        self.altitude_plot_all.setLabel('left', 'Altitude', units='m')
        self.altitude_plot_all.setLabel('bottom', 'Time', units='s')
        self.altitude_plot_all.showGrid(x=True, y=True)
        self.altitude_plot_all.addLegend()
        self.altitude_gps_curve_all = self.altitude_plot_all.plot(pen='g', name='GPS Alt')
        self.altitude_baro_curve_all = self.altitude_plot_all.plot(pen='y', name='Baro Alt')
        layout.addWidget(self.altitude_plot_all, 0, 0)

        # Speed (Combined)
        self.speed_plot_all = pg.PlotWidget(title="Speed (Ground vs Vertical)")
        self.speed_plot_all.setLabel('left', 'Speed', units='m/s')
        self.speed_plot_all.setLabel('bottom', 'Time', units='s')
        self.speed_plot_all.showGrid(x=True, y=True)
        self.speed_plot_all.addLegend()
        self.ground_speed_curve_all = self.speed_plot_all.plot(pen='y', name='Ground Spd')
        self.vertical_speed_curve_all = self.speed_plot_all.plot(pen='c', name='Vertical Spd')
        layout.addWidget(self.speed_plot_all, 0, 1)

        # Signal (Combined)
        self.signal_plot_all = pg.PlotWidget(title="Signal Strength (RSSI vs SNR)")
        self.signal_plot_all.setLabel('left', 'Level') # Generic Y label
        self.signal_plot_all.setLabel('bottom', 'Time', units='s')
        self.signal_plot_all.showGrid(x=True, y=True)
        self.signal_plot_all.addLegend()
        # Create two y-axes for RSSI and SNR if scales are very different, or plot on same.
        # For simplicity, plotting on same, adjust if needed.
        self.rssi_curve_all = self.signal_plot_all.plot(pen='r', name='RSSI (dBm)')
        self.snr_curve_all = self.signal_plot_all.plot(pen='b', name='SNR (dB)')
        layout.addWidget(self.signal_plot_all, 1, 0)
        
        # Temp & Pressure (Combined)
        self.temp_press_plot_all = pg.PlotWidget(title="Temperature & Pressure")
        # self.temp_press_plot_all.setLabel('left', 'Temperature', units='°C') # Use viewbox for multiple axes
        # self.temp_press_plot_all.setLabel('right', 'Pressure', units='hPa')
        self.temp_press_plot_all.setLabel('bottom', 'Time', units='s')
        self.temp_press_plot_all.showGrid(x=True, y=True)
        self.temp_press_plot_all.addLegend(offset=(-30,30)) # Adjust legend position

        p1 = self.temp_press_plot_all.getPlotItem()
        p1.setLabels(left='Temperature (°C)')
        
        self.temp_curve_all = p1.plot(pen='r', name='Temperature')

        # Create a new ViewBox for the right Y axis (Pressure)
        p2_vb = pg.ViewBox()
        p1.showAxis('right')
        p1.scene().addItem(p2_vb)
        p1.getAxis('right').linkToView(p2_vb)
        p2_vb.setXLink(p1)
        p1.getAxis('right').setLabel('Pressure (hPa)', color='#0000FF')

        self.press_curve_all = pg.PlotCurveItem(pen='b', name='Pressure')
        p2_vb.addItem(self.press_curve_all)

        def update_views(): # Function to update linked viewboxes
            p2_vb.setGeometry(p1.vb.sceneBoundingRect())
            p2_vb.linkedViewChanged(p1.vb, p2_vb.XAxis)
        p1.vb.sigResized.connect(update_views) # Connect resize signal
        update_views() # Initial call

        layout.addWidget(self.temp_press_plot_all, 1, 1)
        
        self.plot_stack.addWidget(page)

    def switch_plot_view(self, index):
        self.plot_stack.setCurrentIndex(index)

    def _calculate_plot_vertical_speed(self, current_altitude):
        if self.last_plot_altitude is None or self.last_plot_altitude_time is None:
            self.last_plot_altitude = current_altitude
            self.last_plot_altitude_time = time.time()
            return 0.0
        
        now = time.time()
        time_diff = now - self.last_plot_altitude_time
        
        if time_diff < 0.1:
            return getattr(self, 'last_calculated_plot_vs', 0.0)
            
        altitude_diff = current_altitude - self.last_plot_altitude
        vertical_speed = altitude_diff / time_diff
        
        self.last_plot_altitude = current_altitude
        self.last_plot_altitude_time = now
        self.last_calculated_plot_vs = vertical_speed
        return vertical_speed

    def update_plots_from_model(self):
        """Update plots with new data from telemetry_model."""
        data = self.telemetry_model.get_latest_telemetry()
        current_time_abs = time.time() - self.start_time
        
        self.time_data.append(current_time_abs)
        self.altitude_gps_data.append(data.get('gps_alt', float('nan')))
        self.altitude_baro_data.append(data.get('altitude', float('nan')))
        self.ground_speed_data.append(data.get('gps_speed', float('nan')))
        
        baro_alt_for_vs = data.get('altitude', None)
        if baro_alt_for_vs is not None:
            vs = self._calculate_plot_vertical_speed(baro_alt_for_vs)
            self.vertical_speed_data.append(vs)
        else:
            self.vertical_speed_data.append(float('nan'))

        self.temperature_data.append(data.get('temperature', float('nan')))
        self.pressure_data.append(data.get('pressure', float('nan')))
        self.rssi_data.append(data.get('rssi', float('nan')))
        self.snr_data.append(data.get('snr', float('nan')))

        # Limit data points
        max_points = self.settings_model.get('plot.max_points', 500) 
        for arr in [self.time_data, self.altitude_gps_data, self.altitude_baro_data, 
                    self.ground_speed_data, self.vertical_speed_data, self.temperature_data, 
                    self.pressure_data, self.rssi_data, self.snr_data]:
            if len(arr) > max_points:
                arr.pop(0)
        
        # Update Flight Data Page
        self.altitude_gps_curve_flight.setData(self.time_data, self.altitude_gps_data)
        self.altitude_baro_curve_flight.setData(self.time_data, self.altitude_baro_data)
        self.ground_speed_curve_flight.setData(self.time_data, self.ground_speed_data)
        self.vertical_speed_curve_flight.setData(self.time_data, self.vertical_speed_data)
        self.temp_curve_flight.setData(self.time_data, self.temperature_data)
        self.press_curve_flight.setData(self.time_data, self.pressure_data)

        # Update Signal Strength Page
        self.rssi_curve_signal.setData(self.time_data, self.rssi_data)
        self.snr_curve_signal.setData(self.time_data, self.snr_data)

        # Update All Plots Page
        self.altitude_gps_curve_all.setData(self.time_data, self.altitude_gps_data)
        self.altitude_baro_curve_all.setData(self.time_data, self.altitude_baro_data)
        self.ground_speed_curve_all.setData(self.time_data, self.ground_speed_data)
        self.vertical_speed_curve_all.setData(self.time_data, self.vertical_speed_data)
        self.rssi_curve_all.setData(self.time_data, self.rssi_data)
        self.snr_curve_all.setData(self.time_data, self.snr_data)
        self.temp_curve_all.setData(self.time_data, self.temperature_data)
        self.press_curve_all.setData(self.time_data, self.pressure_data)

    def update_plots(self):
        # This method was in gui.py, now replaced by update_plots_from_model
        # which is directly connected to the telemetry_model's data_updated signal.
        pass