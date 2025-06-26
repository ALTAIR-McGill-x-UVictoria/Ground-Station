#include "../include/GPSParser.h"

GPSParser::GPSParser() : 
  _gpsSerial(GPS_RX, GPS_TX),
  _latitude(0.0), 
  _longitude(0.0), 
  _altitude(0.0),
  _speed(0.0),
  _satellites(0),
  _hasValidFix(false) {
}

void GPSParser::begin(long baudRate) {
  _gpsSerial.begin(baudRate);
  Serial.println("GPS parser initialized");
}

void GPSParser::update() {
  // Process all available GPS data
  while (_gpsSerial.available() > 0) {
    // Use TinyGPSPlus to parse NMEA sentences
    if (_gps.encode(_gpsSerial.read())) {
      // Update location data if valid
      if (_gps.location.isValid()) {
        _latitude = _gps.location.lat();
        _longitude = _gps.location.lng();
        _hasValidFix = true;
      } else {
        _hasValidFix = false;
      }
      
      // Update altitude if valid
      if (_gps.altitude.isValid()) {
        _altitude = _gps.altitude.meters();
      }
      
      // Update speed if valid
      if (_gps.speed.isValid()) {
        _speed = _gps.speed.kmph();
      }
      
      // Update satellites count if valid
      if (_gps.satellites.isValid()) {
        _satellites = _gps.satellites.value();
      }
    }
  }
  
  // Check for GPS timeout - no valid data for 5 seconds
  if (millis() > 5000 && _gps.charsProcessed() < 10) {
    Serial.println("Warning: No GPS data detected. Check wiring.");
  }
}

void GPSParser::printData() {
  Serial.print("GPS: ");
  
  if (_hasValidFix) {
    Serial.print("Fix acquired | ");
    Serial.print("Lat: "); 
    Serial.print(_latitude, 6);
    Serial.print(" | Lon: "); 
    Serial.print(_longitude, 6);
    Serial.print(" | Alt: "); 
    Serial.print(_altitude, 1);
    Serial.print("m | Sats: "); 
    Serial.print(_satellites);
    Serial.print(" | Speed: ");
    Serial.print(_speed, 1);
    Serial.println("km/h");
  } else {
    Serial.println("No fix");
  }
}