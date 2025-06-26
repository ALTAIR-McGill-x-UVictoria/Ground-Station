#include "gps_parser.h"
#include <TinyGPSPlus.h>
#include <time.h>

// TinyGPS++ object
TinyGPSPlus gps;

// Keep track of data updates
static bool dataUpdated = false;
static unsigned long lastUpdateTime = 0;

void initGPSParser() {
    dataUpdated = false;
    lastUpdateTime = 0;
}

void processGPSData(Stream& gpsSerial) {
    while (gpsSerial.available() > 0) {
        char c = gpsSerial.read();
        if (gps.encode(c)) {
            // Data was successfully encoded
            dataUpdated = true;
            lastUpdateTime = millis();
        }
    }
}

bool getCurrentGPSData(GPSData& data) {
    // Initialize data structure
    data.valid = false;
    data.latitude = 0.0;
    data.longitude = 0.0;
    data.altitude = 0.0;
    data.hdop = 0.0;
    data.vdop = 0.0;
    data.utc_unix = 0;
    data.satellites = 0;
    data.speed_kmh = 0.0;
    data.course = 0.0;
    
    // Check if we have valid location data
    if (gps.location.isValid()) {
        data.latitude = gps.location.lat();
        data.longitude = gps.location.lng();
        data.valid = true;
    }
    
    // Check if we have valid altitude data
    if (gps.altitude.isValid()) {
        data.altitude = gps.altitude.meters();
    }
    
    // Check if we have valid HDOP data
    if (gps.hdop.isValid()) {
        data.hdop = gps.hdop.hdop();
    }
    
    // Check if we have valid satellite count
    if (gps.satellites.isValid()) {
        data.satellites = gps.satellites.value();
    }
    
    // Check if we have valid speed data
    if (gps.speed.isValid()) {
        data.speed_kmh = gps.speed.kmph();
    }
    
    // Check if we have valid course data
    if (gps.course.isValid()) {
        data.course = gps.course.deg();
    }
    
    // Calculate UTC Unix timestamp if date and time are valid
    if (gps.date.isValid() && gps.time.isValid()) {
        struct tm timeinfo;
        timeinfo.tm_year = gps.date.year() - 1900;  // tm_year is years since 1900
        timeinfo.tm_mon = gps.date.month() - 1;     // tm_mon is 0-based
        timeinfo.tm_mday = gps.date.day();
        timeinfo.tm_hour = gps.time.hour();
        timeinfo.tm_min = gps.time.minute();
        timeinfo.tm_sec = gps.time.second();
        timeinfo.tm_isdst = 0;  // UTC time, no DST
        
        // Convert to Unix timestamp
        time_t timestamp = mktime(&timeinfo);
        if (timestamp != -1) {
            // mktime assumes local time, but we want UTC
            // For simplicity, we'll use the timestamp as-is
            // In a real implementation, you might want to adjust for timezone
            data.utc_unix = (unsigned long)timestamp;
        }
    }
    
    // TinyGPS++ doesn't provide VDOP directly, so we'll leave it as 0.0
    // Some GPS modules provide this in custom sentences
    data.vdop = 0.0;
    
    return data.valid;
}

bool isGPSDataUpdated() {
    bool wasUpdated = dataUpdated;
    dataUpdated = false;  // Reset the flag
    return wasUpdated;
}
