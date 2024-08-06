//Ground Station Main


// #include <RadioLib.h>
#include <ArduinoQueue.h>
#include "Waveshare_10Dof-D.h"
#include "RadioLogic.h"
#include <SPI.h>
#include <RH_RF95.h>
#include "Waveshare_10Dof-D.h"

//Callsign
#define CALLSIGN "VA2ETD"
#define SHOW_CALLSIGN 0 //will show callsign in serial monitor

//Radio debugging without FC
#define DEBUG_RX 0
#define LOOP_TIMER 500

//Queue
#define QUEUE_SIZE 10

//Radio pin definitions
//Radio #1
#define RFM96_RST 5
#define RFM96_CS 10
#define RFM96_INT 4
//Radio #2
#define RFM95_RST 7
#define RFM95_CS 37
#define RFM95_INT 6

//LoRa parameters definitions
#define RF96_FREQ 433.0 //Rx
#define RF95_FREQ 903.0 //Tx
#define SF 8
#define BW 125000
#define TX_POWER 20

//Functionality enable definitions
#define SHOW_AS_RAW_PACKET 1
#define RX_ENABLE 1
#define TX_ENABLE 0



// Singleton instances
RH_RF95 rf95(RFM95_CS, RFM95_INT);
RH_RF95 rf96(RFM96_CS, RFM96_INT);

ArduinoQueue<String> queue(QUEUE_SIZE);

IMU_ST_ANGLES_DATA stAngles;
IMU_ST_SENSOR_DATA stGyroRawData;
IMU_ST_SENSOR_DATA stAccelRawData;
IMU_ST_SENSOR_DATA stMagnRawData;
int32_t s32PressureVal = 0, s32TemperatureVal = 0, s32AltitudeVal = 0;

//Command parser variables
const byte numChars = 32;
char receivedChars[numChars];
char tempChars[numChars];        // temporary array for use by strtok() function

      // variables to hold the parsed data
char messageFromPC[numChars] = {0};
int integerFromPC = 0;
float floatFromPC = 0.0;

String commandPacket;

boolean newData = false;

elapsedMillis sendTimer;

void setup() {

  Serial.begin(115200);
  while (!Serial && (millis() < 3000));

  #if TX_ENABLE
  radio903Setup();
  #endif

  #if RX_ENABLE
  radio433Setup();
  #endif

  Serial.println("System init complete");

  
}

void loop() {  

  recvCommand();
  commandPacket = commandParser();
  
  if(sendTimer>= LOOP_TIMER){

    if(TX_ENABLE){      
      radioTxDuplex(commandPacket.c_str());
    }

    

    sendTimer = 0;
  }

  if(RX_ENABLE){
    radioRxDuplex();
  }

}




void radioSetup(){
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH);

  // Serial.begin(115200);
  while (!Serial) delay(1);
  delay(100);

  // manual reset
  digitalWrite(RFM95_RST, LOW);
  delay(10);
  digitalWrite(RFM95_RST, HIGH);
  delay(10);

  while (!rf95.init()) {
    Serial.println("LoRa radio init failed");
    while (1);
  }
  Serial.println("LoRa radio init OK!");

  // Defaults after init are 434.0MHz, modulation GFSK_Rb250Fd250, +13dbM
  if (!rf95.setFrequency(RF95_FREQ)) {
    Serial.println("setFrequency failed");
    while (1);
  }
  Serial.print("Set Freq to: "); Serial.println(RF95_FREQ);

  // Defaults after init are 434.0MHz, 13dBm, Bw = 125 kHz, Cr = 4/5, Sf = 128chips/symbol, CRC on

  // The default transmitter power is 13dBm, using PA_BOOST.
  // If you are using RFM95/96/97/98 modules which uses the PA_BOOST transmitter pin, then
  // you can set transmitter powers from 5 to 23 dBm:
  rf95.setSignalBandwidth(BW);
  // rf95.setCodingRate4(5);
  rf95.setSpreadingFactor(SF);
  rf95.setTxPower(TX_POWER, false);


}

void radio903Setup(){
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH);

  // Serial.begin(115200);
  // while (!Serial) delay(1);
  // delay(100);

  // Serial.println("Feather LoRa TX Test!");

  // manual reset
  digitalWrite(RFM95_RST, LOW);
  delay(10);
  digitalWrite(RFM95_RST, HIGH);
  delay(10);

  while (!rf95.init()) {
    Serial.println("LoRa radio init failed");
    // Serial.println("Uncomment '#define SERIAL_DEBUG' in RH_RF95.cpp for detailed debug info");
    while (1);
  }
  // Serial.println("LoRa radio init OK!");

  // Defaults after init are 434.0MHz, modulation GFSK_Rb250Fd250, +13dbM
  if (!rf95.setFrequency(RF95_FREQ)) {
    Serial.println("setFrequency failed");
    while (1);
  }

  Serial.print("Set Rx to: "); Serial.println(RF95_FREQ);

  rf95.setSignalBandwidth(BW);
  rf95.setSpreadingFactor(SF);
  rf95.setTxPower(TX_POWER, false);
  rf95.
}

void radio433Setup(){
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH);

  // Serial.begin(115200);
  // while (!Serial) delay(1);
  // delay(100);

  // Serial.println("Feather LoRa TX Test!");

  // manual reset
  digitalWrite(RFM96_RST, LOW);
  delay(10);
  digitalWrite(RFM96_RST, HIGH);
  delay(10);

  while (!rf96.init()) {
    Serial.println("LoRa radio init failed");
    // Serial.println("Uncomment '#define SERIAL_DEBUG' in RH_RF95.cpp for detailed debug info");
    while (1);
  }
  // Serial.println("LoRa radio init OK!");

  // Defaults after init are 434.0MHz, modulation GFSK_Rb250Fd250, +13dbM
  if (!rf95.setFrequency(RF96_FREQ)) {
    Serial.println("setFrequency failed");
    while (1);
  }


  Serial.print("Set Rx to: "); Serial.println(RF96_FREQ);

  rf96.setSignalBandwidth(BW);
  rf96.setSpreadingFactor(SF);
  rf96.setTxPower(TX_POWER, false);
}

void radioTxDuplex(char radiopacket[100]){
  rf95.send((uint8_t *)radiopacket, 100);
  rf95.waitPacketSent();
}

void radioRxDuplex(){
  if (rf96.available()){

    uint8_t buf[RH_RF95_MAX_MESSAGE_LEN];
    uint8_t len = sizeof(buf);

    if(rf96.recv(buf, &len)){
      digitalWrite(LED_BUILTIN, HIGH);
      Serial.println((char*)buf);
      Serial.print("RSSI: ");
      Serial.print(rf95.lastRssi(), DEC);
      Serial.print(", SNR: ");
      Serial.println(rf95.lastSNR(), DEC);
      
    }
    
  }
}

void radioRx(){
  if (rf95.available() || DEBUG_RX) {
    // Should be a message for us now
    uint8_t buf[RH_RF95_MAX_MESSAGE_LEN];
    // uint8_t len = sizeof(buf);

    if(DEBUG_RX){
      char debugMessage[] = "DEBUG PACKET";
      strcpy(buf, debugMessage);
    }

    uint8_t len = sizeof(buf);

    if (rf95.recv(buf, &len) || DEBUG_RX) {
      digitalWrite(LED_BUILTIN, HIGH);
      // RH_RF95::printBuffer("Received: ", buf, len);

      if(SHOW_AS_RAW_PACKET == 1){
        Serial.println((char*)buf);
      } else{
        groundpacketParser((char*) buf);
      }
      Serial.print("RSSI: ");
      Serial.print(rf95.lastRssi(), DEC);
      Serial.print(", SNR: ");
      Serial.println(rf95.lastSNR(), DEC);
    }

     // Send a reply
    String data;
    // byte data;

    if(queue.isEmpty() != 1){
    data = queue.dequeue();
    } else {data = "0,000.00";}
    String callsgn = CALLSIGN;
    data = callsgn + ":" + data;
    const char* tosend = data.c_str();
    rf95.send((uint8_t *)tosend, 30);
    rf95.waitPacketSent();
    // Serial.println("Sent a reply");
    digitalWrite(LED_BUILTIN, LOW);
    } 
  else {
    // Serial.println("Receive failed");
  }
  

}

void recvCommand() {
    static boolean recvInProgress = false;
    static byte ndx = 0;
    char endMarker = '\n';
    char rc;


    while (Serial.available() > 0 && newData == false) {
      rc = Serial.read();

      if (rc != endMarker) {
        receivedChars[ndx] = rc;
        ndx++;
        if (ndx >= numChars) {
          ndx = numChars - 1;
        }
      }
      else {
        receivedChars[ndx] = '\0'; // terminate the string
        recvInProgress = false;
        ndx = 0;
        newData = true;
      }
  }
}

//============

void parseData() {

  // split the data into its parts
    char * strtokIndx; // this is used by strtok() as an index

    strtokIndx = strtok(tempChars," ");      // get the first part - the string
    // Serial.print(strtokIndx); Serial.print("-"); Serial.println(strtokIndx != NULL);
    if(NULL != strtokIndx)
    {
      strcpy(messageFromPC, strtokIndx);

    }

    strtokIndx = strtok(NULL, " "); // this continues where the previous call left off
    
    if(NULL != strtokIndx)
    {
      floatFromPC = atof(strtokIndx);     // convert this part to an integer
    }

    strtokIndx = strtok(NULL, " ");
    if(NULL != strtokIndx)
    {
    integerFromPC = atoi(strtokIndx);   // convert this part to an integer
    }
    
}

//============


String commandParser(){
  if (newData == true) { 
        strcpy(tempChars, receivedChars);

        parseData();

        String dat = "0,000.00";

        if(strcmp(messageFromPC,"0") == 0){
          dat = "0,000.00";
          //no message
        }
        else if(strcmp(messageFromPC,"ping") == 0){
          // code = 1;
          dat = "1,000.00";
          queue.enqueue(dat);
          Serial.print(dat); Serial.print(": ");
          Serial.println("pong");
          
        }
        else if(strcmp(messageFromPC,"led1") == 0){
          // code = 2;
          floatFromPC = fmodf(floatFromPC, 100.00f);
          dat = "2," + (String) floatFromPC;
          queue.enqueue(dat);
          dat.c_str();
          Serial.print(dat); Serial.print(": ");
          Serial.print("LED 1 on, intensity: "); Serial.println(floatFromPC);
          
        }
        else if(strcmp(messageFromPC,"led2") == 0){
          // code = 2;
          floatFromPC = fmodf(floatFromPC, 100.00f);
          dat = "3," + (String) floatFromPC;
          queue.enqueue(dat);
          dat.c_str();
          Serial.print(dat); Serial.print(": ");
          Serial.print("LED 2 on, intensity: "); Serial.println(floatFromPC);
          
        }
        else if(strcmp(messageFromPC,"led3") == 0){
          // code = 2;
          floatFromPC = fmodf(floatFromPC, 100.00f);
          dat = "4," + (String) floatFromPC;
          queue.enqueue(dat);
          dat.c_str();
          Serial.print(dat); Serial.print(": ");
          Serial.print("LED 3 on, intensity: "); Serial.println(floatFromPC);
          
        }
        else if(strcmp(messageFromPC,"ledoff") == 0){
          // code = 3;
          dat = "5,000.00";
          queue.enqueue(dat);
          Serial.print(dat); Serial.print(": ");
          Serial.println("LED off");
          
        }
        else if(strcmp(messageFromPC,"dangle") == 0){
          // code = 4;
          floatFromPC = abs(fmodf(floatFromPC, 360.0f));
          dat = "6," + (String) floatFromPC;
          queue.enqueue(dat);
          Serial.print(dat); Serial.print(": ");
          Serial.print("Set driver angle to: "); Serial.println(floatFromPC);
          
        }
        else if(strcmp(messageFromPC,"sdwrite") == 0){
          // code = 5;
          dat = "7,000.00";
          queue.enqueue(dat);
          Serial.print(dat); Serial.print(": ");
          Serial.println("Start DAQ write to SD");
          
        }
        else if(strcmp(messageFromPC,"sdstop") == 0){
          // code = 6;
          dat = "8,000.00";
          queue.enqueue(dat);
          Serial.print(dat); Serial.print(": ");
          Serial.println("Stopped DAQ write to SD");
          
        }
        else if(strcmp(messageFromPC,"sdclear") == 0){
          // code = 6;
          dat = "9,000.00";
          queue.enqueue(dat);
          Serial.print(dat); Serial.print(": ");
          Serial.println("Deleted datalog.txt");
          
        }
        else if(strcmp(messageFromPC,"ledblink") == 0){
          // code = 6;
          dat = "10," + (String) floatFromPC;
          queue.enqueue(dat);
          Serial.print(dat); Serial.print(": ");
          Serial.print("LED blinking set for "); Serial.print(floatFromPC); Serial.println(" ms");
          
        }
        else if(strcmp(messageFromPC,"ledbright") == 0){
          // code = 11;
          dat = "11," + (String) floatFromPC;
          queue.enqueue(dat);
          Serial.print(dat); Serial.print(": ");
          Serial.print("LED brightness set for "); Serial.print(floatFromPC); Serial.println("%");
          
        }
        else if(strcmp(messageFromPC,"togglelong") == 0){
          // code = 11;
          dat = "12," + (String) floatFromPC;
          queue.enqueue(dat);
          Serial.print(dat); Serial.print(": ");
          Serial.println("Toggled long packet format");
          
        }

        else {
          String dat = "0,000.00";
          queue.enqueue(dat);
          Serial.print(dat); Serial.print(": ");
          Serial.print("Error: "); Serial.print(messageFromPC); Serial.println(" is not a valid command");
          
        }
        strcpy(receivedChars,"0");
        floatFromPC = 0.0;

        newData = false;
        return dat;
        
    }

}

void groundpacketParser(char* receivedPacket){

  char * strtokIndx; // this is used by strtok() as an index

  strtokIndx = strtok(receivedPacket,":");

  #if SHOW_CALLSIGN
  if(NULL != strtokIndx)
  {
    Serial.print(strtokIndx); Serial.print(": ");
  }
  #endif

  strtokIndx = strtok(NULL, ",");

  if(NULL != strtokIndx)
  {
    Serial.print("Pong: "); Serial.print(strtokIndx);
  }

  strtokIndx = strtok(NULL, ",");

  if(NULL != strtokIndx)
  {
    Serial.print(", Battery Voltage:"); Serial.print(strtokIndx);
  }

  strtokIndx = strtok(NULL, ",");
  
  if(NULL != strtokIndx)
  {
    Serial.print(", Pitch:"); Serial.print(strtokIndx);
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    Serial.print(", Roll:"); Serial.print(strtokIndx);
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    Serial.print(", Yaw:"); Serial.print(strtokIndx);
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    Serial.print(", Pressure:"); Serial.print(strtokIndx);
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    Serial.print(", Altitude:"); Serial.print(strtokIndx);
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    Serial.print(", Temperature:"); Serial.print(strtokIndx);
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    Serial.print(", LED Status:"); Serial.print(strtokIndx);
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    Serial.print(", LED PWM:"); Serial.print(strtokIndx);
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    Serial.print(", SD Status:"); Serial.print(strtokIndx);
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    Serial.print(", RSSI:"); Serial.print(strtokIndx);
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    Serial.print(", SNR:"); Serial.print(strtokIndx);
  }

  Serial.println();
}