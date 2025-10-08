#include "accel.h"

Accelerometer accel;

void Accelerometer::begin() {
    Wire.begin();
    mpu.initialize();

    if (mpu.testConnection()) {
        Serial.println("MPU6050 connected");
    } else {
        Serial.println("MPU6050 connection failed!");
    }
}

void Accelerometer::update() {
    mpu.getAcceleration(&ax, &ay, &az);
    values[0] = ax;
    values[1] = ay;
    values[2] = az;
}

int16_t* Accelerometer::getData() {
    return values;
}
