#include <Arduino.h>
//Ground Station Main

#include <ArduinoQueue.h>
#include <SPI.h>
#include <RH_RF95.h>
#include "gps_parser.h"

//Callsign
#define CALLSIGN "VA2ETD"
#define SHOW_CALLSIGN 0 //will show callsign in serial monitor

//Radio debugging without FC
#define DEBUG_RX 0
#define LOOP_TIMER 1000 

#define SERIALGPS Serial2
#define GPS_PRINT_INTERVAL 1000
//Queue
#define QUEUE_SIZE 10     // Choose one size value - removed duplicate definition

//Radio pin definitions
#define RFM95_RST 19
#define RFM95_CS 10
#define RFM95_INT 20

//LoRa parameters definitions
#define RF95_FREQ 915.0
#define SF 8
#define BW 125000
#define TX_POWER 20

// Function prototypes - Add these to resolve "not declared in scope" errors
void radioSetup();
void radioRx();
void recvCommand();
void parseData();
String commandParser();
void groundpacketParser(char* pkt, int enableRaw);
void printGPSPacket(GPSData& gpsData);

// Radio
RH_RF95 rf95(RFM95_CS, RFM95_INT);

// Basic Queue replacement
String queue[QUEUE_SIZE];
uint8_t queueHead = 0;
uint8_t queueTail = 0;

void enqueue(String s) {
  uint8_t next = (queueTail + 1) % QUEUE_SIZE;
  if (next != queueHead) {
    queue[queueTail] = s;
    queueTail = next;
  }
}

String dequeue() {
  if (queueHead == queueTail) return "GS:0,0.000";
  String s = queue[queueHead];
  queueHead = (queueHead + 1) % QUEUE_SIZE;
  return s;
}

bool queueIsEmpty() {
  return queueHead == queueTail;
}

unsigned long lastPacketTime = 0;
unsigned long sendTimer = 0;

char receivedChars[32];
char tempChars[32];
char messageFromPC[32] = {0};
int integerFromPC = 0;
float floatFromPC = 0.0;
boolean newData = false;
int showAsRawPacket = 1;
volatile int receptionConfirm = 0;
volatile int ignoreNextConfirm = 0;
String FcCommandID = "X";

// Global buffers instead of local stack allocation
uint8_t receiveBuf[RH_RF95_MAX_MESSAGE_LEN];
char parseBuf[RH_RF95_MAX_MESSAGE_LEN]; 
char txBuffer[64]; // Increased size for safety

// Use a single buffer for both RX and TX operations
uint8_t radioBuf[RH_RF95_MAX_MESSAGE_LEN];
uint8_t bufLen = 0;

unsigned long lastGpsPrint = 0;
GPSData gpsData;

void setup() {
  Serial.begin(115200);
  SERIALGPS.begin(9600);  // Initialize GPS serial at 9600 baud for ublox-6m
  delay(2000);
  pinMode(LED_BUILTIN, OUTPUT);
  
  // Initialize GPS parser
  initGPSParser();
  
  radioSetup();
  Serial.println("System init complete");
  Serial.println("GPS initialized on Serial2");
  
  lastGpsPrint = millis();
}

void loop() {
  // Process GPS data from Serial2 using TinyGPS++
  processGPSData(SERIALGPS);
  
  // Update GPS data structure if new data is available
  if (isGPSDataUpdated()) {
    getCurrentGPSData(gpsData);
  }

  // Print GPS data every GPS_PRINT_INTERVAL ms if valid
  if (millis() - lastGpsPrint >= GPS_PRINT_INTERVAL) {
    printGPSPacket(gpsData);
    lastGpsPrint = millis();
  } 

  if (DEBUG_RX && millis() - sendTimer > LOOP_TIMER) {
    recvCommand();
    String commandPacket = commandParser();
    radioRx();
    sendTimer = millis();
  } else {
    recvCommand();
    String commandPacket = commandParser();
    radioRx();
  }
}

void radioSetup() {

  SPI.begin();
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH);
  delay(100);
  digitalWrite(RFM95_RST, LOW);
  delay(10);
  digitalWrite(RFM95_RST, HIGH);
  delay(10);

  // Read registers for debug
  uint8_t modemConfig1 = rf95.spiRead(0x1D); // REG_MODEM_CONFIG1
  uint8_t modemConfig2 = rf95.spiRead(0x1E); // REG_MODEM_CONFIG2
  uint8_t modemConfig3 = rf95.spiRead(0x26); // REG_MODEM_CONFIG3

  Serial.print("ModemConfig1: 0x"); Serial.println(modemConfig1, HEX);
  Serial.print("ModemConfig2: 0x"); Serial.println(modemConfig2, HEX);
  Serial.print("ModemConfig3: 0x"); Serial.println(modemConfig3, HEX);

  if (!rf95.init()) {
    Serial.println("LoRa radio init failed");
    while (1);
  }
  Serial.println("LoRa radio init OK!");

  if (!rf95.setFrequency(RF95_FREQ)) {
    Serial.println("setFrequency failed");
    while (1);
  }
  rf95.setSignalBandwidth(BW);
  rf95.setSpreadingFactor(SF);
  rf95.setTxPower(TX_POWER, false);
  rf95.setCodingRate4(5);
  rf95.setPayloadCRC(true);
}

void radioRx() {
  if (rf95.available() || DEBUG_RX) {
    // Clear buffer before receiving new data
    memset(radioBuf, 0, sizeof(radioBuf));
    
    // Receive data into our single buffer
    bufLen = sizeof(radioBuf);
    if (rf95.recv(radioBuf, &bufLen) || DEBUG_RX) {
      digitalWrite(LED_BUILTIN, HIGH);
      
      unsigned long currentTime = millis();
      unsigned long deltaT = currentTime - lastPacketTime;
      lastPacketTime = currentTime;
      
      // Ensure the buffer is null-terminated for string operations
      if (bufLen < sizeof(radioBuf)) {
        radioBuf[bufLen] = '\0';
      }
      
      // Process received data (use radioBuf as char* for parsing)
      groundpacketParser((char*)radioBuf, showAsRawPacket);
      

      Serial.print("GS:");
      Serial.print(rf95.lastRssi(), DEC);
      Serial.print(",");
      Serial.print(rf95.lastSNR(), DEC);
      Serial.print(",");
      Serial.println(deltaT);

       // Get response data
      String data = queueIsEmpty() ? "0,0.000" : dequeue();
      
      // Copy formatted string to buffer
      memcpy(radioBuf, data.c_str(), bufLen);
      
      // For debug - print what we're sending
      Serial.print("Sending packet: ");
      Serial.println((char*)radioBuf);
      
      // Send the data
      rf95.send(radioBuf, bufLen);
      rf95.waitPacketSent();
      rf95.setModeRx();
      
      
      
      digitalWrite(LED_BUILTIN, LOW);
    }
  }
}

void recvCommand() {
  static byte ndx = 0;
  char endMarker = '\n';
  char rc;

  while (Serial.available() > 0 && newData == false) {
    rc = Serial.read();
    if (rc != endMarker) {
      receivedChars[ndx++] = rc;
      if (ndx >= sizeof(receivedChars) - 1) ndx = sizeof(receivedChars) - 1;
    } else {
      receivedChars[ndx] = '\0';
      ndx = 0;
      newData = true;
    }
  }
}

void parseData() {
  char *strtokIndx = strtok(tempChars, " ");
  if (strtokIndx) strcpy(messageFromPC, strtokIndx);

  strtokIndx = strtok(NULL, " ");
  if (strtokIndx) floatFromPC = atof(strtokIndx);

  strtokIndx = strtok(NULL, " ");
  if (strtokIndx) integerFromPC = atoi(strtokIndx);
}

String commandParser() {
  if (newData) {
    strcpy(tempChars, receivedChars);
    parseData();
    String dat = "GS:";

    if (strcmp(messageFromPC, "ping") == 0) {
      dat = dat + "1,000.00";
    } else if (strcmp(messageFromPC, "led1") == 0) {
      dat = "2," + String(fmodf(floatFromPC, 100.0));
    } else if (strcmp(messageFromPC, "clearq") == 0) {
      while (!queueIsEmpty()) dequeue();
      Serial.println("Cleared queue");
    } else {
      dat = "0,000.00";
      Serial.print("Invalid command: ");
      Serial.println(messageFromPC);
    }

    enqueue(dat);
    newData = false;
    floatFromPC = 0.0;
    strcpy(receivedChars, "0");
    return dat;
  }
  return "";
}

// This function is destructively modifying buf with strtok()
void groundpacketParser(char* pkt, int enableRaw) {
  if (enableRaw) {
    Serial.print("FC:");
    // Print only valid printable characters
    int i = 0;
    bool foundValidData = false;
    
    // First, find the valid comma-separated data
    while (pkt[i] != '\0' && i < 200) {  // Limit to reasonable packet size
      // Only print ASCII printable chars and basic control chars
      char c = pkt[i];
      if ((c >= 32 && c <= 126) || c == '\r' || c == '\n' || c == '\t' || c == ',') {
        Serial.print(c);
        foundValidData = true;
      } else {
        if (foundValidData) {
          // Stop printing once we hit non-printable chars after valid data
          break;
        }
      }
      i++;
    }
    Serial.println(); // End the line
    return;
  }

  // Original parsing code for non-raw format remains unchanged
  char *token = strtok(pkt, ":,");
  int index = 0;
  while (token != NULL) {
    Serial.print(index == 0 ? "CMD ID: " : ", ");
    Serial.print(token);
    token = strtok(NULL, ",");
    index++;
  }
  Serial.println();
}

void printGPSPacket(GPSData &gpsData) {
  if (gpsData.valid) {
    char gpsBuf[200];
    sprintf(gpsBuf, "GPS:%.6f,%.6f,%.2f,%.2f,%.2f,%lu,%d,%.2f,%.2f",
            gpsData.latitude, gpsData.longitude, gpsData.altitude,
            gpsData.hdop, gpsData.vdop, gpsData.utc_unix, 
            gpsData.satellites, gpsData.speed_kmh, gpsData.course);
    Serial.println(gpsBuf);
  } else {
    Serial.println("GPS: No valid data");
  }
}

