/* Phase 2: P2.9 software safety simulator -- the 12 scenarios named in the PO's directive,
 * each against safety_interlock_t (the Phase 2 supervisor) driven through hal_host_mock-free
 * calls (pure logic, no HAL needed for these -- interlock decisions don't touch hal_outputs_t
 * directly; safety_supervisor.c from P1 still owns that mapping and is exercised separately in
 * test_hal_boundary_integration.c). Each scenario prints its name and asserts one deterministic
 * expected state/result -- this file IS the "simulator that can execute scenarios."
 */
#include "test_util.h"
#include "safety_interlock.h"
#include <stdio.h>

static void scenario(const char *name) {
    printf("  scenario: %s\n", name);
}

/* 1. Normal startup */
static void test_scenario_01_normal_startup(void) {
    scenario("01 normal startup");
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0);
    CHECK_EQ(SAFETY_STATE_SAFE_IDLE, safety_interlock_state(&sup));
    safety_interlock_self_test(&sup, true);
    safety_interlock_update(&sup, false, false, false, 0);
    CHECK_EQ(SAFETY_STATE_READY, safety_interlock_state(&sup));
}

/* 2. READY -> RUNNING */
static void test_scenario_02_ready_to_running(void) {
    scenario("02 READY -> RUNNING");
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0);
    safety_interlock_self_test(&sup, true);
    safety_interlock_update(&sup, false, false, false, 0);

    interlock_ack_t ack = safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    CHECK_EQ(CMD_RESULT_ACCEPTED, ack.result);
    CHECK_EQ(SAFETY_STATE_RUNNING, safety_interlock_state(&sup));
}

/* 3. RUNNING -> E-STOP */
static void test_scenario_03_running_to_estop(void) {
    scenario("03 RUNNING -> E-STOP");
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0);
    safety_interlock_self_test(&sup, true);
    safety_interlock_update(&sup, false, false, false, 0);
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);

    safety_interlock_update(&sup, true, false, false, 5);
    CHECK_EQ(SAFETY_STATE_ESTOP, safety_interlock_state(&sup));
}

/* 4. E-STOP reset */
static void test_scenario_04_estop_reset(void) {
    scenario("04 E-STOP reset");
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0);
    safety_interlock_self_test(&sup, true);
    safety_interlock_update(&sup, false, false, false, 0);
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    safety_interlock_update(&sup, true, false, false, 5);

    safety_interlock_update(&sup, false, false, false, 10); /* wire reconnected */
    CHECK_EQ(CMD_RESULT_ACCEPTED, safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0).result);
    CHECK(safety_interlock_confirm_recovery(&sup, 15));
    CHECK_EQ(SAFETY_STATE_READY, safety_interlock_state(&sup));
}

/* 5. RUNNING -> communication loss */
static void test_scenario_05_running_to_comm_loss(void) {
    scenario("05 RUNNING -> communication loss");
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0);
    safety_interlock_self_test(&sup, true);
    safety_interlock_feed_comm_heartbeat(&sup, 0);
    safety_interlock_update(&sup, false, false, false, 0);
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);

    safety_interlock_update(&sup, false, false, false, 500); /* no more heartbeats fed */
    CHECK_EQ(SAFETY_STATE_FAULT, safety_interlock_state(&sup));
}

/* 6. communication recovery */
static void test_scenario_06_communication_recovery(void) {
    scenario("06 communication recovery");
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0);
    safety_interlock_self_test(&sup, true);
    safety_interlock_feed_comm_heartbeat(&sup, 0);
    safety_interlock_update(&sup, false, false, false, 0);
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    safety_interlock_update(&sup, false, false, false, 500);

    safety_interlock_feed_comm_heartbeat(&sup, 510);
    safety_interlock_update(&sup, false, false, false, 510);
    CHECK_EQ(CMD_RESULT_ACCEPTED, safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0).result);
    CHECK(safety_interlock_confirm_recovery(&sup, 520));
    CHECK_EQ(SAFETY_STATE_READY, safety_interlock_state(&sup));
}

/* 7. RUNNING -> motor fault */
static void test_scenario_07_running_to_motor_fault(void) {
    scenario("07 RUNNING -> motor fault");
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0);
    safety_interlock_self_test(&sup, true);
    safety_interlock_update(&sup, false, false, false, 0);
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);

    safety_interlock_update(&sup, false, true, false, 5);
    CHECK_EQ(SAFETY_STATE_FAULT, safety_interlock_state(&sup));
    CHECK_EQ(INTERLOCK_REJECT_MOTOR_FAULT,
             safety_interlock_dispatch(&sup, CMD_ACTION_SET_SPEED, 40).interlock_reason);
}

/* 8. RUNNING -> sensor fault */
static void test_scenario_08_running_to_sensor_fault(void) {
    scenario("08 RUNNING -> sensor fault");
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0);
    safety_interlock_self_test(&sup, true);
    safety_interlock_update(&sup, false, false, false, 0);
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);

    safety_interlock_update(&sup, false, false, true, 5);
    CHECK_EQ(SAFETY_STATE_FAULT, safety_interlock_state(&sup));
    CHECK_EQ(INTERLOCK_REJECT_SENSOR_FAULT,
             safety_interlock_dispatch(&sup, CMD_ACTION_PUSHER_TEST, 0).interlock_reason);
}

/* 9. invalid command */
static void test_scenario_09_invalid_command(void) {
    scenario("09 invalid command");
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0);
    safety_interlock_self_test(&sup, true);
    safety_interlock_update(&sup, false, false, false, 0);

    interlock_ack_t ack = safety_interlock_dispatch(&sup, (cmd_action_t)123, 0);
    CHECK_EQ(CMD_RESULT_REJECTED, ack.result);
    CHECK_EQ(REJECT_INVALID_PARAMS, ack.cmd_reason);
    /* Deterministic: rejecting an unknown command must not itself change the safety state. */
    CHECK_EQ(SAFETY_STATE_READY, safety_interlock_state(&sup));
}

/* 10. FAULT -> recovery */
static void test_scenario_10_fault_to_recovery(void) {
    scenario("10 FAULT -> recovery");
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0);
    safety_interlock_self_test(&sup, true);
    safety_interlock_update(&sup, false, false, false, 0);
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    safety_interlock_update(&sup, false, true, false, 5); /* motor fault -> FAULT */

    safety_interlock_update(&sup, false, false, false, 10); /* condition cleared */
    CHECK_EQ(CMD_RESULT_ACCEPTED, safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0).result);
    CHECK_EQ(SAFETY_STATE_RECOVERY, safety_interlock_state(&sup));
}

/* 11. watchdog timeout */
static void test_scenario_11_watchdog_timeout(void) {
    scenario("11 watchdog timeout");
    safety_interlock_t sup;
    safety_interlock_init(&sup, 200, 0);
    safety_interlock_self_test(&sup, true);
    safety_interlock_feed_comm_heartbeat(&sup, 0);
    safety_interlock_update(&sup, false, false, false, 0);
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);

    safety_interlock_update(&sup, false, false, false, 199);
    CHECK_EQ(SAFETY_STATE_RUNNING, safety_interlock_state(&sup)); /* not yet */
    safety_interlock_update(&sup, false, false, false, 200);
    CHECK_EQ(SAFETY_STATE_FAULT, safety_interlock_state(&sup)); /* timed out */
}

/* 12. repeated fault */
static void test_scenario_12_repeated_fault(void) {
    scenario("12 repeated fault");
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0);
    safety_interlock_self_test(&sup, true);
    safety_interlock_update(&sup, false, false, false, 0);
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);

    /* First fault + full recovery cycle. */
    safety_interlock_update(&sup, false, true, false, 5);
    safety_interlock_update(&sup, false, false, false, 10);
    safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0);
    CHECK(safety_interlock_confirm_recovery(&sup, 15));
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    CHECK_EQ(SAFETY_STATE_RUNNING, safety_interlock_state(&sup));

    /* Same fault condition happens again -- must be caught again, not suppressed by history. */
    safety_interlock_update(&sup, false, true, false, 20);
    CHECK_EQ(SAFETY_STATE_FAULT, safety_interlock_state(&sup));
    CHECK_EQ(CMD_RESULT_REJECTED, safety_interlock_dispatch(&sup, CMD_ACTION_START, 0).result);
}

int main(void) {
    test_scenario_01_normal_startup();
    test_scenario_02_ready_to_running();
    test_scenario_03_running_to_estop();
    test_scenario_04_estop_reset();
    test_scenario_05_running_to_comm_loss();
    test_scenario_06_communication_recovery();
    test_scenario_07_running_to_motor_fault();
    test_scenario_08_running_to_sensor_fault();
    test_scenario_09_invalid_command();
    test_scenario_10_fault_to_recovery();
    test_scenario_11_watchdog_timeout();
    test_scenario_12_repeated_fault();
    TEST_SUMMARY_AND_RETURN();
}
