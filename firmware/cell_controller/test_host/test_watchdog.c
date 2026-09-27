#include "test_util.h"
#include "watchdog.h"

static void test_not_expired_before_timeout(void) {
    watchdog_t wd;
    watchdog_init(&wd, 500, 0);
    CHECK(!watchdog_check(&wd, 100));
    CHECK(!watchdog_check(&wd, 499));
}

static void test_expires_at_timeout_and_stays_latched(void) {
    watchdog_t wd;
    watchdog_init(&wd, 500, 0);
    CHECK(watchdog_check(&wd, 500));
    watchdog_feed(&wd, 600); /* feeding after expiry does NOT clear the latch -- SF-06 informational only */
    CHECK(watchdog_check(&wd, 601));
}

static void test_regular_feeding_prevents_expiry(void) {
    watchdog_t wd;
    watchdog_init(&wd, 200, 0);
    for (uint32_t t = 0; t <= 1000; t += 100) {
        watchdog_feed(&wd, t);
        CHECK(!watchdog_check(&wd, t));
    }
}

int main(void) {
    test_not_expired_before_timeout();
    test_expires_at_timeout_and_stays_latched();
    test_regular_feeding_prevents_expiry();
    TEST_SUMMARY_AND_RETURN();
}
