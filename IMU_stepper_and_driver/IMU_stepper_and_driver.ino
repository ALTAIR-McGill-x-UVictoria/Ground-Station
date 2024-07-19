#include <Bonezegei_DRV8825.h>

//put actual pins
#define DIR_PIN 2
#define STEP_PIN 3
#define SLEEP_PIN 4
#define RESET_PIN 5
#define FAULT_PIN 6

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

//Set pins, start serial and start timer interrupt
void setup() {
  Serial.begin(9600);

  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(RESET_PIN, OUTPUT);
  pinMode(SLEEP_PIN, OUTPUT);
  pinMode(FAULT_PIN, INPUT);

  pinMode(LED_PIN, OUTPUT);

  stepper.begin();

  //Disables sleep and reset
  digitalWrite(RESET_PIN, HIGH);
  digitalWrite(SLEEP_PIN, HIGH);

  //Motor starts low
  digitalWrite(DIR_PIN, LOW);
  digitalWrite(STEP_PIN, LOW);

  Serial.println("Done setup");
  Serial.flush();
}

void loop() {

  payload_yaw += 0.001;

  if (!digitalRead(FAULT_PIN)) {
    Serial.println("Fault pin low: error. Exiting...");
    Serial.flush();
    exit(4);
  }
  
  //Remove lock when rotation is achieved
  if (!steps_left) step_lock = false; 
  //Else, turn 
  else { 
    stepper.step(curr_dir, steps_left);
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

  last_payload_yaw = payload_yaw;
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
    if (toggle_yaw_stabilization) {toggle_yaw_stabilization = false; }
    else if (!toggle_yaw_stabilization) { toggle_yaw_stabilization = true; }
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
  //Serial.println(delta_angle);
  turn_degrees(delta_angle, SYS);

  return 0;
}
