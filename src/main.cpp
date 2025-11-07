#include <NimBLEDevice.h>
#include <Arduino.h>
#include "LSM6DS3.h"
#define SAMPLE_PERIOD 2778
#define LOW_POWER
#define TIMER_INTERRUPT_DEBUG         0
#define _TIMERINTERRUPT_LOGLEVEL_     0
#include <NRF52TimerInterrupt.h>
#include <NRF52_ISR_Timer.h>
#define BUFFER_SIZE 10
uint16_t data_buffer[BUFFER_SIZE];
uint8_t cursor = 0;
#define ECG_PIN    A0    // Analog ECG output
#define LO_PLUS    D1    // Lead-off detection + //try changing to d2
#define LO_MINUS   D2    // Lead-off detection -
#define BATTERY_PIN A5
bool low_battery = false;
LSM6DS3 myIMU(I2C_MODE, 0x6A);
NRF52Timer ITimer(NRF_TIMER_1);
NRF52_ISR_Timer ISR_Timer;
void blinkLed(int color, int no) {
        digitalWrite(color, HIGH);
        delay(200);
        digitalWrite(color, LOW);
        delay(200);
        digitalWrite(color, HIGH);
        delay(200);
        digitalWrite(color, LOW);
}
NimBLECharacteristic* characteristic;
void beginAdvertising() {
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
        pServer->updateConnParams(connInfo.getConnHandle(), 24, 48, 0, 400);
        blinkLed(LED_GREEN,2);
        connected = true;
    }
    void onDisconnect(NimBLEServer* pServer, NimBLEConnInfo& connInfo, int reason) {
        beginAdvertising();
        connected = false;
    }
};
void sendECGData() {
    static char string_buffer[12];

    int loPlusState = digitalRead(LO_PLUS);
    int loMinusState = digitalRead(LO_MINUS);

    if (loPlusState == HIGH || loMinusState == HIGH) {
        data_buffer[cursor] = 0; //leads off
        cursor++;
    } else {
        uint16_t ecgValue = analogRead(ECG_PIN);
        data_buffer[cursor] = ecgValue;
        cursor++;
    }
    if (cursor >= BUFFER_SIZE) {
        characteristic->setValue((uint8_t*)data_buffer,cursor * 2);
        characteristic->notify();
        cursor = 0;
    }
}

BLEStatus bleStatus;
void setup() {
    #ifdef LOW_POWER
    NRF_POWER->DCDCEN = 1;
    #endif
    delay(5000);
    pinMode(LED_BUILTIN, OUTPUT);
    blinkLed(LED_BLUE,2);
    ITimer.attachInterrupt(360.0, sendECGData);
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
        READ
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
    blinkLed(LED_GREEN,3);

}
void loop() {
    __SEV();
    __WFE();
    __WFE();
};