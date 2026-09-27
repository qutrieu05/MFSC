/* Phase 2: P2.1 (safety state machine), P2.2 (software E-STOP event), P2.7 (invalid/malformed
 * command handling). Uses only safety_interlock's public API -- never pokes cell_sm/fault_manager
 * fields directly, matching how a real caller (app_main's control_task, later) would use it.
 */
#include "test_util.h"
#include "safety_interlock.h"
#include <string.h>

static void boot_to_ready(safety_interlock_t *sup) {
    safety_interlock_init(sup, /*comm_timeout_ms=*/500, /*now=*/0);
    safety_interlock_self_test(sup, true);
    safety_interlock_update(sup, false, false, false, 0);
}

/* ---------------------------------------------------------- P2.1 state machine */
static void test_boot_starts_in_safe_idle(void) {
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0);
    CHECK_EQ(SAFETY_STATE_SAFE_IDLE, safety_interlock_state(&sup));
}

static void test_self_test_pass_reaches_ready(void) {
    safety_interlock_t sup;
    boot_to_ready(&sup);
    CHECK_EQ(SAFETY_STATE_READY, safety_interlock_state(&sup));
}

static void test_self_test_failure_reaches_fault_not_ready(void) {
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0);
    safety_interlock_self_test(&sup, false);
    safety_interlock_update(&sup, false, false, false, 0);
    CHECK_EQ(SAFETY_STATE_FAULT, safety_interlock_state(&sup));
}

static void test_ready_to_running_via_start(void) {
    safety_interlock_t sup;
    boot_to_ready(&sup);

    interlock_ack_t ack = safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    CHECK_EQ(CMD_RESULT_ACCEPTED, ack.result);
    /* STARTING is still reported as RUNNING in the safety view (P2.1: motion may be live). */
    CHECK_EQ(SAFETY_STATE_RUNNING, safety_interlock_state(&sup));
}

/* ---------------------------------------------------------- P2.2 software E-STOP event */
static void test_estop_forces_safe_state_from_running(void) {
    safety_interlock_t sup;
    boot_to_ready(&sup);
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    CHECK_EQ(SAFETY_STATE_RUNNING, safety_interlock_state(&sup));

    safety_interlock_update(&sup, /*estop_active=*/true, false, false, 10);
    CHECK_EQ(SAFETY_STATE_ESTOP, safety_interlock_state(&sup));
}

static void test_estop_inhibits_new_run_commands(void) {
    safety_interlock_t sup;
    boot_to_ready(&sup);
    safety_interlock_update(&sup, true, false, false, 0); /* ESTOP straight from READY */

    interlock_ack_t ack = safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    CHECK_EQ(CMD_RESULT_REJECTED, ack.result);
    CHECK_EQ(INTERLOCK_REJECT_FROM_CMD_HANDLER, ack.interlock_reason);
    CHECK_EQ(REJECT_ESTOP_LATCHED, ack.cmd_reason);
}

static void test_estop_inhibits_actuator_commands_while_running(void) {
    safety_interlock_t sup;
    boot_to_ready(&sup);
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    safety_interlock_update(&sup, true, false, false, 5); /* ESTOP mid-run */

    interlock_ack_t ack = safety_interlock_dispatch(&sup, CMD_ACTION_SET_SPEED, 50);
    CHECK_EQ(CMD_RESULT_REJECTED, ack.result);
    CHECK_EQ(REJECT_ESTOP_LATCHED, ack.cmd_reason);
}

static void test_estop_recovery_requires_reset_then_confirm(void) {
    safety_interlock_t sup;
    boot_to_ready(&sup);
    safety_interlock_update(&sup, true, false, false, 0);
    CHECK_EQ(SAFETY_STATE_ESTOP, safety_interlock_state(&sup));

    /* Wire still cut -- reset must be rejected (cause not cleared). */
    interlock_ack_t reset_ack = safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0);
    CHECK_EQ(CMD_RESULT_REJECTED, reset_ack.result);
    CHECK_EQ(REJECT_CAUSE_NOT_CLEARED, reset_ack.cmd_reason);

    /* Wire reconnected: reset now accepted, but the system must sit in RECOVERY, not READY. */
    safety_interlock_update(&sup, false, false, false, 20);
    reset_ack = safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0);
    CHECK_EQ(CMD_RESULT_ACCEPTED, reset_ack.result);
    CHECK_EQ(SAFETY_STATE_RECOVERY, safety_interlock_state(&sup));

    /* START must still be rejected until recovery is explicitly confirmed (P2.8). */
    interlock_ack_t start_ack = safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    CHECK_EQ(CMD_RESULT_REJECTED, start_ack.result);
    CHECK_EQ(INTERLOCK_REJECT_RECOVERY_NOT_COMPLETE, start_ack.interlock_reason);

    CHECK(safety_interlock_confirm_recovery(&sup, 25));
    CHECK_EQ(SAFETY_STATE_READY, safety_interlock_state(&sup));

    start_ack = safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    CHECK_EQ(CMD_RESULT_ACCEPTED, start_ack.result);
}

static void test_estop_state_is_observable_by_name(void) {
    safety_interlock_t sup;
    boot_to_ready(&sup);
    safety_interlock_update(&sup, true, false, false, 0);
    CHECK_EQ(0, strcmp("ESTOP", safety_state_name(safety_interlock_state(&sup))));
}

/* ---------------------------------------------------------- P2.7 invalid/malformed commands */
static void test_unknown_command_is_rejected(void) {
    safety_interlock_t sup;
    boot_to_ready(&sup);
    /* Out-of-range action value -- represents a malformed/unknown command from the wire. */
    interlock_ack_t ack = safety_interlock_dispatch(&sup, (cmd_action_t)99, 0);
    CHECK_EQ(CMD_RESULT_REJECTED, ack.result);
    CHECK_EQ(REJECT_INVALID_PARAMS, ack.cmd_reason);
}

static void test_invalid_parameter_is_rejected(void) {
    safety_interlock_t sup;
    boot_to_ready(&sup);
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    interlock_ack_t ack = safety_interlock_dispatch(&sup, CMD_ACTION_SET_SPEED, 999);
    CHECK_EQ(CMD_RESULT_REJECTED, ack.result);
    CHECK_EQ(REJECT_INVALID_PARAMS, ack.cmd_reason);
}

static void test_motion_command_while_fault_is_rejected(void) {
    safety_interlock_t sup;
    boot_to_ready(&sup);
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    safety_interlock_update(&sup, false, /*motor_fault=*/true, false, 5); /* -> FAULT */
    CHECK_EQ(SAFETY_STATE_FAULT, safety_interlock_state(&sup));

    interlock_ack_t ack = safety_interlock_dispatch(&sup, CMD_ACTION_SET_SPEED, 50);
    CHECK_EQ(CMD_RESULT_REJECTED, ack.result);
    CHECK_EQ(INTERLOCK_REJECT_MOTOR_FAULT, ack.interlock_reason);
}

static void test_command_received_before_ready_is_rejected(void) {
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0); /* still SAFE_IDLE -- self-test not yet run */
    interlock_ack_t ack = safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    CHECK_EQ(CMD_RESULT_REJECTED, ack.result);
    CHECK_EQ(REJECT_NOT_IDLE, ack.cmd_reason);
}

static void test_invalid_state_transition_stop_while_idle_is_rejected(void) {
    safety_interlock_t sup;
    boot_to_ready(&sup);
    interlock_ack_t ack = safety_interlock_dispatch(&sup, CMD_ACTION_STOP, 0);
    CHECK_EQ(CMD_RESULT_REJECTED, ack.result);
    CHECK_EQ(REJECT_NOT_RUNNING, ack.cmd_reason);
}

int main(void) {
    test_boot_starts_in_safe_idle();
    test_self_test_pass_reaches_ready();
    test_self_test_failure_reaches_fault_not_ready();
    test_ready_to_running_via_start();
    test_estop_forces_safe_state_from_running();
    test_estop_inhibits_new_run_commands();
    test_estop_inhibits_actuator_commands_while_running();
    test_estop_recovery_requires_reset_then_confirm();
    test_estop_state_is_observable_by_name();
    test_unknown_command_is_rejected();
    test_invalid_parameter_is_rejected();
    test_motion_command_while_fault_is_rejected();
    test_command_received_before_ready_is_rejected();
    test_invalid_state_transition_stop_while_idle_is_rejected();
    TEST_SUMMARY_AND_RETURN();
}
