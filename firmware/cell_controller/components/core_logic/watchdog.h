/* Watchdog abstraction (SF-06). Pure logic — a timeout tracker over the device's monotonic
 * clock — so it is identical on host and on ESP32; the eventual esp_task_wdt_* calls (P1.10)
 * wrap THIS module rather than being called from core_logic directly, keeping core_logic
 * portable per README rule 1.
 */
#ifndef MSFC_WATCHDOG_H
#define MSFC_WATCHDOG_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint32_t timeout_ms;
    uint32_t last_feed_mono_ms;
    bool expired;   /* latched true once timeout is detected; cleared only by watchdog_init */
} watchdog_t;

void watchdog_init(watchdog_t *wd, uint32_t timeout_ms, uint32_t now_mono_ms);
void watchdog_feed(watchdog_t *wd, uint32_t now_mono_ms);
/* Call once per control cycle; returns true if the watchdog is (now or already) expired. */
bool watchdog_check(watchdog_t *wd, uint32_t now_mono_ms);

#endif /* MSFC_WATCHDOG_H */
