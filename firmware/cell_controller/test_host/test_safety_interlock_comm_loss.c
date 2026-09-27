/* Phase 2: P2.5 (communication loss) + P2.6 (watchdog integration). Does not assume MQTT/Wi-Fi
 * is itself a safety mechanism -- comm loss here means "the comm watchdog (fed by incoming
 * heartbeats) timed out," and the ONLY safety behavior asserted is what safety_interlock does
 * about it (fault_active -> FAULT, motion commands blocked).
 */
#include "test_util.h"
#include "safety_interlock.h"

#define TIMEOUT_MS 500u

static void boot_to_running(safety_interlock_t *sup) {
    safety_interlock_init(sup, TIMEOUT_MS, 0);
    safety_interlock_self_test(sup, true);
    safety_interlock_feed_comm_heartbeat(sup, 0);
    safety_interlock_update(sup, false, false, false, 0);
    safety_interlock_dispatch(sup, CMD_ACTION_START, 0);
}

/* ---------------------------------------------------------- normal heartbeat */
static void test_regular_heartbeats_keep_the_system_running(void) {
    safety_interlock_t sup;
    boot_to_running(&sup);
    for (uint32_t t = 0; t <= 3000; t += 100) {
        safety_interlock_feed_comm_heartbeat(&sup, t);
        safety_interlock_update(&sup, false, false, false, t);
        CHECK_EQ(SAFETY_STATE_RUNNING, safety_interlock_state(&sup));
    }
}

/* ---------------------------------------------------------- missed heartbeat / timeout */
static void test_missed_heartbeats_trip_into_fault(void) {
    safety_interlock_t sup;
    boot_to_running(&sup);

    safety_interlock_update(&sup, false, false, false, 100); /* still within timeout */
    CHECK_EQ(SAFETY_STATE_RUNNING, safety_interlock_state(&sup));

    safety_interlock_update(&sup, false, false, false, TIMEOUT_MS); /* exactly at timeout */
    CHECK_EQ(SAFETY_STATE_FAULT, safety_interlock_state(&sup));
}

static void test_motion_commands_blocked_during_comm_loss(void) {
    safety_interlock_t sup;
    boot_to_running(&sup);
    safety_interlock_update(&sup, false, false, false, TIMEOUT_MS);

    interlock_ack_t ack = safety_interlock_dispatch(&sup, CMD_ACTION_SET_SPEED, 40);
    CHECK_EQ(CMD_RESULT_REJECTED, ack.result);
    /* is_motion_command() checks comm_loss before falling through to cmd_handler, so this is
     * reported precisely as comm loss, not a generic "fault latched." */
    CHECK_EQ(INTERLOCK_REJECT_COMM_LOSS, ack.interlock_reason);
}

/* ---------------------------------------------------------- disconnect -> recovery */
static void test_recovery_after_comm_loss_requires_reset_and_confirm(void) {
    safety_interlock_t sup;
    boot_to_running(&sup);
    safety_interlock_update(&sup, false, false, false, TIMEOUT_MS);
    CHECK_EQ(SAFETY_STATE_FAULT, safety_interlock_state(&sup));

    /* Heartbeats resume, but the fault is latched -- reset must still be rejected until the
     * next update() call observes comm_loss cleared. */
    safety_interlock_feed_comm_heartbeat(&sup, TIMEOUT_MS + 10);
    interlock_ack_t reset_ack = safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0);
    CHECK_EQ(CMD_RESULT_REJECTED, reset_ack.result);

    safety_interlock_update(&sup, false, false, false, TIMEOUT_MS + 10);
    reset_ack = safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0);
    CHECK_EQ(CMD_RESULT_ACCEPTED, reset_ack.result);
    CHECK_EQ(SAFETY_STATE_RECOVERY, safety_interlock_state(&sup));

    CHECK(safety_interlock_confirm_recovery(&sup, TIMEOUT_MS + 20));
    CHECK_EQ(SAFETY_STATE_READY, safety_interlock_state(&sup));
}

/* ---------------------------------------------------------- repeated timeout */
static void test_repeated_comm_loss_after_recovery_faults_again(void) {
    safety_interlock_t sup;
    boot_to_running(&sup);
    safety_interlock_update(&sup, false, false, false, TIMEOUT_MS);
    safety_interlock_feed_comm_heartbeat(&sup, TIMEOUT_MS + 10);
    safety_interlock_update(&sup, false, false, false, TIMEOUT_MS + 10);
    safety_interlock_dispatch(&sup, CMD_ACTION_RESET, 0);
    safety_interlock_confirm_recovery(&sup, TIMEOUT_MS + 20);
    safety_interlock_dispatch(&sup, CMD_ACTION_START, 0);
    CHECK_EQ(SAFETY_STATE_RUNNING, safety_interlock_state(&sup));

    /* Heartbeats stop a second time -- must fault again, not stay latched-open from before. */
    uint32_t second_timeout = TIMEOUT_MS + 20 + TIMEOUT_MS;
    safety_interlock_update(&sup, false, false, false, second_timeout);
    CHECK_EQ(SAFETY_STATE_FAULT, safety_interlock_state(&sup));
}

int main(void) {
    test_regular_heartbeats_keep_the_system_running();
    test_missed_heartbeats_trip_into_fault();
    test_motion_commands_blocked_during_comm_loss();
    test_recovery_after_comm_loss_requires_reset_and_confirm();
    test_repeated_comm_loss_after_recovery_faults_again();
    TEST_SUMMARY_AND_RETURN();
}
