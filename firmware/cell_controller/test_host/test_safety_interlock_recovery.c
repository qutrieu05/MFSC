/* Phase 2: P2.8 fault/recovery determinism. For each fault type: trigger -> resulting state ->
 * blocked operations -> reset condition -> recovery condition -> final state. Also proves
 * "avoid automatic recovery where it could violate safety assumptions" (P2.8): a new unsafe
 * condition appearing between an accepted RESET and confirm_recovery() must block the confirm.
 */
#include "test_util.h"
#include "safety_interlock.h"

static void boot_to_running(safety_interlock_t *sup) {
    safety_interlock_init(sup, 500, 0);
    safety_interlock_self_test(sup, true);
    safety_interlock_feed_comm_heartbeat(sup, 0);
    safety_interlock_update(sup, false, false, false, 0);
    safety_interlock_dispatch(sup, CMD_ACTION_START, 0);
}

/* ---- ESTOP: trigger=estop_active -> FAULT-class latch (ESTOP) -> all motion blocked ---- */
/* ---- -> reset condition: estop_active false -> recovery: confirm_recovery() -> READY ---- */
static void test_recovery_matrix_estop(void) {
    safety_interlock_t sup;
    boot_to_running(&sup);

    safety_interlock_update(&sup, true, false, false, 10); /* trigger */
    CHECK_EQ(SAFETY_STATE_ESTOP, safety_interlock_state(&sup));
    CHECK_EQ(CMD_RESULT_REJECTED, safety_interlock_dispatch(&sup, CMD_ACTION_START, 0).result);

    interlock_ack_t reset_ack = safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0);
    CHECK_EQ(CMD_RESULT_REJECTED, reset_ack.result); /* cause (estop) not cleared yet */

    safety_interlock_update(&sup, false, false, false, 20); /* reset condition met */
    reset_ack = safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0);
    CHECK_EQ(CMD_RESULT_ACCEPTED, reset_ack.result);
    CHECK(safety_interlock_confirm_recovery(&sup, 25)); /* recovery condition met */
    CHECK_EQ(SAFETY_STATE_READY, safety_interlock_state(&sup)); /* final state */
}

/* ---- motor fault: trigger=motor_fault -> FAULT -> motion blocked (motor-fault reason) ---- */
static void test_recovery_matrix_motor_fault(void) {
    safety_interlock_t sup;
    boot_to_running(&sup);

    safety_interlock_update(&sup, false, true, false, 10); /* trigger */
    CHECK_EQ(SAFETY_STATE_FAULT, safety_interlock_state(&sup));
    interlock_ack_t blocked = safety_interlock_dispatch(&sup, CMD_ACTION_SET_SPEED, 30);
    CHECK_EQ(INTERLOCK_REJECT_MOTOR_FAULT, blocked.interlock_reason);

    interlock_ack_t reset_ack = safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0);
    CHECK_EQ(CMD_RESULT_REJECTED, reset_ack.result); /* motor fault still active */

    safety_interlock_update(&sup, false, false, false, 20); /* reset condition met */
    reset_ack = safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0);
    CHECK_EQ(CMD_RESULT_ACCEPTED, reset_ack.result);
    CHECK(safety_interlock_confirm_recovery(&sup, 25));
    CHECK_EQ(SAFETY_STATE_READY, safety_interlock_state(&sup));
}

/* ---- sensor fault: same shape as motor fault, distinct reason ---- */
static void test_recovery_matrix_sensor_fault(void) {
    safety_interlock_t sup;
    boot_to_running(&sup);

    safety_interlock_update(&sup, false, false, true, 10);
    CHECK_EQ(SAFETY_STATE_FAULT, safety_interlock_state(&sup));
    interlock_ack_t blocked = safety_interlock_dispatch(&sup, CMD_ACTION_PUSHER_TEST, 0);
    CHECK_EQ(INTERLOCK_REJECT_SENSOR_FAULT, blocked.interlock_reason);

    safety_interlock_update(&sup, false, false, false, 20);
    CHECK_EQ(CMD_RESULT_ACCEPTED, safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0).result);
    CHECK(safety_interlock_confirm_recovery(&sup, 25));
    CHECK_EQ(SAFETY_STATE_READY, safety_interlock_state(&sup));
}

/* ---- self-test failure: trigger before READY -> FAULT -> blocked -> reset -> recovery ---- */
static void test_recovery_matrix_self_test_failure(void) {
    safety_interlock_t sup;
    safety_interlock_init(&sup, 500, 0);
    safety_interlock_self_test(&sup, false); /* trigger */
    safety_interlock_update(&sup, false, false, false, 0);
    CHECK_EQ(SAFETY_STATE_FAULT, safety_interlock_state(&sup));
    CHECK_EQ(CMD_RESULT_REJECTED, safety_interlock_dispatch(&sup, CMD_ACTION_START, 0).result);

    safety_interlock_self_test(&sup, true); /* reset condition: self-test re-run and passes */
    safety_interlock_update(&sup, false, false, false, 10);
    CHECK_EQ(CMD_RESULT_ACCEPTED, safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0).result);
    CHECK(safety_interlock_confirm_recovery(&sup, 15));
    CHECK_EQ(SAFETY_STATE_READY, safety_interlock_state(&sup));
}

/* ---- P2.8: no automatic recovery if a new condition appears before confirm ---- */
static void test_confirm_recovery_blocked_by_new_condition(void) {
    safety_interlock_t sup;
    boot_to_running(&sup);
    safety_interlock_update(&sup, true, false, false, 10); /* ESTOP */
    safety_interlock_update(&sup, false, false, false, 20); /* cleared */
    CHECK_EQ(CMD_RESULT_ACCEPTED, safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0).result);
    CHECK_EQ(SAFETY_STATE_RECOVERY, safety_interlock_state(&sup));

    /* A NEW motor fault appears while still in RECOVERY, before confirmation. */
    safety_interlock_update(&sup, false, true, false, 22);
    CHECK(!safety_interlock_confirm_recovery(&sup, 25));
    /* Underlying cell_sm has already re-latched to FAULT via update()'s fault_active path;
     * the safety view must not claim READY either way. */
    CHECK(safety_interlock_state(&sup) != SAFETY_STATE_READY);
}

static void test_confirm_recovery_without_pending_reset_fails(void) {
    safety_interlock_t sup;
    boot_to_running(&sup);
    /* No fault, no reset accepted -- nothing to confirm. */
    CHECK(!safety_interlock_confirm_recovery(&sup, 1));
}

int main(void) {
    test_recovery_matrix_estop();
    test_recovery_matrix_motor_fault();
    test_recovery_matrix_sensor_fault();
    test_recovery_matrix_self_test_failure();
    test_confirm_recovery_blocked_by_new_condition();
    test_confirm_recovery_without_pending_reset_fails();
    TEST_SUMMARY_AND_RETURN();
}
