from PyQt5.QtCore import QObject, pyqtSignal

class SettingsModel(QObject):
    """Model for managing application settings"""
    
    # Define signals
    settings_changed = pyqtSignal()
    
    def __init__(self, settings=None):
        super().__init__()
        
        if settings is None:
            settings = {}
        
        self.settings = settings
        
    def get(self, key, default=None):
        """Get a setting value by key with optional default"""
        # Support nested keys like 'serial.baud_rate'
        keys = key.split('.')
        value = self.settings
        
        for k in keys:
            if k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key, value):
        """Set a setting value and emit signal"""
        # Support nested keys like 'serial.baud_rate'
        keys = key.split('.')
        target = self.settings
        
        # Navigate to the proper nesting level
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        # Set the value
        target[keys[-1]] = value
        self.settings_changed.emit()