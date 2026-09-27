#include "safety_supervisor.h"
#include <string.h>

void safety_supervisor_compute_outputs(cell_state_t state, uint8_t requested_motor_pwm_pct,
                                        bool requested_motor_forward, bool requested_pusher_extend,
                                        hal_outputs_t *out) {
    memset(out, 0, sizeof(*out));

    if (state == CELL_STATE_RUNNING) {
        out->safety_relay_closed = true;
        out->motor_enable = true;
        out->motor_pwm_pct = requested_motor_pwm_pct > 100 ? 100 : requested_motor_pwm_pct;
        out->motor_forward = requested_motor_forward;
        out->pusher_extend = requested_pusher_extend;
    }
    /* Every other state: struct is already all-false/zero from memset — SF-07/SF-10 fail-safe. */

    switch (state) {
        case CELL_STATE_RUNNING:
            out->led_green = true;
            break;
        case CELL_STATE_STARTING:
        case CELL_STATE_STOPPING:
            out->led_yellow = true;
            break;
        case CELL_STATE_ESTOP:
        case CELL_STATE_FAULT:
        case CELL_STATE_SAFE_STOP:
            out->led_red = true;
            break;
        default:
            break; /* BOOT/SELF_TEST/IDLE: no LED lit */
    }
}
