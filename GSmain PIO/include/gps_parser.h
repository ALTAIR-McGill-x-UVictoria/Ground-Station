#ifndef GPS_PARSER_H
#define GPS_PARSER_H

#include <Arduino.h>
#include <TinyGPSPlus.h>

struct GPSData {
    double latitude;   // Decimal degrees
    double longitude;  // Decimal degrees
    double altitude;   // Meters
    double hdop;      // Horizontal dilution of precision
    double vdop;      // Vertical dilution of precision
    unsigned long utc_unix; // UTC time as unix timestamp (seconds since epoch)
    bool valid;        // True if data is valid
    uint8_t satellites; // Number of satellites
    double speed_kmh;   // Speed in km/h
    double course;      // Course over ground in degrees
};

// Initialize the GPS parser
void initGPSParser();

// Process GPS data from Serial stream
// Call this in your main loop to feed GPS data to TinyGPSPlus
void processGPSData(Stream& gpsSerial);

// Get current GPS data
// Returns true if GPS data is valid and updated
bool getCurrentGPSData(GPSData& data);

// Check if GPS data has been updated since last call
bool isGPSDataUpdated();

#endif // GPS_PARSER_H
