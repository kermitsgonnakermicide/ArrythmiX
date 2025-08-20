#include <NimBLEDevice.h>
#include <Arduino.h>
#define SAMPLE_PERIOD 2778
#define ECG_PIN   A0    // Analog ECG output
#define LO_PLUS    D8    // Lead-off detection +
#define LO_MINUS   D7    // Lead-off detection -
#define BATTERY_PIN A9
bool low_battery = false;
void blinkLed() {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(200);
    digitalWrite(LED_BUILTIN, LOW);
}
NimBLECharacteristic* characteristic;
void beginAdvertising() {
    Serial.println("Advertising");
    NimBLEAdvertising* pAdvertising = NimBLEDevice::getAdvertising();
    pAdvertising->setName("ECG Data");

    pAdvertising->addServiceUUID("180D");  // Heart Rate Service
    pAdvertising->addServiceUUID("180A");
    std::string manufData = "";
    manufData += (char)0xFF;
    manufData += (char)0xFF;
    manufData += "Embedded Jankineers";
    pAdvertising->setManufacturerData(manufData);
    pAdvertising->start();
}
class BLEStatus : public NimBLEServerCallbacks {
public:
    bool connected = false;
    void onConnect(NimBLEServer* pServer, NimBLEConnInfo& connInfo) {
        Serial.println("Device Connected");
        connected = true;
    }
    void onDisconnect(NimBLEServer* pServer, NimBLEConnInfo& connInfo, int reason) {
        Serial.printf("Device Disconnected %d\n", reason);
        beginAdvertising();
        connected = false;
    }
};

BLEStatus bleStatus;
void setup() {
    delay(5000);
    Serial.begin(115200);
    pinMode(LED_BUILTIN, OUTPUT);
    blinkLed();

    NimBLEDevice::init("ECG Data");
    NimBLEDevice::setOwnAddrType(BLE_OWN_ADDR_RANDOM);
    NimBLEServer* pServer = NimBLEDevice::createServer();
    pServer->setCallbacks(&bleStatus);
    NimBLEService* pDIS = pServer->createService("180A");
    NimBLECharacteristic* pManufChar = pDIS->createCharacteristic(
        "2A29",
        NIMBLE_PROPERTY::READ
    );
    pManufChar->setValue("Embedded Jankineers");
    NimBLECharacteristic* pModelChar = pDIS->createCharacteristic(
        "2A24",
        NIMBLE_PROPERTY::READ
    );
    pModelChar->setValue("ECG Device Model 1");
    pDIS->start();
    NimBLEService* pService = pServer->createService("180D");
    characteristic = pService->createCharacteristic(
        "e2fd985e-ceb8-4ccb-9cd3-52563e4b5c62",
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::NOTIFY
    );
    characteristic->setValue("Hello from NimBLE!");
    characteristic->notify();
    pService->start();

    pinMode(BATTERY_PIN, INPUT);
    pinMode(ECG_PIN, INPUT);
    pinMode(LO_PLUS, INPUT_PULLUP);
    pinMode(LO_MINUS, INPUT_PULLUP);
    beginAdvertising();
    Serial.println("NimBLE running");
    Serial.println(NimBLEDevice::getAddress().toString().c_str());
}

int i = 0;
unsigned long timeSinceLastBlink = 0;
bool builtinLed_Status = false;
void loop() {
    if (low_battery) {
        if (millis() - timeSinceLastBlink > 200) {
            if (builtinLed_Status) {
                digitalWrite(LED_BUILTIN, LOW);
            } else {
                digitalWrite(LED_BUILTIN, HIGH);
            }
            builtinLed_Status = !builtinLed_Status;
            timeSinceLastBlink = millis();
        }
    }
    static unsigned long lastSampleTime = 0;
    unsigned long currentTime = micros();
    String Value;
    if (currentTime - lastSampleTime >= SAMPLE_PERIOD) {
        lastSampleTime += SAMPLE_PERIOD;
        int loPlusState = digitalRead(LO_PLUS);
        int loMinusState = digitalRead(LO_MINUS);
        if (loPlusState == HIGH || loMinusState == HIGH) {
            Value = "Leads Off";
        } else {
            int ecgValue = analogRead(ECG_PIN);
            Value = String(ecgValue);
        }
    }
    characteristic->setValue(Value.c_str());
    characteristic->notify();
    delay(20);
}
