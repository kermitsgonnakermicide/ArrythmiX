#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/logging/log.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/adc.h>
LOG_MODULE_REGISTER(ecg_app, LOG_LEVEL_INF);
#define ECG_SERVICE_UUID_VAL \
    BT_UUID_128_ENCODE(0x12345678, 0x1234, 0x5678, 0x1234, 0x56789abcdef0)
#define ECG_CHAR_UUID_VAL \
    BT_UUID_128_ENCODE(0x12345678, 0x1234, 0x5678, 0x1234, 0x56789abcdef1)

static struct bt_uuid_128 ecg_service_uuid = BT_UUID_INIT_128(ECG_SERVICE_UUID_VAL);
static struct bt_uuid_128 ecg_char_uuid = BT_UUID_INIT_128(ECG_CHAR_UUID_VAL);

static bool notify_enabled = false;

static void ecg_ccc_cfg_changed(const struct bt_gatt_attr *attr, uint16_t value)
{
    notify_enabled = (value == BT_GATT_CCC_NOTIFY);
    LOG_INF("ECG notifications %s", notify_enabled ? "enabled" : "disabled");
}
#define DATA_LENGTH 20
static uint16_t ecg_data[DATA_LENGTH];

BT_GATT_SERVICE_DEFINE(ecg_service,
    BT_GATT_PRIMARY_SERVICE(&ecg_service_uuid),
    BT_GATT_CHARACTERISTIC(&ecg_char_uuid.uuid,
                          BT_GATT_CHRC_NOTIFY,
                          BT_GATT_PERM_NONE,
                          NULL, NULL, NULL),
    BT_GATT_CCC(ecg_ccc_cfg_changed,
               BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),
);

static const struct bt_data ad[] = {
    BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
    BT_DATA_BYTES(BT_DATA_UUID128_ALL, ECG_SERVICE_UUID_VAL),
};

static const struct gpio_dt_spec lo_pos = GPIO_DT_SPEC_GET(DT_ALIAS(leads_pos), gpios);
static const struct gpio_dt_spec lo_neg = GPIO_DT_SPEC_GET(DT_ALIAS(leads_negative), gpios);
static const struct adc_dt_spec ecg_adc = ADC_DT_SPEC_GET_BY_IDX(DT_PATH(zephyr_user), 0);

struct k_timer send_timer;
struct k_work send_work;
int lo_neg_state, lo_pos_state;
uint8_t cursor_pos = 0;
uint16_t adc_raw_value;
struct adc_sequence sequence;
void send_work_handler(struct k_work *work)
{
    lo_neg_state = gpio_pin_get_dt(&lo_neg);
    lo_pos_state = gpio_pin_get_dt(&lo_pos);
    
    if (cursor_pos >= DATA_LENGTH) {
        if (notify_enabled) {
            struct bt_gatt_attr *attr = bt_gatt_find_by_uuid(ecg_service.attrs, 
                                                             ecg_service.attr_count,
                                                             &ecg_char_uuid.uuid);
            if (attr) {
                bt_gatt_notify(NULL, attr, ecg_data, sizeof(ecg_data));
            }
        }
        cursor_pos = 0;
        return;
    }
    
    if (lo_neg_state && lo_pos_state) {
        LOG_INF("leads off");
        ecg_data[cursor_pos++] = 0;
    } else {
        adc_read(ecg_adc.dev, &sequence);
        ecg_data[cursor_pos++] = adc_raw_value;
    }
}

void timer_expiry(struct k_timer *timer_id)
{
    k_work_submit(&send_work);
}

static void connected(struct bt_conn *conn, uint8_t err)
{
    if (err) {
        LOG_ERR("Connection failed (err 0x%02x)", err);
    } else {
        LOG_INF("Connected");
    }
}

static void disconnected(struct bt_conn *conn, uint8_t reason)
{
    LOG_INF("Disconnected (reason 0x%02x)", reason);
}

BT_CONN_CB_DEFINE(conn_callbacks) = {
    .connected = connected,
    .disconnected = disconnected,
};

int main(void)
{
    int err, ret;

    err = bt_enable(NULL);
    if (err) {
        LOG_ERR("Bluetooth init failed (err %d)", err);
        return -1;
    }
    LOG_INF("Bluetooth initialized");

    if (!gpio_is_ready_dt(&lo_pos) || !gpio_is_ready_dt(&lo_neg)) {
        LOG_ERR("GPIO driver not ready");
        return -1;
    }

    if (!adc_is_ready_dt(&ecg_adc)) {
        LOG_ERR("ADC driver not ready");
        return -1;
    }

    ret = gpio_pin_configure_dt(&lo_pos, GPIO_INPUT);
    if (ret < 0) {
        LOG_ERR("Failed to configure lo_pos");
        return -1;
    }

    ret = gpio_pin_configure_dt(&lo_neg, GPIO_INPUT);
    if (ret < 0) {
        LOG_ERR("Failed to configure lo_neg");
        return -1;
    }

    ret = adc_channel_setup_dt(&ecg_adc);
    if (ret < 0) {
        LOG_ERR("ADC channel setup failed");
        return -1;
    }

    ret = adc_sequence_init_dt(&ecg_adc, &sequence);
    if (ret < 0) {
        LOG_ERR("ADC sequence init failed");
        return -1;
    }

    sequence.buffer = &adc_raw_value;
    sequence.buffer_size = sizeof(adc_raw_value);

    k_work_init(&send_work, send_work_handler);
    k_timer_init(&send_timer, timer_expiry, NULL);
    k_timer_start(&send_timer, K_USEC(2300), K_USEC(2300));

    err = bt_le_adv_start(BT_LE_ADV_CONN_FAST_1, ad, ARRAY_SIZE(ad), NULL, 0);
    if (err) {
        LOG_ERR("Advertising failed to start (err %d)", err);
        return -1;
    }
    LOG_INF("Advertising started");

    while (1) {
        k_sleep(K_FOREVER);
    }

    return 0;
}
