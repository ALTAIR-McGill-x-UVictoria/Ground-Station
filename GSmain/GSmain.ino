
//Flight Computer Main

// #include <RadioLib.h>
#include <ArduinoQueue.h>
#include "Waveshare_10Dof-D.h"
#include "RadioLogic.h"
#include <SPI.h>
#include <RH_RF95.h>
#include "Waveshare_10Dof-D.h"

#define QUEUE_SIZE 10

ArduinoQueue<String> queue(QUEUE_SIZE);

// bool gbSenserConnectState = false;

#define RFM95_RST 5
#define RFM95_CS 10
#define RFM95_INT 4

// Change to 434.0 or other frequency, must match RX's freq!
#define RF95_FREQ 433.0

// Singleton instance of the radio driver
RH_RF95 rf95(RFM95_CS, RFM95_INT);

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


void setup() {

  // radio = new RadioLogic();
  // rf95 = radio.rf95
  
  Serial.begin(115200);
  Serial.println("Initializing");
  // radioSetup();
  

  Serial.println("Running main loop");


}

void loop() {

  /*
  Radio logic loop:
  1 - FC starts in transmit mode, GS starts in receive mode
  2 - FC transmits one (or more) packet(s), flags last packet with set to receive, switch to receive and waits x ms
  3 - GS receives packet with flag, switch to transmit send command then switch back to receive
  4 - If FC receives packet confirmation (code >= 0), instantly switch to transmit (back to step 2), else if no packet reception for duration of wait switch back to step 2

  */

  recvCommand();
  commandPacket = commandParser();

  // fullSensorLoop();
  // radioTx("packet");

  
  

}




void radioSetup(){
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH);

  Serial.begin(115200);
  while (!Serial) delay(1);
  delay(100);

  Serial.println("Feather LoRa TX Test!");

  // manual reset
  digitalWrite(RFM95_RST, LOW);
  delay(10);
  digitalWrite(RFM95_RST, HIGH);
  delay(10);

  while (!rf95.init()) {
    Serial.println("LoRa radio init failed");
    Serial.println("Uncomment '#define SERIAL_DEBUG' in RH_RF95.cpp for detailed debug info");
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
  rf95.setTxPower(20, false);

}

void radioTx(char radiopacket[20]){

  // delay(1000); // Wait 1 second between transmits, could also 'sleep' here!
  Serial.println("Transmitting..."); // Send a message to rf95_server

  // char radiopacket[20] = "Hello World";
  // itoa(packetnum++, radiopacket+13, 10);
  // Serial.print("Sending "); Serial.println(radiopacket);
  // radiopacket[19] = 0;

  Serial.println("Sending...");
  // delay(10);
  rf95.send((uint8_t *)radiopacket, 20);

  Serial.println("Waiting for packet to complete...");
  // delay(10);
  rf95.waitPacketSent();
  // Now wait for a reply
  uint8_t buf[RH_RF95_MAX_MESSAGE_LEN];
  uint8_t len = sizeof(buf);

  // Serial.println("Waiting for reply...");
  if (rf95.waitAvailableTimeout(1000)) {
    // Should be a reply message for us now
    if (rf95.recv(buf, &len)) {
      // Serial.print("Got reply: ");
      Serial.println((char*)buf);
      Serial.print("RSSI: ");
      Serial.println(rf95.lastRssi(), DEC);
    } else {
      Serial.println("Receive failed");
    }
  } else {
    Serial.println("No reply, is there a listener around?");
  }
}

void radioRx(){
  if (rf95.available()) {
    // Should be a message for us now
    uint8_t buf[RH_RF95_MAX_MESSAGE_LEN];
    uint8_t len = sizeof(buf);

    if (rf95.recv(buf, &len)) {
      digitalWrite(LED_BUILTIN, HIGH);
      RH_RF95::printBuffer("Received: ", buf, len);
      Serial.print("Got: ");
      Serial.println((char*)buf);
      Serial.print("RSSI: ");
      Serial.println(rf95.lastRssi(), DEC);
    }

     // Send a reply
    String data;
    // byte data;

    if(!queue.isEmpty()){
    data = queue.dequeue();
    } else {data = "0,000.00";}
    const char* tosend = data.c_str(); //no idea if this works
    rf95.send((uint8_t *)tosend, sizeof(data));
    rf95.waitPacketSent();
    // Serial.println("Sent a reply");
    digitalWrite(LED_BUILTIN, LOW);
    } 
    else {
      Serial.println("Receive failed");
    }
  

}

void recvCommand() {
    static boolean recvInProgress = false;
    static byte ndx = 0;
    // char startMarker = '<';
    char endMarker = '\n';
    char rc;

    // if(Serial.available() > 0){
    //   recvInProgress = true;
    // }

    while (Serial.available() > 0 && newData == false) {
        rc = Serial.read();

        // if (recvInProgress == true) {
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
        // }

        // else if () {
        //     recvInProgress = true;
        // }
    }
}

//============

void parseData() {

      // split the data into its parts
    char * strtokIndx; // this is used by strtok() as an index

    strtokIndx = strtok(tempChars," ");      // get the first part - the string
    strcpy(messageFromPC, strtokIndx); // copy it to messageFromPC
  
    strtokIndx = strtok(NULL, " "); // this continues where the previous call left off
    floatFromPC = atof(strtokIndx);

    strtokIndx = strtok(NULL, " ");
    integerFromPC = atoi(strtokIndx);
}

//============

void showParsedData() {
    Serial.print("Command: ");
    Serial.print(messageFromPC);
    Serial.print(", FloatArg: ");
    Serial.print(floatFromPC);
    Serial.print(", IntArg ");
    Serial.print(integerFromPC);
    Serial.println();
}

String commandParser(){
  if (newData == true) { 
        strcpy(tempChars, receivedChars);
            // this temporary copy is necessary to protect the original data
            //   because strtok() replaces the commas with \0
        parseData();
        // showParsedData();
        
        // int code = 0;
        String dat = "0,000.00";

        if(strcmp(messageFromPC,"ping") == 0){
          // code = 1;
          dat = "1,000.00";
          Serial.print(dat); Serial.print(": ");
          Serial.println("pong");
          
        }
        else if(strcmp(messageFromPC,"ledon") == 0){
          // code = 2;
          floatFromPC = fmodf(floatFromPC, 10.0f);
          dat = "2," + (String) floatFromPC;
          dat.c_str();
          Serial.print(dat); Serial.print(": ");
          Serial.print("LED on, intensity: "); Serial.println(floatFromPC);
          
        }
        else if(strcmp(messageFromPC,"ledoff") == 0){
          // code = 3;
          dat = "3,000.00";
          Serial.print(dat); Serial.print(": ");
          Serial.println("LED off");
          
        }
        else if(strcmp(messageFromPC,"dangle") == 0){
          // code = 4;
          floatFromPC = abs(fmodf(floatFromPC, 360.0f));
          dat = "4," + (String) floatFromPC;
          Serial.print(dat); Serial.print(": ");
          Serial.print("Set driver angle to: "); Serial.println(floatFromPC);
          
        }
        else if(strcmp(messageFromPC,"sdwrite") == 0){
          // code = 5;
          dat = "5,000.00";
          Serial.print(dat); Serial.print(": ");
          Serial.println("Start DAQ write to SD");
          
        }
        else if(strcmp(messageFromPC,"sdstop") == 0){
          // code = 6;
          dat = "6,000.00";
          Serial.print(dat); Serial.print(": ");
          Serial.println("Stop DAQ write to SD");
          
        }
        else {
          String dat = "0,000.00";
          Serial.print(dat); Serial.print(": ");
          Serial.print("Error: "); Serial.print(messageFromPC); Serial.println(" is not a valid command");
          
        }


        newData = false;
        return dat;
        
    }
    return "0,000.00";

}