/* Command parser: decides ACCEPTED/REJECTED for an incoming control command and, if accepted,
 * drives cell_sm. Mirrors msfc.domain.enums.CommandAction/CommandResult/RejectReason so the
 * reason codes match control_cmd.v1/cmd_ack.v1 exactly (values, not just meaning).
 */
#ifndef MSFC_CMD_HANDLER_H
#define MSFC_CMD_HANDLER_H

#include <stdbool.h>
#include <stdint.h>
#include "cell_sm.h"

typedef enum {
    CMD_ACTION_START = 0,
    CMD_ACTION_STOP,
    CMD_ACTION_RESET,
    CMD_ACTION_SET_SPEED,
    CMD_ACTION_PUSHER_TEST,
} cmd_action_t;

typedef enum {
    CMD_RESULT_ACCEPTED = 0,
    CMD_RESULT_REJECTED,
} cmd_result_t;

typedef enum {
    REJECT_NONE = 0,
    REJECT_ESTOP_LATCHED,
    REJECT_FAULT_LATCHED,
    REJECT_SAFE_STOP_LATCHED,
    REJECT_NOT_IDLE,
    REJECT_NOT_RUNNING,
    REJECT_CAUSE_NOT_CLEARED,
    REJECT_INVALID_PARAMS,
} reject_reason_t;

typedef struct {
    cmd_result_t result;
    reject_reason_t reason; /* REJECT_NONE when result == CMD_RESULT_ACCEPTED */
} cmd_ack_t;

/* param is set_speed's target PWM percent (0..100); ignored for other actions.
 * Reads back estop/fault/safe_stop only to explain a REJECT_CAUSE_NOT_CLEARED on RESET —
 * it does not itself decide those conditions (safety_supervisor/fault_manager own that). */
cmd_ack_t cmd_handler_dispatch(cell_sm_t *sm, cmd_action_t action, int32_t param,
                                bool estop_active, bool fault_active, bool safe_stop_active);

#endif /* MSFC_CMD_HANDLER_H */
