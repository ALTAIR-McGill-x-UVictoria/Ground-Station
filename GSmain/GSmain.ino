//Ground Station Main


//STEPPER STUFF-------------------------------------------------
#include <Bonezegei_DRV8825.h>

//put actual pins
#define DIR_PIN 6
#define STEP_PIN 7
#define SLEEP_PIN 8
#define RESET_PIN 9
#define FAULT_PIN 3
#define STEPS_PER_REV 200
#define NUM_LEDS 3
#define CW 0
#define CCW 1
#define USER 0
#define SYS 1

Bonezegei_DRV8825 stepper(DIR_PIN, STEP_PIN);

int speed = 80;

float partial_steps = 0;
bool curr_dir = CW;
int steps_left = 0;
bool step_lock = false;

float payload_yaw = 0; //TODO This should be constantly updated with data from imu. Place holder for now
float last_payload_yaw = 0;
bool toggle_yaw_stabilization = false;

#define LED_PIN 13
bool led_state = false;

int set_dir(bool dir);
int turn_steps(float steps, bool user_sys);
int turn_degrees(float degrees, bool user_sys);
int turn_led(bool dir, bool user_sys);
void c_step_signal();
int handle_command(String command);
int init_yaw_stabilization();
int stabilize_yaw();
void stepperSetup();
void radioSetup();

int handle_command(String command){

  int error = 0;
  command.trim();

  if (command.startsWith("step ")) {//i.e. "step 100"
    float steps = command.substring(5).toFloat();
    error = turn_steps(steps, USER);
  } 
  else if (command.startsWith("degree ")) {//i.e. "degree -90"
    float degrees = command.substring(7).toFloat();
    error = turn_degrees(degrees, USER);
  }
  else if (command.startsWith("led ")) {//i.e. "led CCW"
    String led_dir = command.substring(4);
    if (led_dir.startsWith("CW")){ error = turn_led(CW, USER); }
    if (led_dir.startsWith("CCW")){ error = turn_led(CCW, USER); }
  }
  else if (command.startsWith("toggle yaw")) {//i.e. "toggle yaw"
    if (toggle_yaw_stabilization) { toggle_yaw_stabilization = false; }
    else if (!toggle_yaw_stabilization) { last_payload_yaw = payload_yaw; toggle_yaw_stabilization = true; }
  }
  else {
    error = -2;
  }

  return error;
}

//CW or CCW
int set_dir(bool dir) {
  digitalWrite(DIR_PIN, dir);
  curr_dir = dir;
  return 0;
}

//Turn by X.x steps. The non-integer part is accumulated in "partial_steps"
//When partial_steps reaches an integer, the motor position is corrected by adding the accumulated error
//A CW then CCW rotation will cancel the error, hence why we need to add/substract based on direction
int turn_steps(float steps, bool user_sys) {

  if (steps == 0) {return 0;}

  //Allows the user to rotate even when stabilizing (Changing the target angle)    //TODO What to do for partial steps?
  if (toggle_yaw_stabilization && user_sys == USER) {
    
    //Motor Direction and User rotation in same direction 
    if ( (steps < 0 && curr_dir == CCW)   ||   (steps>0 && curr_dir == CW) ){
      steps_left += abs(steps);
    }
    //In different direction
    else {
      steps_left = abs(steps) - steps_left;
      set_dir(!curr_dir);
    }

    return 0;
  }

  //Ignore command if motor already turning
  if (step_lock) {return -1;}

  //Select direction based on sign
  bool dir = (steps>0) ? CW : CCW;
  set_dir(dir);

  //Add or Remove to the accumulated error.
  int add_sub = (curr_dir == CW) ? 1 : -1;
  partial_steps += (add_sub)*(steps - (int)steps);

  //The accumulated error reached 1 or -1. Add it to the steps to do
  if (abs(partial_steps) >= 1) {
    steps += (int)partial_steps;
    partial_steps -= (int)partial_steps;
  }

  steps_left = abs( (int)steps );
  step_lock = true;
  return 0;
}

//Turn by X.x degrees. Positive is CW, Negative is CCW
int turn_degrees(float degrees, bool user_sys) {
  float steps = (degrees / 360) * STEPS_PER_REV;
  return turn_steps(steps, user_sys);
}

//Go to previous or next LED
int turn_led(bool dir, bool user_sys) {
  float steps = (STEPS_PER_REV / NUM_LEDS);
  if (dir == CCW) steps *= -1;

  return turn_steps(steps, user_sys);
}

int stabilize_yaw(){ 
  float delta_angle = last_payload_yaw - payload_yaw;
  Serial.print("Stabilizing: "); Serial.println(delta_angle);
  last_payload_yaw = payload_yaw;
  delay(500);
  turn_degrees(delta_angle, SYS);

  return 0;
}
//END STEPPER STUFF-------------------------------


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
#define LOOP_TIMER 1000 

//Queue
#define QUEUE_SIZE 10

//Radio pin definitions
#define RFM95_RST 5
#define RFM95_CS 10
#define RFM95_INT 4

//LoRa parameters definitions
#define RF95_FREQ 433.0
#define SF 8
#define BW 125000
#define TX_POWER 20

//Show the raw packet received from FC instead of being parsed
#define SHOW_AS_RAW_PACKET 1


// Singleton instances
RH_RF95 rf95(RFM95_CS, RFM95_INT);
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

// elapsedMillis sendTimer;

void setup() {

  Serial.begin(115200);
  while (!Serial && (millis() < 3000));

  stepperSetup();
  radioSetup();

  Serial.println("System init complete");

  
}
int some_int = 0;
void loop() {  

  // if(DEBUG_RX == 1){
  //   if (sendTimer >= LOOP_TIMER){
  //     recvCommand();
  //     commandPacket = commandParser();
  //     radioRx();
  //     sendTimer = 0;
  //   }
  // } else{
  //   recvCommand();
  //   commandPacket = commandParser();
  //   radioRx();
  // }

  recvCommand();
  commandPacket = commandParser();
  radioRx();


  //STEPPER LOOP -------------------------------------
  if (!digitalRead(FAULT_PIN)) {
    Serial.println("Fault pin low: error. Exiting...");
    Serial.flush();
    exit(4);
  }
    
  //Remove lock when rotation is achieved
  payload_yaw = stAngles.fYaw;

  if (some_int >= 110000) {Serial.print("Yaw: ");Serial.println(payload_yaw); some_int = 0;}
  some_int++;
  if (!steps_left) {step_lock = false; }
  //Else, turn 
  else { 
    //Serial.println("Spinning"); Serial.flush();
    stepper.step(curr_dir, steps_left);
    //Serial.println("Stop Spinning"); Serial.flush();
    steps_left = 0;
  }

  if (toggle_yaw_stabilization && !step_lock){
    stabilize_yaw();
  }

  //Poll the serial for user input
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    int error = handle_command(command);

    switch(error) {
      case 0:
        Serial.println("Executing Command");
        break;
      case -1:
        Serial.println("Error: Motor is locked because it is turning.");
        break;
      case -2:
        Serial.println("Error: Command Unrecognized.");
        break;
    }
  }

}

void stepperSetup(){
  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(RESET_PIN, OUTPUT);
  pinMode(SLEEP_PIN, OUTPUT);
  pinMode(FAULT_PIN, INPUT);

  pinMode(LED_PIN, OUTPUT);

  stepper.begin();
  stepper.setSpeed(2000);

  //Disables sleep and reset
  digitalWrite(RESET_PIN, HIGH);
  digitalWrite(SLEEP_PIN, HIGH);

  //Motor starts low
  digitalWrite(DIR_PIN, LOW);
  digitalWrite(STEP_PIN, LOW);

  Serial.println("Done setup");
  Serial.flush();
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
    const char* tosend = data.c_str(); //no idea if this works
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