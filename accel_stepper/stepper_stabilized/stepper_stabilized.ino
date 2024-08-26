
#include "Waveshare_10Dof-D.h"
#include <SPI.h>
#include <IntervalTimer.h>

#define DIR_PIN 2
#define STEP_PIN 3
#define SLEEP_PIN 4
#define RESET_PIN 5
#define FAULT_PIN 6

#define M0_PIN 7
#define M1_PIN 8
#define M2_PIN 9

#define STEPS_PER_REV 200

#define NUM_LEDS 3

#define CW 0
#define CCW 1

#define USER 0
#define SYS 1

IntervalTimer timer1;

IMU_ST_ANGLES_DATA stAngles;
IMU_ST_SENSOR_DATA stGyroRawData;
IMU_ST_SENSOR_DATA stAccelRawData;
IMU_ST_SENSOR_DATA stMagnRawData;

int speed = 1000;
int step_division = 2;

double partial_steps = 0;
bool curr_dir = CW;
int steps_left = 0;
bool step_lock = false;

float payload_yaw = 0; 
float last_payload_yaw = 0;
bool toggle_yaw_stabilization = false;

#define LED_PIN 13
bool led_state = false;

int set_dir(bool dir);
int turn_steps(double steps, bool user_sys);
int turn_degrees(double degrees, bool user_sys);
int turn_led(bool dir, bool user_sys);
int handle_command(String command);
int init_yaw_stabilization();
int stabilize_yaw();
int set_substep(int division);
int set_speed(int s);
void pid_update();

bool step_state = true;
void handle_step(){
  if (steps_left > 0 && !step_state) {
    digitalWrite(STEP_PIN, 1);
    steps_left -= 1;
  }
  else if (step_state){
    digitalWrite(STEP_PIN, 0 );
    pid_update();
  }
  step_state = !step_state;
}

void setup() {
  Serial.begin(9600);
  sensorSetup();

  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(RESET_PIN, OUTPUT);
  pinMode(SLEEP_PIN, OUTPUT);
  pinMode(FAULT_PIN, INPUT);

  pinMode(M0_PIN, OUTPUT);
  pinMode(M1_PIN, OUTPUT);
  pinMode(M2_PIN, OUTPUT);

  pinMode(LED_PIN, OUTPUT);


  //Disables sleep and reset
  digitalWrite(RESET_PIN, HIGH);
  digitalWrite(SLEEP_PIN, HIGH);

  //Motor starts low
  digitalWrite(DIR_PIN, LOW);
  digitalWrite(STEP_PIN, LOW);

  if (set_substep(step_division)) {
    Serial.println("Invalid Step Division");
    Serial.flush();
    exit(-4);
  };
  
  timer1.begin(handle_step, speed);

  Serial.println("Done setup");
  Serial.flush();

}

int prev_time = 0;
int total_steps = 0;
void loop() {
  
  //Update angles
  if (1) {
    imuDataGet( &stAngles, &stGyroRawData, &stAccelRawData, &stMagnRawData);
    prev_time = millis();
    payload_yaw = stAngles.fYaw;
    Serial.print("Yaw "); Serial.print(payload_yaw); Serial.print("   Speed: "); Serial.print(speed); 
    Serial.print("   Steps Left:"); Serial.print(steps_left); Serial.print("   Partial: "); Serial.println(partial_steps); 
  }
  
  if (!steps_left) {step_lock = false; }
  //Else, turn 
  else if (1) {
    //digitalWrite(STEP_PIN, 1);
    //delayMicroseconds(1000);
    //digitalWrite(STEP_PIN, 0);
    //steps_left -= 1;
  }

  if (!digitalRead(FAULT_PIN)) {
    Serial.println("Fault pin low: error. Exiting...");
    Serial.flush();
    exit(4);
  }

 
  if ( toggle_yaw_stabilization){
    stabilize_yaw();
  }
  

  //Poll the serial for user input
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    int error = handle_command(command);

    switch(error) {
      case 0:
        Serial.println("Executed Command");
        break;
      case -1:
        Serial.println("Error: Motor is locked because it is turning.");
        break;
      case -2:
        Serial.println("Error: Command Unrecognized.");
        break;
      case -5:
        Serial.println("Error: Speed must be at least 500 and at most 3000.");
        break;
    }
  }
}


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
    else if (!toggle_yaw_stabilization) { toggle_yaw_stabilization = true; }
  }
  else if (command.startsWith("speed ")) {//i.e. "speed 750"
    float s = command.substring(6).toFloat();
    error = set_speed(s);
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

int set_speed(int s) {
  if (s < 500 || s > 3000) { return -5;}
  timer1.update(s);
  speed = s;
  return 0;
}

//Turn by X.x steps. The non-integer part is accumulated in "partial_steps"
//When partial_steps reaches an integer, the motor position is corrected by adding the accumulated error
//A CW then CCW rotation will cancel the error, hence why we need to add/substract based on direction
int turn_steps(double steps, bool user_sys) {
  //Serial.print("Steps: "); Serial.println(steps);
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
  //Serial.print("Steps is: "); Serial.print(steps); Serial.print(" so dir is: "); Serial.println(dir);

  //Update the accumulated error.
  partial_steps += steps - (int)steps;

  //The accumulated error reached 1 or -1. Add it to the steps to do
  if (abs(partial_steps) >= 1) {
    steps += (int)partial_steps;
    partial_steps -= (int)partial_steps;
  }
  //Select direction based on sign (again)
  dir = (steps>0) ? CW : CCW;
  set_dir(dir);

  steps_left = abs( (int)steps );
  step_lock = true;
  return 0;
}

//Turn by X.x degrees. Positive is CW, Negative is CCW
int turn_degrees(double degrees, bool user_sys) {
  double steps = (degrees / 360) * STEPS_PER_REV*step_division;
  return turn_steps(steps, user_sys);
}

//Go to previous or next LED 
int turn_led(bool dir, bool user_sys) {
  double steps = (STEPS_PER_REV*step_division / NUM_LEDS);
  if (dir == CCW) steps *= -1;

  return turn_steps(steps, user_sys);
}

int stabilize_yaw(){ 
  double delta_angle =  last_payload_yaw - payload_yaw;
  last_payload_yaw = payload_yaw;
  //Serial.print("Stabilizing: "); Serial.println(delta_angle);

  //Range of IMU is [-180,180]. Example Case: To move from -179 to 180 is 1 degree not -359 degrees 
  if (abs(delta_angle) > 180) {
    if (delta_angle > 0) { delta_angle -= 360; }
    else if (delta_angle < 0) { delta_angle += 360; }
  }

  turn_degrees(delta_angle, SYS);

  return 0; 
}

void pid_update(){
  if (steps_left == 0) return;
  float s = 0.5*steps_left*steps_left;
  s = 3000/s;
  if (s > 3000) s = 3000;
  if (s < 500) s = 500;
  set_speed(s);
}

int set_substep(int division){

  bool M0 = 0;
  bool M1 = 0;
  bool M2 = 0;

  switch(division) {
    case 1:
      M0 = 0;
      M1 = 0;
      M2 = 0;
      break;
    case 2:
      M0 = 1;
      M1 = 0;
      M2 = 0;
      break;
    case 4:
      M0 = 0;
      M1 = 1;
      M2 = 0;
      break;
    case 16:
      M0 = 1;
      M1 = 1;
      M2 = 0;
      break;
    case 32:
      M0 = 0;
      M1 = 0;
      M2 = 1;
      break;
    case 64:
      M0 = 1;
      M1 = 1;
      M2 = 1;
      break;
    default:
      return -4;
  }

  digitalWrite(M0_PIN, M0);
  digitalWrite(M1_PIN, M1);
  digitalWrite(M2_PIN, M2);

  return 0;
}

void sensorSetup(){
  IMU_EN_SENSOR_TYPE enMotionSensorType, enPressureType;
  imuInit(&enMotionSensorType, &enPressureType);
  delay(200);
}
