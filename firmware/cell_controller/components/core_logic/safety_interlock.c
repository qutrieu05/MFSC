#include "safety_interlock.h"

const char *safety_state_name(safety_state_t state) {
    switch (state) {
        case SAFETY_STATE_SAFE_IDLE: return "SAFE_IDLE";
        case SAFETY_STATE_READY: return "READY";
        case SAFETY_STATE_RUNNING: return "RUNNING";
        case SAFETY_STATE_FAULT: return "FAULT";
        case SAFETY_STATE_ESTOP: return "ESTOP";
        case SAFETY_STATE_RECOVERY: return "RECOVERY";
        default: return "UNKNOWN";
    }
}

void safety_interlock_init(safety_interlock_t *sup, uint32_t comm_heartbeat_timeout_ms, uint32_t now_mono_ms) {
    cell_sm_init(&sup->sm);
    fault_manager_init(&sup->faults);
    watchdog_init(&sup->comm_watchdog, comm_heartbeat_timeout_ms, now_mono_ms);
    sup->estop_active = false;
    sup->motor_fault = false;
    sup->sensor_fault = false;
    sup->comm_loss = false;
    sup->recovery_pending = false;
}

void safety_interlock_self_test(safety_interlock_t *sup, bool passed) {
    if (passed) {
        fault_manager_ack(&sup->faults, FAULT_F050_SELF_TEST_FAILED);
        cell_sm_self_test_passed(&sup->sm);
    } else {
        fault_manager_raise(&sup->faults, FAULT_F050_SELF_TEST_FAILED);
    }
}

void safety_interlock_feed_comm_heartbeat(safety_interlock_t *sup, uint32_t now_mono_ms) {
    watchdog_feed(&sup->comm_watchdog, now_mono_ms);
}

/* Deliberately NOT watchdog_check(): that latches `expired` permanently once tripped (correct
 * for P1's one-shot device-reset watchdog -- a real reboot re-inits it), but comm loss must be
 * able to clear once heartbeats resume (P2.5's "disconnect -> recovery", P2.6's "repeated
 * timeout"). This reuses watchdog_t's feed-tracking data (last_feed_mono_ms/timeout_ms, still
 * fed via the unmodified watchdog_feed()) with a live, self-clearing freshness check instead --
 * see D-039, DECISIONS.md. */
static bool comm_heartbeat_fresh(const watchdog_t *wd, uint32_t now_mono_ms) {
    return (now_mono_ms - wd->last_feed_mono_ms) < wd->timeout_ms;
}

static bool any_fault_active(const safety_interlock_t *sup) {
    return sup->motor_fault || sup->sensor_fault || sup->comm_loss
           || fault_manager_any_latched_active(&sup->faults);
}

void safety_interlock_update(safety_interlock_t *sup, bool estop_active, bool motor_fault,
                              bool sensor_fault, uint32_t now_mono_ms) {
    sup->estop_active = estop_active;
    sup->motor_fault = motor_fault;
    sup->sensor_fault = sensor_fault;
    sup->comm_loss = !comm_heartbeat_fresh(&sup->comm_watchdog, now_mono_ms);

    cell_sm_update(&sup->sm, estop_active, any_fault_active(sup), false);
}

safety_state_t safety_interlock_state(const safety_interlock_t *sup) {
    switch (sup->sm.state) {
        case CELL_STATE_BOOT:
        case CELL_STATE_SELF_TEST:
            return SAFETY_STATE_SAFE_IDLE;
        case CELL_STATE_IDLE:
            return sup->recovery_pending ? SAFETY_STATE_RECOVERY : SAFETY_STATE_READY;
        case CELL_STATE_STARTING:
        case CELL_STATE_RUNNING:
        case CELL_STATE_STOPPING:
            return SAFETY_STATE_RUNNING;
        case CELL_STATE_FAULT:
        case CELL_STATE_SAFE_STOP:
            return SAFETY_STATE_FAULT;
        case CELL_STATE_ESTOP:
            return SAFETY_STATE_ESTOP;
        default:
            return SAFETY_STATE_SAFE_IDLE;
    }
}

static bool is_motion_command(cmd_action_t action) {
    return action == CMD_ACTION_START || action == CMD_ACTION_SET_SPEED || action == CMD_ACTION_PUSHER_TEST;
}

interlock_ack_t safety_interlock_dispatch(safety_interlock_t *sup, cmd_action_t action, int32_t param) {
    interlock_ack_t ack = {CMD_RESULT_REJECTED, INTERLOCK_REJECT_FROM_CMD_HANDLER, REJECT_NONE};

    if (action == CMD_ACTION_RESET) {
        cmd_ack_t cmd_ack = cmd_handler_dispatch(&sup->sm, action, param, sup->estop_active,
                                                  any_fault_active(sup), false);
        if (cmd_ack.result == CMD_RESULT_ACCEPTED) {
            sup->recovery_pending = true; /* P2.8: no automatic recovery -- must confirm */
            ack.result = CMD_RESULT_ACCEPTED;
            ack.interlock_reason = INTERLOCK_OK;
            return ack;
        }
        ack.cmd_reason = cmd_ack.reason;
        return ack;
    }

    if (is_motion_command(action)) {
        if (sup->motor_fault) {
            ack.interlock_reason = INTERLOCK_REJECT_MOTOR_FAULT;
            return ack;
        }
        if (sup->sensor_fault) {
            ack.interlock_reason = INTERLOCK_REJECT_SENSOR_FAULT;
            return ack;
        }
        if (sup->comm_loss) {
            ack.interlock_reason = INTERLOCK_REJECT_COMM_LOSS;
            return ack;
        }
        if (sup->recovery_pending) {
            ack.interlock_reason = INTERLOCK_REJECT_RECOVERY_NOT_COMPLETE;
            return ack;
        }
    }

    cmd_ack_t cmd_ack = cmd_handler_dispatch(&sup->sm, action, param, sup->estop_active,
                                              any_fault_active(sup), false);
    ack.result = cmd_ack.result;
    ack.cmd_reason = cmd_ack.reason;
    ack.interlock_reason = (cmd_ack.result == CMD_RESULT_ACCEPTED)
                                ? INTERLOCK_OK
                                : INTERLOCK_REJECT_FROM_CMD_HANDLER;
    return ack;
}

bool safety_interlock_confirm_recovery(safety_interlock_t *sup, uint32_t now_mono_ms) {
    if (!sup->recovery_pending) {
        return false;
    }
    sup->comm_loss = !comm_heartbeat_fresh(&sup->comm_watchdog, now_mono_ms);
    if (sup->estop_active || any_fault_active(sup)) {
        return false; /* still unsafe -- stays in RECOVERY */
    }
    sup->recovery_pending = false;
    return true;
}
