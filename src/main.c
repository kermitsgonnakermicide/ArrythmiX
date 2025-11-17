#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/logging/log.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/gpio.h>
static const struct gpio_dt_spec lo_pos = GPIO_DT_SPEC_GET(DT_ALIAS(leads_pos), gpios);
struct k_timer send_timer;
int lo_neg_state, lo_pos_state;
#define DATA_LENGTH 20
uint8_t cursor_pos = 0;
uint16_t data[DATA_LENGTH];
extern void send_data(struct k_timer *timer_id) {
    lo_neg_state = gpio_pin_get_dt(&lo_neg);
    lo_pos_state = gpio_pin_get_dt(&lo_pos);
    if (cursor_pos >= DATA_LENGTH) {
        cursor_pos = 0;
        return;
    }
    if (lo_neg_state && lo_pos_state) {
        LOG_INF("leads off");
        data[cursor_pos++] = lo_neg_state;
    }else {

    }
}
static const struct gpio_dt_spec lo_neg = GPIO_DT_SPEC_GET(DT_ALIAS(leads_negative), gpios);
int main() {
    if (!gpio_is_ready_dt(&lo_pos) || !gpio_is_ready_dt(&lo_neg)) {
        LOG_ERR("GPIO driver not ready");
        return -1;
    }
    k_timer_init(&send_timer,&send_data, NULL);
    int ret;
    ret = gpio_pin_configure_dt(&lo_pos, GPIO_INPUT);
    ret = gpio_pin_configure_dt(&lo_neg, GPIO_INPUT);
    if (ret < 0) {
        LOG_ERR("GPIO config failed");
        return -1;
    }
    k_timer_start(&send_timer, K_USEC(2300), K_USEC(2300));

    while (true) {

    }
    return 0;
}