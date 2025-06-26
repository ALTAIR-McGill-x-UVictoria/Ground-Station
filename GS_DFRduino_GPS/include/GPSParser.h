#ifndef GPS_PARSER_H
#define GPS_PARSER_H

#include <Arduino.h>
#include <SoftwareSerial.h>
#include <TinyGPSPlus.h>  // Changed from TinyGPS++.h to TinyGPSPlus.h

// GPS pin definitions
#define GPS_RX 4  // Connect to TX of GPS module
#define GPS_TX 3  // Connect to RX of GPS module

class GPSParser {
public:
  GPSParser();
  void begin(long baudRate = 9600);
  void update();
  
  float getLat() const { return _latitude; }
  float getLon() const { return _longitude; }
  float getAlt() const { return _altitude; }
  float getSpeed() const { return _speed; }
  int getSats() const { return _satellites; }
  bool hasValidFix() const { return _hasValidFix; }
  
  // Print formatted GPS data to Serial
  void printData();
  
private:
  SoftwareSerial _gpsSerial;
  TinyGPSPlus _gps;  // Using TinyGPSPlus class
  
  float _latitude;
  float _longitude;
  float _altitude;
  float _speed;
  int _satellites;
  bool _hasValidFix;
};

#endif // GPS_PARSER_H