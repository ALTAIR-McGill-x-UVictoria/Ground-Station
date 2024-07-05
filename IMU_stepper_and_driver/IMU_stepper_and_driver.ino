#include "IntervalTimer.h"

//put actual pins
#define DIR_PIN 2
#define STEP_PIN 3
#define SLEEP_PIN 4
#define RESET_PIN 5

#define STEPS_PER_REV 200

#define NUM_LEDS 3

#define CW 0
#define CCW 1

IntervalTimer stepper_timer;

int speed = 80;

float partial_steps = 0;
bool curr_dir = CW;
int steps_left = 0;
bool step_lock = false;

float payload_yaw = 0; //TODO This should be constantly updated with data from imu. Place holder for now
float beacon_yaw = 0;
bool toggle_yaw_stabilization = false;

int set_dir(bool dir);
int turn_steps(float steps);
int turn_degrees(float degrees);
int turn_led(bool dir);
void c_step_signal();
int handle_command(String command);
int init_yaw_stabilization();
int stabilize_yaw();

//Set pins, start serial and start timer interrupt
void setup() {
  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(RESET_PIN, OUTPUT);
  pinMode(SLEEP_PIN, OUTPUT);
  Serial.begin(9600);
  if (!stepper_timer.begin(c_step_signal, 4)){ //triggers every 4 us
    Serial.println("Cannot begin timer. Exiting...");
    Serial.flush();
    exit(3);
  }
  //Disables sleep and reset
  digitalWrite(RESET_PIN, HIGH);
  digitalWrite(SLEEP_PIN, HIGH);
}

void loop() {

  //Remove lock when rotation is achieved
  if (!steps_left) step_lock = false; 

  if (toggle_yaw_stabilization){
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
        Serial.println("Error: Motor is locked.");
        break;
      case -2:
        Serial.println("Error: Command Unrecognized.");
        break;
    }
  }
}

int handle_command(String command){

  int error = 0;
  command.trim();

  if (command.startsWith("step ")) {//i.e. "step 100"
    float steps = command.substring(5).toFloat();
    error = turn_steps(steps);
  } 
  else if (command.startsWith("degree ")) {//i.e. "degree -90"
    float degrees = command.substring(7).toFloat();
    error = turn_degrees(degrees);
  }
  else if (command.startsWith("led ")) {//i.e. "led CCW"
    String led_dir = command.substring(4);
    if (led_dir.startsWith("CW")){ error = turn_led(CW); }
    if (led_dir.startsWith("CCW")){ error = turn_led(CCW); }
  }
  else if (command.startsWith("toggle yaw")) {//i.e. "toggle yaw"
    if (toggle_yaw_stabilization) {toggle_yaw_stabilization = false;}
    else if (!toggle_yaw_stabilization) {
      error = init_yaw_stabilization();
      if (!error) { toggle_yaw_stabilization = true; }
    }
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

//Callback function used by timer interrupt. 
void c_step_signal() {
  if (steps_left > 0) {
    digitalWrite(STEP_PIN, HIGH);
    delayNanoseconds(1900);
    digitalWrite(STEP_PIN, LOW);
    steps_left -= 1;
  }
}

//Turn by X.x steps. The non-integer part is accumulated in "partial_steps"
//When partial_steps reaches an integer, the motor position is corrected by adding the accumulated error
//A CW then CCW rotation will cancel the error, hence why we need to add/substract based on direction
int turn_steps(float steps) {

  //TODO Update angle
  //imu_yaw = update_imu_yaw();

  //Ignore command if motor already turning
  if (step_lock) return -1;

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
int turn_degrees(float degrees) {
  float steps = (degrees / 360) * STEPS_PER_REV;
  return turn_steps(steps);
}

//Go to previous or next LED
int turn_led(bool dir) {
  float steps = (STEPS_PER_REV / NUM_LEDS);
  if (dir == CCW) steps *= -1;

  return turn_steps(steps);
}

int init_yaw_stabilization() {
  beacon_yaw = payload_yaw;
  return 0;
}
int stabilize_yaw(){ //Incomplete
  float delta_angle = beacon_yaw - payload_yaw;
  turn_degrees(delta_angle);
  beacon_yaw += delta_angle 

  return 0;
}
