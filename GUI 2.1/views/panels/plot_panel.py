from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
    QStackedWidget, QGridLayout, QLabel, QFrame
)
from PyQt5.QtCore import Qt
import pyqtgraph as pg

class PlotPanel(QWidget):
    """Panel for displaying telemetry data plots"""
    
    def __init__(self, telemetry_model, settings_model, parent=None):
        super().__init__(parent)
        self.telemetry_model = telemetry_model
        self.settings_model = settings_model
        
        # Set plot style defaults
        pg.setConfigOptions(antialias=True)
        
        # Create UI components
        self.setup_ui()
        
        # Connect to model signals
        self.telemetry_model.data_updated.connect(self.update_plots)
    
    def setup_ui(self):
        """Set up the plot panel UI"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add plot selector
        plot_selector = QComboBox()
        plot_selector.addItems([
            "Flight Data",
            "Signal Strength",
            "All Plots"
        ])
        plot_selector.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                min-width: 150px;
            }
        """)
        plot_selector.currentIndexChanged.connect(self.switch_plot_view)
        layout.addWidget(plot_selector)
        
        # Create stacked widget for different plot pages
        self.plot_stack = QStackedWidget()
        layout.addWidget(self.plot_stack, 1)  # 1 = stretch factor
        
        # Flight Data page (GPS altitude, speeds, temp, pressure)
        self.create_flight_data_page()
        
        # Signal Strength page
        self.create_signal_strength_page()
        
        # All Plots page
        self.create_all_plots_page()
    
    def create_flight_data_page(self):
        """Create page with flight data plots"""
        flight_page = QWidget()
        flight_layout = QGridLayout(flight_page)
        
        # GPS Altitude plot (top left)
        self.altitude_plot = pg.PlotWidget(title="Altitude")
        self.altitude_plot.setLabel('left', 'Altitude', units='m')
        self.altitude_plot.setLabel('bottom', 'Time', units='s')
        self.altitude_plot.showGrid(x=True, y=True)
        self.altitude_plot.addLegend()
        flight_layout.addWidget(self.altitude_plot, 0, 0)
        
        # Initialize altitude curves
        self.altitude_gps_curve = self.altitude_plot.plot(pen='g', name='GPS Altitude')
        self.altitude_baro_curve = self.altitude_plot.plot(pen='y', name='Baro Altitude')
        
        # Speed plot (top right)
        self.speed_plot = pg.PlotWidget(title="Speed")
        self.speed_plot.setLabel('left', 'Speed', units='m/s')
        self.speed_plot.setLabel('bottom', 'Time', units='s')
        self.speed_plot.showGrid(x=True, y=True)
        self.speed_plot.addLegend()
        flight_layout.addWidget(self.speed_plot, 0, 1)
        
        # Initialize speed curves
        self.speed_h_curve = self.speed_plot.plot(
            pen=pg.mkPen(color='y', width=2), name='Ground Speed')
        self.speed_v_curve = self.speed_plot.plot(
            pen=pg.mkPen(color='c', width=2), name='Vertical Speed')
        
        # Temperature plot (bottom left)
        self.temp_plot = pg.PlotWidget(title="Temperature")
        self.temp_plot.setLabel('left', 'Temperature', units='°C')
        self.temp_plot.setLabel('bottom', 'Time', units='s')
        self.temp_plot.showGrid(x=True, y=True)
        flight_layout.addWidget(self.temp_plot, 1, 0)
        
        # Initialize temperature curve
        self.temp_curve = self.temp_plot.plot(pen=pg.mkPen(color='r', width=2))
        
        # Pressure plot (bottom right)
        self.press_plot = pg.PlotWidget(title="Pressure")
        self.press_plot.setLabel('left', 'Pressure', units='hPa')
        self.press_plot.setLabel('bottom', 'Time', units='s')
        self.press_plot.showGrid(x=True, y=True)
        flight_layout.addWidget(self.press_plot, 1, 1)
        
        # Initialize pressure curve
        self.press_curve = self.press_plot.plot(pen=pg.mkPen(color='b', width=2))
        
        # Add page to stack
        self.plot_stack.addWidget(flight_page)
    
    def create_signal_strength_page(self):
        """Create page with signal strength plots"""
        signal_page = QWidget()
        signal_layout = QGridLayout(signal_page)
        
        # RSSI Plot
        self.rssi_plot = pg.PlotWidget(title="RSSI")
        self.rssi_plot.setLabel('left', 'RSSI', units='dBm')
        self.rssi_plot.setLabel('bottom', 'Time', units='s')
        self.rssi_plot.showGrid(x=True, y=True)
        signal_layout.addWidget(self.rssi_plot, 0, 0)
        
        # Initialize RSSI curve
        self.rssi_curve = self.rssi_plot.plot(pen=pg.mkPen(color='r', width=2))
        
        # SNR Plot
        self.snr_plot = pg.PlotWidget(title="SNR")
        self.snr_plot.setLabel('left', 'SNR', units='dB')
        self.snr_plot.setLabel('bottom', 'Time', units='s')
        self.snr_plot.showGrid(x=True, y=True)
        signal_layout.addWidget(self.snr_plot, 1, 0)
        
        # Initialize SNR curve
        self.snr_curve = self.snr_plot.plot(pen=pg.mkPen(color='b', width=2))
        
        # Add page to stack
        self.plot_stack.addWidget(signal_page)
    
    def create_all_plots_page(self):
        """Create page with all plots combined"""
        all_plots_page = QWidget()
        all_layout = QGridLayout(all_plots_page)
        
        # Altitude plot (top left)
        altitude_plot_all = pg.PlotWidget(title="Altitude")
        altitude_plot_all.setLabel('left', 'Altitude', units='m')
        altitude_plot_all.setLabel('bottom', 'Time', units='s')
        altitude_plot_all.showGrid(x=True, y=True)
        all_layout.addWidget(altitude_plot_all, 0, 0)
        
        # Speed plot (top right)
        speed_plot_all = pg.PlotWidget(title="Speed")
        speed_plot_all.setLabel('left', 'Speed', units='m/s')
        speed_plot_all.setLabel('bottom', 'Time', units='s')
        speed_plot_all.showGrid(x=True, y=True)
        speed_plot_all.addLegend()
        all_layout.addWidget(speed_plot_all, 0, 1)
        
        # Signal plot (bottom left)
        signal_plot_all = pg.PlotWidget(title="Signal Strength")
        signal_plot_all.setLabel('left', 'Level')
        signal_plot_all.setLabel('bottom', 'Time', units='s')
        signal_plot_all.showGrid(x=True, y=True)
        signal_plot_all.addLegend()
        all_layout.addWidget(signal_plot_all, 1, 0)
        
        # Temperature & Pressure plot (bottom right)
        temp_press_plot_all = pg.PlotWidget(title="Temperature & Pressure")
        temp_press_plot_all.setLabel('left', 'Temperature', units='°C')
        temp_press_plot_all.setLabel('right', 'Pressure', units='hPa')
        temp_press_plot_all.setLabel('bottom', 'Time', units='s')
        temp_press_plot_all.showGrid(x=True, y=True)
        temp_press_plot_all.addLegend()
        all_layout.addWidget(temp_press_plot_all, 1, 1)
        
        # Initialize curves for the all plots view
        self.altitude_curve_all = altitude_plot_all.plot(pen=pg.mkPen(color='g', width=2))
        
        self.speed_h_curve_all = speed_plot_all.plot(
            pen=pg.mkPen(color='y', width=2), name='Ground Speed')
        self.speed_v_curve_all = speed_plot_all.plot(
            pen=pg.mkPen(color='c', width=2), name='Vertical Speed')
        
        self.rssi_curve_all = signal_plot_all.plot(
            pen=pg.mkPen(color='r', width=2), name='RSSI')
        self.snr_curve_all = signal_plot_all.plot(
            pen=pg.mkPen(color='b', width=2), name='SNR')
        
        self.temp_curve_all = temp_press_plot_all.plot(
            pen=pg.mkPen(color='r', width=2), name='Temperature')
        self.press_curve_all = temp_press_plot_all.plot(
            pen=pg.mkPen(color='b', width=2), name='Pressure')
        
        # Add page to stack
        self.plot_stack.addWidget(all_plots_page)
    
    def switch_plot_view(self, index):
        """Switch between different plot views"""
        self.plot_stack.setCurrentIndex(index)
    
    def update_plots(self):
        """Update all plots with data from the telemetry model"""
        try:
            # Flight data plots
            self.altitude_curve.setData(self.telemetry_model.telemetry_time_data, 
                                       self.telemetry_model.altitude_data)
            self.temp_curve.setData(self.telemetry_model.telemetry_time_data, 
                                   self.telemetry_model.temperature_data)
            self.press_curve.setData(self.telemetry_model.telemetry_time_data, 
                                    self.telemetry_model.pressure_data)
            
            # Speed plots
            self.speed_h_curve.setData(self.telemetry_model.telemetry_time_data, 
                                      self.telemetry_model.ground_speed_data)
            
            if hasattr(self.telemetry_model, 'vertical_speed_data') and len(self.telemetry_model.vertical_speed_data) > 0:
                self.speed_v_curve.setData(
                    self.telemetry_model.telemetry_time_data[-len(self.telemetry_model.vertical_speed_data):],
                    self.telemetry_model.vertical_speed_data
                )
            
            # Signal strength plots
            self.rssi_curve.setData(self.telemetry_model.signal_time_data, 
                                   self.telemetry_model.rssi_data)
            self.snr_curve.setData(self.telemetry_model.signal_time_data, 
                                  self.telemetry_model.snr_data)
            
            # "All plots" view
            self.altitude_curve_all.setData(self.telemetry_model.telemetry_time_data, 
                                          self.telemetry_model.altitude_data)
            self.temp_curve_all.setData(self.telemetry_model.telemetry_time_data, 
                                       self.telemetry_model.temperature_data)
            self.press_curve_all.setData(self.telemetry_model.telemetry_time_data, 
                                        self.telemetry_model.pressure_data)
            self.speed_h_curve_all.setData(self.telemetry_model.telemetry_time_data, 
                                          self.telemetry_model.ground_speed_data)
            self.rssi_curve_all.setData(self.telemetry_model.signal_time_data, 
                                       self.telemetry_model.rssi_data)
            self.snr_curve_all.setData(self.telemetry_model.signal_time_data, 
                                      self.telemetry_model.snr_data)
            
            if hasattr(self.telemetry_model, 'vertical_speed_data') and len(self.telemetry_model.vertical_speed_data) > 0:
                self.speed_v_curve_all.setData(
                    self.telemetry_model.telemetry_time_data[-len(self.telemetry_model.vertical_speed_data):],
                    self.telemetry_model.vertical_speed_data
                )
                
        except Exception as e:
            print(f"Error updating plots: {str(e)}")