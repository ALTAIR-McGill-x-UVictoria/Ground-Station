import numpy as np
import threading
import time


class EKF:
    """Simple constant velocity Kalman filter for lat/lon/alt prediction."""
    """Estimate position and velocity from GPS and predict 5 seconds ahead."""

    def __init__(self):
        # state: [lat, lon, alt, v_lat, v_lon, v_alt]
        self.x = np.zeros(6)

        self.lock = threading.Lock()
        self.last_time = None
        self.last_meas = None

    def update(self, measurement):
        """Update state with a new GPS measurement and recompute velocity."""
        with self.lock:

            z = np.array(measurement, dtype=float)
            now = time.time()
            if self.last_meas is not None and self.last_time is not None:
                dt = now - self.last_time
                if dt > 0:
                    self.x[3:] = (z - self.last_meas) / dt
            self.x[:3] = z
            self.last_meas = z
            self.last_time = now

    def predict(self, dt):
        """Propagate the state forward by dt seconds."""
        with self.lock:

            self.x[:3] += self.x[3:] * dt

    def get_state(self, future_seconds: float = 5.0):
        """Return predicted [lat, lon, alt] after future_seconds."""
        with self.lock:
            return (self.x[:3] + self.x[3:] * future_seconds).copy()