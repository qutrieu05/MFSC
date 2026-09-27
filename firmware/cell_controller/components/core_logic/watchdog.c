#include "watchdog.h"

void watchdog_init(watchdog_t *wd, uint32_t timeout_ms, uint32_t now_mono_ms) {
    wd->timeout_ms = timeout_ms;
    wd->last_feed_mono_ms = now_mono_ms;
    wd->expired = false;
}

void watchdog_feed(watchdog_t *wd, uint32_t now_mono_ms) {
    wd->last_feed_mono_ms = now_mono_ms;
}

bool watchdog_check(watchdog_t *wd, uint32_t now_mono_ms) {
    if (!wd->expired && (now_mono_ms - wd->last_feed_mono_ms) >= wd->timeout_ms) {
        wd->expired = true;
    }
    return wd->expired;
}
