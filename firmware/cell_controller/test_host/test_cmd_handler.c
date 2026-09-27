#include "test_util.h"
#include "cmd_handler.h"

static void test_start_accepted_from_idle(void) {
    cell_sm_t sm;
    cell_sm_init(&sm);
    cell_sm_self_test_passed(&sm);

    cmd_ack_t ack = cmd_handler_dispatch(&sm, CMD_ACTION_START, 0, false, false, false);
    CHECK_EQ(CMD_RESULT_ACCEPTED, ack.result);
    CHECK_EQ(CELL_STATE_STARTING, sm.state);
}

static void test_start_rejected_when_already_running(void) {
    cell_sm_t sm;
    cell_sm_init(&sm);
    cell_sm_self_test_passed(&sm);
    cell_sm_start(&sm);
    cell_sm_start_settled(&sm);

    cmd_ack_t ack = cmd_handler_dispatch(&sm, CMD_ACTION_START, 0, false, false, false);
    CHECK_EQ(CMD_RESULT_REJECTED, ack.result);
    CHECK_EQ(REJECT_NOT_IDLE, ack.reason);
}

static void test_start_rejected_with_specific_reason_when_estopped(void) {
    cell_sm_t sm;
    cell_sm_init(&sm);
    cell_sm_self_test_passed(&sm);
    cell_sm_update(&sm, true, false, false);

    cmd_ack_t ack = cmd_handler_dispatch(&sm, CMD_ACTION_START, 0, true, false, false);
    CHECK_EQ(CMD_RESULT_REJECTED, ack.result);
    CHECK_EQ(REJECT_ESTOP_LATCHED, ack.reason);
}

static void test_reset_rejected_while_cause_active(void) {
    cell_sm_t sm;
    cell_sm_init(&sm);
    cell_sm_self_test_passed(&sm);
    cell_sm_update(&sm, true, false, false); /* -> ESTOP */

    cmd_ack_t ack = cmd_handler_dispatch(&sm, CMD_ACTION_RESET, 0, true, false, false);
    CHECK_EQ(CMD_RESULT_REJECTED, ack.result);
    CHECK_EQ(REJECT_CAUSE_NOT_CLEARED, ack.reason);

    ack = cmd_handler_dispatch(&sm, CMD_ACTION_RESET, 0, false, false, false);
    CHECK_EQ(CMD_RESULT_ACCEPTED, ack.result);
    CHECK_EQ(CELL_STATE_IDLE, sm.state);
}

static void test_set_speed_validates_param_range(void) {
    cell_sm_t sm;
    cell_sm_init(&sm);
    cell_sm_self_test_passed(&sm);
    cell_sm_start(&sm);
    cell_sm_start_settled(&sm);

    cmd_ack_t ack = cmd_handler_dispatch(&sm, CMD_ACTION_SET_SPEED, 150, false, false, false);
    CHECK_EQ(CMD_RESULT_REJECTED, ack.result);
    CHECK_EQ(REJECT_INVALID_PARAMS, ack.reason);

    ack = cmd_handler_dispatch(&sm, CMD_ACTION_SET_SPEED, 50, false, false, false);
    CHECK_EQ(CMD_RESULT_ACCEPTED, ack.result);
}

static void test_stop_rejected_when_not_running(void) {
    cell_sm_t sm;
    cell_sm_init(&sm);
    cell_sm_self_test_passed(&sm);

    cmd_ack_t ack = cmd_handler_dispatch(&sm, CMD_ACTION_STOP, 0, false, false, false);
    CHECK_EQ(CMD_RESULT_REJECTED, ack.result);
    CHECK_EQ(REJECT_NOT_RUNNING, ack.reason);
}

int main(void) {
    test_start_accepted_from_idle();
    test_start_rejected_when_already_running();
    test_start_rejected_with_specific_reason_when_estopped();
    test_reset_rejected_while_cause_active();
    test_set_speed_validates_param_range();
    test_stop_rejected_when_not_running();
    TEST_SUMMARY_AND_RETURN();
}
