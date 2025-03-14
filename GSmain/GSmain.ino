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
#define QUEUE_SIZE 10

//Radio pin definitions
#define RFM95_RST 20
#define RFM95_CS 10
#define RFM95_INT 21

//LoRa parameters definitions
#define RF95_FREQ 433.0
#define SF 8
#define BW 125000
#define TX_POWER 20

//Show the raw packet received from FC instead of being parsed
int showAsRawPacket = 1;

// Add at the top with other global variables
unsigned long lastPacketTime = 0;

// Singleton instances
RH_RF95 rf95(RFM95_CS, RFM95_INT);
ArduinoQueue<String> queue(QUEUE_SIZE);



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

volatile int receptionConfirm = 0;
volatile int ignoreNextConfirm = 0;
String FcCommandID = "X";

elapsedMillis sendTimer;

void setup() {

  Serial.begin(115200);
  while (!Serial && (millis() < 3000));

  radioSetup();

  queue.dequeue();
  Serial.println("System init complete");

  
}

void loop() {  

  if(DEBUG_RX == 1){
    if (sendTimer >= LOOP_TIMER){
      recvCommand();
      commandPacket = commandParser();
      radioRx();
      sendTimer = 0;
    }
  } else{
    recvCommand();
    commandPacket = commandParser();
    radioRx();
  }


  // recvCommand();
  // commandPacket = commandParser();
  // radioRx();


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


void radioRx(){

  
  if (rf95.available() || DEBUG_RX) {
    // Should be a message for us now
    uint8_t buf[RH_RF95_MAX_MESSAGE_LEN];
    // uint8_t len = sizeof(buf);

    

    if(DEBUG_RX){
      String str = "";
      str = str + String(rand()).substring(0,5) + ":0,-26,12,5.69,35.08,-134.84,0.07,-1,-1,-1,0.00,44330.00,0.00,111,160,1,1,1,11.1,1.4\n-22,11";
      // str = str + String(rand()).substring(0,5) + ":0,-26,12,5.69\n-22,11";
      char* debugMessage = str.c_str();
      strcpy(buf, debugMessage);
      
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
    String data;
    if(!queue.isEmpty()) {
        data = queue.dequeue();
    } else {
        data = "0,0.00"; // Simple command,argument format
    }
    
    // Don't append telemetry data
    const char* tosend = data.c_str();
    rf95.send((uint8_t *)tosend, strlen(tosend));
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
          // Serial.print(dat); Serial.print(": ");
          // Serial.println("pong");
          
        }
        else if(strcmp(messageFromPC,"led1") == 0){
          // code = 2;
          floatFromPC = fmodf(floatFromPC, 100.00f);
          dat = "2," + (String) floatFromPC;
          queue.enqueue(dat);
          dat.c_str();
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Toggled LED 1");
          
        }
        else if(strcmp(messageFromPC,"led2") == 0){
          // code = 2;
          floatFromPC = fmodf(floatFromPC, 100.00f);
          dat = "3," + (String) floatFromPC;
          queue.enqueue(dat);
          dat.c_str();
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Toggle LED 2");
          
        }
        else if(strcmp(messageFromPC,"led3") == 0){
          // code = 2;
          floatFromPC = fmodf(floatFromPC, 100.00f);
          dat = "4," + (String) floatFromPC;
          queue.enqueue(dat);
          dat.c_str();
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Toggled LED 3");
          
        }
        else if(strcmp(messageFromPC,"ledoff") == 0){
          // code = 3;
          dat = "5,000.00";
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.println("LED off");
          
        }
        else if(strcmp(messageFromPC,"imucal") == 0){
          // code = 4;
          dat = "6,000.00";
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Zeroed IMU angles");
          
        }
        else if(strcmp(messageFromPC,"sdwrite") == 0){
          // code = 5;
          dat = "7,000.00";
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Start DAQ write to SD");
          
        }
        else if(strcmp(messageFromPC,"sdstop") == 0){
          // code = 6;
          dat = "8,000.00";
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Stopped DAQ write to SD");
          
        }
        else if(strcmp(messageFromPC,"sdclear") == 0){
          // code = 6;
          dat = "9,000.00";
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Deleted datalog.txt");
          
        }
        else if(strcmp(messageFromPC,"ledblink") == 0){
          // code = 6;
          dat = "10," + (String) floatFromPC;
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.print("LED blinking set for "); Serial.print(floatFromPC); Serial.println(" ms");
          
        }
        else if(strcmp(messageFromPC,"ledbright") == 0){
          // code = 11;
          dat = "11," + (String) floatFromPC;
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.print("LED brightness set for "); Serial.print(floatFromPC); Serial.println("%");
          
        }
        else if(strcmp(messageFromPC,"togglelong") == 0){
          // code = 12;
          dat = "12," + (String) floatFromPC;
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Toggled long packet format");
          
        }
        else if(strcmp(messageFromPC,"toggleparsing") == 0){
          showAsRawPacket = !showAsRawPacket; 
          
        }
        else if(strcmp(messageFromPC,"zeromotor") == 0){
          dat = "13," + (String) floatFromPC;
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Set current motor angle as zero");
          
        }
        else if(strcmp(messageFromPC,"stepperspeed") == 0){
          dat = "14," + (String) floatFromPC;
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.print("Set step speed to "); Serial.println(floatFromPC);
          
        }
        else if(strcmp(messageFromPC,"togglestab") == 0){
          dat = "15," + (String) floatFromPC;
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Toggled beacon stabilization");
          
        }
        else if(strcmp(messageFromPC,"toggleflightmode") == 0){
          dat = "16," + (String) floatFromPC;
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Toggled flight mode fast transmission rate");
          
        }
        else if(strcmp(messageFromPC,"setradiotimeout") == 0){
          dat = "17," + (String) floatFromPC;
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.print("Set radio timeout for "); Serial.print(floatFromPC); Serial.println(" ms");
          
        }
        else if(strcmp(messageFromPC,"resetfc") == 0){
          dat = "18," + (String) floatFromPC;
          ignoreNextConfirm = 1;
          queue.enqueue(dat);
          Serial.println("Reinitializing Flight Computer");
        }
        else if(strcmp(messageFromPC,"clearq") == 0){
          while(!queue.isEmpty()){
            queue.dequeue();
          }
          Serial.println("Cleared command queue");
        }
        else if(strcmp(messageFromPC,"terminate") == 0){
          dat = "19," + (String) floatFromPC;
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Linear actuator energized");
          
        }
        else if(strcmp(messageFromPC,"resetactuator") == 0){
          dat = "20," + (String) floatFromPC;
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Linear actuator de-energized");
          
        }
        else if(strcmp(messageFromPC,"sdnewfile") == 0){
          dat = "21," + (String) floatFromPC;
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Created new SD card file");
          
        }
        else if(strcmp(messageFromPC,"debugheating") == 0){
          dat = "22," + (String) floatFromPC;
          queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.println("Temporarily toggled heating");
          
        }


        else if(strcmp(messageFromPC,"debugstop") == 0){
          //debug command
          while(1);
          
        }



        else {
          String dat = "0,000.00";
          // queue.enqueue(dat);
          // Serial.print(dat); Serial.print(": ");
          Serial.print("Error: "); Serial.print(messageFromPC); Serial.println(" is not a valid command");
          
        }
        
        strcpy(receivedChars,"0");
        floatFromPC = 0.0;

        newData = false;
        return dat;
        
    }

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