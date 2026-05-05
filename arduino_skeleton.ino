// Sewbot Arduino Control (Serial2 version for Mega)
// Raspberry Pi communicates via TX2/RX2

// ---------------- PIN DEFINITIONS ----------------
const int MOTOR_LEFT_F = 22;
const int MOTOR_LEFT_B = 24;
const int MOTOR_RIGHT_F = 26;
const int MOTOR_RIGHT_B = 28;

const int PUMP_PIN = 34;
const int CONVEYOR_PIN = 30;

// ---------------- LOG FUNCTION ----------------
void sendLog(String level, String msg) {
  String full = "log:" + level + ":" + msg;

  Serial.println(full);    // USB debug
  Serial2.println(full);   // Send to Raspberry Pi
}

// ---------------- SETUP ----------------
void setup() {
  Serial.begin(9600);    // USB debug
  Serial2.begin(9600);   // Raspberry Pi UART

  // Set motor pins
  pinMode(MOTOR_LEFT_F, OUTPUT);
  pinMode(MOTOR_LEFT_B, OUTPUT);
  pinMode(MOTOR_RIGHT_F, OUTPUT);
  pinMode(MOTOR_RIGHT_B, OUTPUT);

  pinMode(PUMP_PIN, OUTPUT);
  pinMode(CONVEYOR_PIN, OUTPUT);

  stopAll();

  delay(1000); // allow serial to stabilize

  sendLog("info", "Arduino (Serial2) initialized and ready");
}

// ---------------- MAIN LOOP ----------------
void loop() {
  if (Serial2.available() > 0) {
    String command = Serial2.readStringUntil('\n');
    command.trim();

    if (command.length() > 0) {
      processCommand(command);
    }
  }
}

// ---------------- COMMAND PROCESSOR ----------------
void processCommand(String cmd) {
  int colonIndex = cmd.indexOf(':');

  if (colonIndex == -1) {
    sendLog("error", "Invalid format: " + cmd);
    return;
  }

  String category = cmd.substring(0, colonIndex);
  String action = cmd.substring(colonIndex + 1);

  sendLog("info", "Processing " + category + ":" + action);

  // -------- MOVEMENT --------
  if (category == "move") {
    stopMovement();

    if (action == "stop") return;

    bool w = action.indexOf('w') != -1;
    bool a = action.indexOf('a') != -1;
    bool s = action.indexOf('s') != -1;
    bool d = action.indexOf('d') != -1;

    if (w && a) moveForwardLeft();
    else if (w && d) moveForwardRight();
    else if (s && a) moveBackwardLeft();
    else if (s && d) moveBackwardRight();
    else if (w) moveForward();
    else if (s) moveBackward();
    else if (a) turnLeft();
    else if (d) turnRight();
  }

  // -------- PUMP --------
  else if (category == "pump") {
    if (action == "on") {
      digitalWrite(PUMP_PIN, HIGH);
    } else if (action == "off") {
      digitalWrite(PUMP_PIN, LOW);
    }
  }

  // -------- CONVEYOR --------
  else if (category == "conveyor") {
    if (action == "on") {
      digitalWrite(CONVEYOR_PIN, HIGH);
    } else if (action == "off") {
      digitalWrite(CONVEYOR_PIN, LOW);
    }
  }

  // -------- PLACEHOLDERS --------
  else if (category == "sideFlap") {
    sendLog("info", "Side flap: " + action);
  }

  else if (category == "ramp") {
    sendLog("info", "Ramp: " + action);
  }

  else if (category == "spray") {
    sendLog("info", "Spray: " + action);
  }

  else {
    sendLog("warning", "Unknown category: " + category);
  }
}

// ---------------- MOVEMENT FUNCTIONS ----------------
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
}
