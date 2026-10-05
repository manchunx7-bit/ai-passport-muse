#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
    PASSPORT_MUSE_NEEDS_TOKEN, PASSPORT_MUSE_PAIRING, PASSPORT_MUSE_CONFIRM,
    PASSPORT_MUSE_CONNECTING, PASSPORT_MUSE_READY, PASSPORT_MUSE_LISTENING,
    PASSPORT_MUSE_WORKING, PASSPORT_MUSE_REPLY, PASSPORT_MUSE_ERROR,
    PASSPORT_MUSE_PHONE_SETUP,
} passport_muse_stage_t;
typedef struct {
    passport_muse_stage_t stage;
    bool sdk_token_set, paired, reply_is_answer;
    uint16_t level;
    uint32_t reply_revision;
    char name[64], device_name[32], detail[96], reply[1024];
} passport_muse_snapshot_t;
esp_err_t passport_muse_set_sdk_token(const char *token);
void passport_muse_config_status(bool *token_set, bool *paired);
esp_err_t passport_muse_set_proxy(const char *host, uint16_t port);
bool passport_muse_proxy_valid(const char *host, uint16_t port);
void passport_muse_proxy_config(char *host, size_t cap, uint16_t *port);
esp_err_t passport_muse_start(void);
bool passport_muse_stop(void);
void passport_muse_key(bool pressed, bool cancel);
void passport_muse_confirm(void);
// Explicit long-DOWN recovery. Clears only Muse account pairing, preserving
// SDK token, system Wi-Fi and the user's profile.
void passport_muse_repair(void);
void passport_muse_log_diagnostics(void);
void passport_muse_snapshot(passport_muse_snapshot_t *out);
size_t muse_hatch_reply_page(const char *text, size_t at, char *out, size_t cap);
// Serial diagnostics: only while the unconfigured Muse page is open. Starts
// and tears down BLE without advertising, pairing, credentials or cloud calls.
bool passport_muse_diagnostic_ble_cycle(void);
#ifdef __cplusplus
}
#endif
