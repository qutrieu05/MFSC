#include "test_util.h"
#include "safety_supervisor.h"
#include <stddef.h>

static void test_outside_running_everything_is_off(void) {
    hal_outputs_t out;
    cell_state_t states[] = {CELL_STATE_BOOT, CELL_STATE_SELF_TEST, CELL_STATE_IDLE,
                              CELL_STATE_STARTING, CELL_STATE_STOPPING, CELL_STATE_SAFE_STOP,
                              CELL_STATE_FAULT, CELL_STATE_ESTOP};
    for (size_t i = 0; i < sizeof(states) / sizeof(states[0]); i++) {
        safety_supervisor_compute_outputs(states[i], 80, true, true, &out);
        CHECK(!out.motor_enable);
        CHECK(!out.safety_relay_closed);
        CHECK_EQ(0, out.motor_pwm_pct);
        CHECK(!out.pusher_extend); /* SF-07: retracted outside RUNNING, even if requested */
    }
}

static void test_running_applies_requested_values(void) {
    hal_outputs_t out;
    safety_supervisor_compute_outputs(CELL_STATE_RUNNING, 65, true, true, &out);
    CHECK(out.motor_enable);
    CHECK(out.safety_relay_closed);
    CHECK_EQ(65, out.motor_pwm_pct);
    CHECK(out.pusher_extend);
    CHECK(out.led_green);
    CHECK(!out.led_red);
}

static void test_pwm_percent_is_clamped(void) {
    hal_outputs_t out;
    safety_supervisor_compute_outputs(CELL_STATE_RUNNING, 250, true, false, &out);
    CHECK_EQ(100, out.motor_pwm_pct);
}

static void test_led_reflects_latched_states(void) {
    hal_outputs_t out;
    safety_supervisor_compute_outputs(CELL_STATE_ESTOP, 0, false, false, &out);
    CHECK(out.led_red);
    safety_supervisor_compute_outputs(CELL_STATE_FAULT, 0, false, false, &out);
    CHECK(out.led_red);
    safety_supervisor_compute_outputs(CELL_STATE_STARTING, 0, false, false, &out);
    CHECK(out.led_yellow);
}

int main(void) {
    test_outside_running_everything_is_off();
    test_running_applies_requested_values();
    test_pwm_percent_is_clamped();
    test_led_reflects_latched_states();
    TEST_SUMMARY_AND_RETURN();
}
