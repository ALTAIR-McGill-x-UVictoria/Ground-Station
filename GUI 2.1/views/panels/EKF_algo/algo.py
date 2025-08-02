import numpy as np
import threading

class EKF:
    """Simple constant velocity Kalman filter for lat/lon/alt prediction."""
    def __init__(self):
        # state: [lat, lon, alt, v_lat, v_lon, v_alt]
        self.x = np.zeros(6)
        self.P = np.eye(6)
        self.last_time = None
        # process and measurement noise covariances
        self.Q_base = np.diag([1e-6, 1e-6, 1e-1, 1e-4, 1e-4, 1e-2])
        self.R = np.diag([1e-5, 1e-5, 1.0])
        self.lock = threading.Lock()

    def predict(self, dt):
        with self.lock:
            F = np.eye(6)
            F[0,3] = dt
            F[1,4] = dt
            F[2,5] = dt
            Q = self.Q_base * max(dt, 0)
            self.x = F @ self.x
            self.P = F @ self.P @ F.T + Q

    def update(self, measurement):
        with self.lock:
            z = np.array(measurement)
            H = np.zeros((3,6))
            H[0,0] = 1
            H[1,1] = 1
            H[2,2] = 1
            y = z - H @ self.x
            S = H @ self.P @ H.T + self.R
            K = self.P @ H.T @ np.linalg.inv(S)
            self.x = self.x + K @ y
            self.P = (np.eye(6) - K @ H) @ self.P

    def get_state(self):
        with self.lock:
            return self.x[:3].copy()