#include "cmd_handler.h"

static reject_reason_t latched_reason(cell_state_t state) {
    switch (state) {
        case CELL_STATE_ESTOP: return REJECT_ESTOP_LATCHED;
        case CELL_STATE_FAULT: return REJECT_FAULT_LATCHED;
        case CELL_STATE_SAFE_STOP: return REJECT_SAFE_STOP_LATCHED;
        default: return REJECT_NONE;
    }
}

cmd_ack_t cmd_handler_dispatch(cell_sm_t *sm, cmd_action_t action, int32_t param,
                                bool estop_active, bool fault_active, bool safe_stop_active) {
    cmd_ack_t ack = {CMD_RESULT_REJECTED, REJECT_NONE};

    switch (action) {
        case CMD_ACTION_START:
            if (cell_sm_is_latched(sm->state)) {
                ack.reason = latched_reason(sm->state);
                return ack;
            }
            if (!cell_sm_start(sm)) {
                ack.reason = REJECT_NOT_IDLE;
                return ack;
            }
            ack.result = CMD_RESULT_ACCEPTED;
            return ack;

        case CMD_ACTION_STOP:
            if (cell_sm_is_latched(sm->state)) {
                ack.reason = latched_reason(sm->state);
                return ack;
            }
            if (!cell_sm_stop(sm)) {
                ack.reason = REJECT_NOT_RUNNING;
                return ack;
            }
            ack.result = CMD_RESULT_ACCEPTED;
            return ack;

        case CMD_ACTION_RESET:
            if (!cell_sm_is_latched(sm->state)) {
                ack.reason = REJECT_INVALID_PARAMS; /* nothing latched to reset */
                return ack;
            }
            if (!cell_sm_reset(sm, estop_active, fault_active, safe_stop_active)) {
                ack.reason = REJECT_CAUSE_NOT_CLEARED;
                return ack;
            }
            ack.result = CMD_RESULT_ACCEPTED;
            return ack;

        case CMD_ACTION_SET_SPEED:
            if (cell_sm_is_latched(sm->state)) {
                ack.reason = latched_reason(sm->state);
                return ack;
            }
            if (sm->state != CELL_STATE_RUNNING && sm->state != CELL_STATE_STARTING) {
                ack.reason = REJECT_NOT_RUNNING;
                return ack;
            }
            if (param < 0 || param > 100) {
                ack.reason = REJECT_INVALID_PARAMS;
                return ack;
            }
            ack.result = CMD_RESULT_ACCEPTED;
            return ack;

        case CMD_ACTION_PUSHER_TEST:
            /* Manual jog for commissioning — only meaningful while nothing else is moving. */
            if (cell_sm_is_latched(sm->state)) {
                ack.reason = latched_reason(sm->state);
                return ack;
            }
            if (sm->state != CELL_STATE_IDLE) {
                ack.reason = REJECT_NOT_IDLE;
                return ack;
            }
            ack.result = CMD_RESULT_ACCEPTED;
            return ack;

        default:
            ack.reason = REJECT_INVALID_PARAMS;
            return ack;
    }
}
