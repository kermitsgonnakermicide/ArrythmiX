#ifndef ACCEL_H
#define ACCEL_H

#include <Arduino.h>
#include <MPU6050.h>

class Accelerometer {
public:
    void begin();
    void update();
    int16_t* getData();

private:
    MPU6050 mpu;
    int16_t ax, ay, az;
    int16_t values[3] = {0,0,0};
};

extern Accelerometer accel;

#endif
