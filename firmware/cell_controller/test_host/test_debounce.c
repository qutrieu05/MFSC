#include "test_util.h"
#include "debounce.h"

static void test_short_glitch_is_ignored(void) {
    debounce_t d;
    debounce_init(&d, 30, false);
    CHECK(!debounce_update(&d, true, 0));   /* glitch starts */
    CHECK(!debounce_update(&d, true, 10));  /* only 10ms in, still not stable */
    CHECK(!debounce_update(&d, false, 15)); /* glitch ends before debounce window -> ignored */
    CHECK(!debounce_update(&d, false, 50));
}

static void test_sustained_change_becomes_stable(void) {
    debounce_t d;
    debounce_init(&d, 30, false);
    debounce_update(&d, true, 0);
    debounce_update(&d, true, 20);
    CHECK(debounce_update(&d, true, 35)); /* held true for >=30ms -> now stable true */
    CHECK(debounce_update(&d, true, 100));
}

static void test_debounce_from_true_initial_state(void) {
    debounce_t d;
    debounce_init(&d, 20, true);
    CHECK(debounce_update(&d, true, 0));    /* no change yet */
    CHECK(debounce_update(&d, false, 0));   /* candidate just started; still stable true */
    CHECK(!debounce_update(&d, false, 25)); /* held >=20ms -> now stable false */
}

int main(void) {
    test_short_glitch_is_ignored();
    test_sustained_change_becomes_stable();
    test_debounce_from_true_initial_state();
    TEST_SUMMARY_AND_RETURN();
}
