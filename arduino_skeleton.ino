// Sewbot Arduino Control Skeleton
// Reads commands formatted as "category:action" over serial (baud 9600)
// from the Raspberry Pi and maps them to actuator functions.

// Define Motor / Actuator Pins Here
const int MOTOR_LEFT_F = 2;
const int MOTOR_LEFT_B = 3;
const int MOTOR_RIGHT_F = 4;
const int MOTOR_RIGHT_B = 5;

// Define other pins...
const int PUMP_PIN = 6;
const int CONVEYOR_PIN = 7;

void setup() {
  // Start Serial communication at 9600 baud
  // Must match the Python backend's baudrate!
  Serial.begin(9600);
  
  // Set pin modes
  pinMode(MOTOR_LEFT_F, OUTPUT);
  pinMode(MOTOR_LEFT_B, OUTPUT);
  pinMode(MOTOR_RIGHT_F, OUTPUT);
  pinMode(MOTOR_RIGHT_B, OUTPUT);
  pinMode(PUMP_PIN, OUTPUT);
  pinMode(CONVEYOR_PIN, OUTPUT);
  
  // Initialize states
  stopAll();
}

void loop() {
  // Check if data is available from the Raspberry Pi
  if (Serial.available() > 0) {
    // Read the incoming line until newline character '\n'
    String command = Serial.readStringUntil('\n');
    command.trim(); // Remove any carriage returns or spaces

    // Process the command
    processCommand(command);
  }
}

void processCommand(String cmd) {
  // Split the command into category and action using ':'
  int colonIndex = cmd.indexOf(':');
  
  if (colonIndex == -1) {
    // Invalid format, ignore
    return; 
  }
  
  String category = cmd.substring(0, colonIndex);
  String action = cmd.substring(colonIndex + 1);

  // --- 1. MOVEMENT CONTROL ---
  if (category == "move") {
    // First, stop all motors to avoid conflicting signals
    stopMovement();

    if (action == "stop") {
      return; // Already stopped
    }

    // Check which keys are actively being pressed
    bool w = action.indexOf('w') != -1;
    bool a = action.indexOf('a') != -1;
    bool s = action.indexOf('s') != -1;
    bool d = action.indexOf('d') != -1;

    // Apply combined logic (diagonals first, then straight)
    if (w && a) {
      moveForwardLeft();
    } 
    else if (w && d) {
      moveForwardRight();
    } 
    else if (s && a) {
      moveBackwardLeft();
    } 
    else if (s && d) {
      moveBackwardRight();
    } 
    else if (w) {
      moveForward();
    } 
    else if (s) {
      moveBackward();
    } 
    else if (a) {
      turnLeft();
    } 
    else if (d) {
      turnRight();
    }
  }
  
  // --- 2. SIDE FLAPS ---
  else if (category == "sideFlap") {
    if (action == "open") {
      // e.g., move servo to open angle
    } 
    else if (action == "close") {
      // e.g., move servo to close angle
    }
  }
  
  // --- 3. RAMP ---
  else if (category == "ramp") {
    if (action == "open") {
      // e.g., lower ramp
    } 
    else if (action == "close") {
      // e.g., raise ramp
    }
  }
  
  // --- 4. SPRAY ---
  else if (category == "spray") {
    if (action == "left") {
      // Activate left spray
    } 
    else if (action == "right") {
      // Activate right spray
    }
  }
  
  // --- 5. PUMP ---
  else if (category == "pump") {
    if (action == "on") {
      digitalWrite(PUMP_PIN, HIGH);
    } 
    else if (action == "off") {
      digitalWrite(PUMP_PIN, LOW);
    }
  }
  
  // --- 6. CONVEYOR ---
  else if (category == "conveyor") {
    if (action == "on") {
      digitalWrite(CONVEYOR_PIN, HIGH);
    } 
    else if (action == "off") {
      digitalWrite(CONVEYOR_PIN, LOW);
    }
  }
}

// ---------------------------------------------
// IMPLEMENTATION FUNCTIONS
// ---------------------------------------------

void moveForward() {
  digitalWrite(MOTOR_LEFT_F, HIGH);
  digitalWrite(MOTOR_LEFT_B, LOW);
  digitalWrite(MOTOR_RIGHT_F, HIGH);
  digitalWrite(MOTOR_RIGHT_B, LOW);
}

void moveBackward() {
  digitalWrite(MOTOR_LEFT_F, LOW);
  digitalWrite(MOTOR_LEFT_B, HIGH);
  digitalWrite(MOTOR_RIGHT_F, LOW);
  digitalWrite(MOTOR_RIGHT_B, HIGH);
}

void turnLeft() {
  digitalWrite(MOTOR_LEFT_F, LOW);
  digitalWrite(MOTOR_LEFT_B, HIGH);
  digitalWrite(MOTOR_RIGHT_F, HIGH);
  digitalWrite(MOTOR_RIGHT_B, LOW);
}

void turnRight() {
  digitalWrite(MOTOR_LEFT_F, HIGH);
  digitalWrite(MOTOR_LEFT_B, LOW);
  digitalWrite(MOTOR_RIGHT_F, LOW);
  digitalWrite(MOTOR_RIGHT_B, HIGH);
}

void moveForwardLeft() {
  // E.g., right motor full forward, left motor stopped or half speed
  digitalWrite(MOTOR_LEFT_F, LOW);
  digitalWrite(MOTOR_LEFT_B, LOW);
  digitalWrite(MOTOR_RIGHT_F, HIGH);
  digitalWrite(MOTOR_RIGHT_B, LOW);
}

void moveForwardRight() {
  digitalWrite(MOTOR_LEFT_F, HIGH);
  digitalWrite(MOTOR_LEFT_B, LOW);
  digitalWrite(MOTOR_RIGHT_F, LOW);
  digitalWrite(MOTOR_RIGHT_B, LOW);
}

void moveBackwardLeft() {
  digitalWrite(MOTOR_LEFT_F, LOW);
  digitalWrite(MOTOR_LEFT_B, LOW);
  digitalWrite(MOTOR_RIGHT_F, LOW);
  digitalWrite(MOTOR_RIGHT_B, HIGH);
}

void moveBackwardRight() {
  digitalWrite(MOTOR_LEFT_F, LOW);
  digitalWrite(MOTOR_LEFT_B, HIGH);
  digitalWrite(MOTOR_RIGHT_F, LOW);
  digitalWrite(MOTOR_RIGHT_B, LOW);
}

void stopMovement() {
  digitalWrite(MOTOR_LEFT_F, LOW);
  digitalWrite(MOTOR_LEFT_B, LOW);
  digitalWrite(MOTOR_RIGHT_F, LOW);
  digitalWrite(MOTOR_RIGHT_B, LOW);
}

void stopAll() {
  stopMovement();
  digitalWrite(PUMP_PIN, LOW);
  digitalWrite(CONVEYOR_PIN, LOW);
  // Reset servos/actuators if necessary...
}
