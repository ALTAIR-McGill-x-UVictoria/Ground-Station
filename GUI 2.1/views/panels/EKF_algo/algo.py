import numpy as np
import threading
import time


class EKF:
    """Simple constant velocity Kalman filter for lat/lon/alt prediction."""
    """Extended Kalman Filter using GPS position and acceleration data."""

    def __init__(self):
        # state: [lat, lon, alt, v_lat, v_lon, v_alt]
        self.x = np.zeros(6)
        self.P = np.eye(6)
        self.last_time = None
        self.last_accel = np.zeros(3)
        # process and measurement noise covariances
        self.Q_base = np.eye(6) * 100
        self.R = np.eye(3) * 0.01
        self.lock = threading.Lock()

    def _predict(self, x, P, dt, accel):
        F = np.eye(6)
        F[0, 3] = dt
        F[1, 4] = dt
        F[2, 5] = dt

        B = np.zeros((6, 3))
        B[0, 0] = 0.5 * dt ** 2
        B[1, 1] = 0.5 * dt ** 2
        B[2, 2] = 0.5 * dt ** 2
        B[3, 0] = dt
        B[4, 1] = dt
        B[5, 2] = dt

        Q = self.Q_base * max(dt, 0)
        x = F @ x + B @ accel
        P = F @ P @ F.T + Q
        return x, P

    def predict(self, dt, accel=None):
        """Propagate the state by dt seconds using acceleration input."""
        with self.lock:
            F = np.eye(6)
            F[0,3] = dt
            F[1,4] = dt
            F[2,5] = dt
            Q = self.Q_base * max(dt, 0)
            self.x = F @ self.x
            self.P = F @ self.P @ F.T + Q


    def update(self, lat, lon, alt, ax, ay, az):
        """Update filter with GPS position and acceleration."""
        with self.lock:
            now = time.time()
            if self.last_time is None:
                dt = 0.0
            else:
                dt = now - self.last_time
            self.last_time = now

            accel = np.array([ax, ay, az])
            self.last_accel = accel

            # Predict to current time using acceleration
            self.x, self.P = self._predict(self.x, self.P, dt, accel)

            # Measurement update with GPS position
            z = np.array([lat, lon, alt])
            H = np.zeros((3, 6))
            H[0, 0] = 1
            H[1, 1] = 1
            H[2, 2] = 1
            y = z - H @ self.x
            S = H @ self.P @ H.T + self.R
            K = self.P @ H.T @ np.linalg.inv(S)
            self.x = self.x + K @ y
            self.P = (np.eye(6) - K @ H) @ self.P

    def get_state(self, future_dt=0.0):
        """Return current state or predict a future state by future_dt seconds."""
        with self.lock:
            if future_dt > 0:
                x_future, _ = self._predict(self.x.copy(), self.P.copy(), future_dt, self.last_accel)
                return x_future[:3].copy()
            return self.x[:3].copy()