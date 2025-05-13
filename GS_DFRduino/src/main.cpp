//Ground Station Main

#include <ArduinoQueue.h>
#include <SPI.h>
#include <RH_RF95.h>

//Callsign
#define CALLSIGN "VA2ETD"
#define SHOW_CALLSIGN 0 //will show callsign in serial monitor

//Radio debugging without FC
#define DEBUG_RX 0
#define LOOP_TIMER 1000 

//Queue
#define QUEUE_SIZE 5     // Reduced from 10

//Radio pin definitions
#define RFM95_RST 7
#define RFM95_CS 10
#define RFM95_INT 2

//LoRa parameters definitions
#define RF95_FREQ 900.0
#define SF 8
#define BW 125000
#define TX_POWER 20

//Show the raw packet received from FC instead of being parsed
int showAsRawPacket = 1;

// Add at the top with other global variables
unsigned long lastPacketTime = 0;
unsigned long sendTimer = 0;
unsigned long currentMillis = 0;

// Singleton instances
RH_RF95 rf95(RFM95_CS, RFM95_INT);
ArduinoQueue<String> queue(QUEUE_SIZE);

// Add this forward declaration before it's used:
void groundpacketParser(char* receivedPacket, int enableRaw);

//Command parser variables
const byte numChars = 20;      // Reduced from 32
char receivedChars[numChars];
char tempChars[numChars];        // temporary array for use by strtok() function

      // variables to hold the parsed data
char messageFromPC[numChars] = {0};
int integerFromPC = 0;
float floatFromPC = 0.0;

String commandPacket;

boolean newData = false;

volatile int receptionConfirm = 0;
volatile int ignoreNextConfirm = 0;
String FcCommandID = "X";

// Add these at the top of your file with other #define statements
#define CMD_BUFSIZE 12  // Buffer size for command strings

void radioSetup(){
  Serial.println("Starting radio setup...");
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH);

  delay(100);

  // manual reset
  digitalWrite(RFM95_RST, LOW);
  delay(10);
  digitalWrite(RFM95_RST, HIGH);
  delay(10);

  while (!rf95.init()) {
    Serial.println("LoRa radio init failed");
    delay(1000); // Add delay instead of infinite loop
  }
  Serial.println("LoRa radio init OK!");

  // Defaults after init are 434.0MHz, modulation GFSK_Rb250Fd250, +13dbM
  if (!rf95.setFrequency(RF95_FREQ)) {
    Serial.println("setFrequency failed");
    delay(1000); // Add delay instead of infinite loop
  }
  Serial.print("Set Freq to: "); Serial.println(RF95_FREQ);

  // The default transmitter power is 13dBm, using PA_BOOST.
  // If you are using RFM95/96/97/98 modules which uses the PA_BOOST transmitter pin, then
  // you can set transmitter powers from 5 to 23 dBm:
  rf95.setSignalBandwidth(BW);
  // rf95.setCodingRate4(5);
  rf95.setSpreadingFactor(SF);
  rf95.setTxPower(TX_POWER, false);
  
  Serial.println("Radio setup complete");
}


void radioRx(){
  static uint8_t buf[RH_RF95_MAX_MESSAGE_LEN]; // Make static to save stack
  
  if (rf95.available() || DEBUG_RX) {
    
    if(DEBUG_RX){
      String str = "";
      str = str + String(rand()).substring(0,5) + ":0,-26,12,5.69,35.08,-134.84,0.07,-1,-1,-1,0.00,44330.00,0.00,111,160,1,1,1,11.1,1.4\n-22,11";
      // Cast properly to avoid warnings
      strncpy((char*)buf, str.c_str(), sizeof(buf)-1);
      buf[sizeof(buf)-1] = '\0'; // Ensure null-termination
    }

    uint8_t len = sizeof(buf);

    if (rf95.recv(buf, &len) || DEBUG_RX) {
      digitalWrite(LED_BUILTIN, HIGH);
      
      // Calculate time since last packet
      unsigned long currentTime = millis();
      unsigned long timeSinceLastPacket = currentTime - lastPacketTime;
      lastPacketTime = currentTime;

      groundpacketParser((char*) buf, showAsRawPacket);
      
      if(DEBUG_RX){return;}

      if(showAsRawPacket == 0) {
          Serial.print("RSSI: ");
      }
      Serial.print(rf95.lastRssi(), DEC);
      Serial.print(",");
      if(showAsRawPacket == 0) {
          Serial.print(" SNR: ");
      }
      Serial.print(rf95.lastSNR(), DEC);
      Serial.print(",");
      if(showAsRawPacket == 0) {
          Serial.print(" Delta t: ");
      }
      Serial.println(timeSinceLastPacket);
    }

     // Send a reply
    static char dataBuffer[CMD_BUFSIZE];
    
    if(!queue.isEmpty()) {
      String data = queue.dequeue();
      strncpy(dataBuffer, data.c_str(), CMD_BUFSIZE-1);
      dataBuffer[CMD_BUFSIZE-1] = '\0'; // Ensure null-termination
    } else {
      strcpy(dataBuffer, "0,0.00");
    }
    
    rf95.send((uint8_t *)dataBuffer, strlen(dataBuffer));
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
    char rc;
    char startMarker = '>';  // Optional: Add a start marker
    char endMarker = '\n';

    while (Serial.available() > 0) {
        rc = Serial.read();

        // Optional: Start collecting only after start marker
        if (recvInProgress == false && rc == startMarker) {
            recvInProgress = true;
            Serial.println("Command started");
            continue;
        }

        if (recvInProgress) {
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
                Serial.print("Received command: ");
                Serial.println(receivedChars);
            }
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
        
        static char dat[CMD_BUFSIZE]; // Static to avoid stack allocations
        strcpy(dat, "0,000.00");  // Default value
        
        Serial.print("Parsed command: '");
        Serial.print(messageFromPC);
        Serial.print("', value: ");
        Serial.println(floatFromPC);

        if(strcmp(messageFromPC,"0") == 0){
            strcpy(dat, "0,000.00");
            Serial.println("Command '0' processed");
        }
        else if(strcmp(messageFromPC,"ping") == 0){
            strcpy(dat, "1,000.00");
            queue.enqueue(dat);
            Serial.println("Ping command queued");
        }
        else if(strcmp(messageFromPC,"led1") == 0){
            floatFromPC = fmodf(floatFromPC, 100.00f);
            snprintf(dat, CMD_BUFSIZE, "2,%.2f", floatFromPC);
            queue.enqueue(dat);
            Serial.println("LED1 command queued");
        }
        // Other commands...
        else {
            Serial.println("Unknown command");
        }
        
        strcpy(receivedChars,"0");
        floatFromPC = 0.0;
        newData = false;
        return dat;
    }
    return "0,000.00"; // Default return value
}

void groundpacketParser(char* receivedPacket, int enableRaw){

  char * strtokIndx; // this is used by strtok() as an index

  // char * packetCopy = ""; 
  // strcpy(packetCopy, receivedPacket);
  if (enableRaw){
    Serial.print(receivedPacket);
  }

  strtokIndx = strtok(receivedPacket,":");

  
  //COMMAND ID
  if(NULL != strtokIndx)
  {
    
    FcCommandID = strtokIndx;
    // Serial.print(strtokIndx); Serial.print(": ");
    
  }
  

  // if(enableRaw == 1){
  //   Serial.print(packetCopy);
  // }

  strtokIndx = strtok(NULL, ",");

  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print("Pong: "); Serial.print(strtokIndx);
    }
    
    receptionConfirm = strcmp(strtokIndx,"1") == 0 ? 1 : 0; 
    
  }

  strtokIndx = strtok(NULL, ",");

  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", FC RSSI:"); Serial.print(strtokIndx);
    }
  }

  strtokIndx = strtok(NULL, ",");

  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", FC SNR:"); Serial.print(strtokIndx);
    }
  }


  strtokIndx = strtok(NULL, ",");

  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", Battery Voltage:"); Serial.print(strtokIndx);
    }
  }

  strtokIndx = strtok(NULL, ",");
  
  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", Pitch:"); Serial.print(strtokIndx);
    }
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", Roll:"); Serial.print(strtokIndx);
    }
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", Yaw:"); Serial.print(strtokIndx);
    }
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", AccX:"); Serial.print(strtokIndx);
    }
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", AccY:"); Serial.print(strtokIndx);
    }
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", AccZ:"); Serial.print(strtokIndx);
    }
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", Pressure:"); Serial.print(strtokIndx);
    }
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", Altitude:"); Serial.print(strtokIndx);
    }
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", Temperature:"); Serial.print(strtokIndx);
    }
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", LED Status:"); Serial.print(strtokIndx);
    }
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", LED PWM:"); Serial.print(strtokIndx);
    }
  }

  strtokIndx = strtok(NULL, ",");
    
  if(NULL != strtokIndx)
  {
    if(enableRaw == 0){
    Serial.print(", SD Status:"); Serial.print(strtokIndx);
    }
  }




  

  Serial.println();
  
}

void setup() {
  // Setup serial directly without closing first
  Serial.begin(115200);
  delay(250); // Reduced delay
  
  // Uncomment buffer clearing - it's important to avoid garbage data
  while(Serial.available()) {
    Serial.read();
  }
  
  Serial.println("GS start");
  
  // Remove the extra Serial waiting loop to save memory
  //unsigned long startMillis = millis();
  //while (!Serial && (millis() - startMillis < 3000));
  
  radioSetup();
  
  // Check if queue is not empty before dequeuing
  if(!queue.isEmpty()) {
    queue.dequeue();
  }
  
  Serial.println("Init OK");
  Serial.println("Ready:");
}

void loop() {  
    currentMillis = millis();

    // Print a heartbeat message every 5 seconds
    static unsigned long lastHeartbeat = 0;
    if (currentMillis - lastHeartbeat >= 5000) {
        Serial.println("Heartbeat - system running");
        lastHeartbeat = currentMillis;
    }

    // Check for available serial data and display count
    static unsigned long lastSerialCheck = 0;
    if (currentMillis - lastSerialCheck >= 1000) {
        int bytesAvail = Serial.available();
        if (bytesAvail > 0) {
            Serial.print("Serial bytes available: ");
            Serial.println(bytesAvail);
        }
        lastSerialCheck = currentMillis;
    }

    if(DEBUG_RX == 1){
        if ((currentMillis - sendTimer) >= LOOP_TIMER){
            recvCommand();
            commandPacket = commandParser();
            radioRx();
            sendTimer = currentMillis;
        }
    } else{
        recvCommand();
        if (newData) {
            Serial.println("Processing new command");
        }
        commandPacket = commandParser();
        radioRx();
    }
}