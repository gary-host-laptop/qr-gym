const int LED_PIN = 13;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  Serial.begin(9600);
}

void loop() {
  if (Serial.available() > 0) {
    char comando = Serial.read();
    
    if (comando == 'H') {
      digitalWrite(LED_PIN, HIGH);
      delay(2000);  // 2 segundos encendido
      digitalWrite(LED_PIN, LOW);
      delay(1000);  // 1 segundo apagado
    }
  }
}