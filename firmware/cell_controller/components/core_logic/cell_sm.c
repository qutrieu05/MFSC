#include "cell_sm.h"
#include <stddef.h>

void cell_sm_init(cell_sm_t *sm) {
    sm->state = CELL_STATE_BOOT;
}

const char *cell_sm_state_name(cell_state_t state) {
    switch (state) {
        case CELL_STATE_BOOT: return "BOOT";
        case CELL_STATE_SELF_TEST: return "SELF_TEST";
        case CELL_STATE_IDLE: return "IDLE";
        case CELL_STATE_STARTING: return "STARTING";
        case CELL_STATE_RUNNING: return "RUNNING";
        case CELL_STATE_STOPPING: return "STOPPING";
        case CELL_STATE_SAFE_STOP: return "SAFE_STOP";
        case CELL_STATE_FAULT: return "FAULT";
        case CELL_STATE_ESTOP: return "ESTOP";
        default: return "UNKNOWN";
    }
}

bool cell_sm_is_non_production(cell_state_t state) {
    switch (state) {
        case CELL_STATE_BOOT:
        case CELL_STATE_SELF_TEST:
        case CELL_STATE_IDLE:
        case CELL_STATE_SAFE_STOP:
        case CELL_STATE_FAULT:
        case CELL_STATE_ESTOP:
            return true;
        default:
            return false;
    }
}

bool cell_sm_is_latched(cell_state_t state) {
    return state == CELL_STATE_SAFE_STOP || state == CELL_STATE_FAULT || state == CELL_STATE_ESTOP;
}

void cell_sm_update(cell_sm_t *sm, bool estop_active, bool fault_active, bool safe_stop_active) {
    /* Priority order (HARDWARE_INTERFACE.md): ESTOP > SAFE_STOP > FAULT > everything else. */
    if (estop_active) {
        sm->state = CELL_STATE_ESTOP;
        return;
    }
    if (sm->state == CELL_STATE_ESTOP) {
        return; /* latched until cell_sm_reset() */
    }
    if (safe_stop_active) {
        sm->state = CELL_STATE_SAFE_STOP;
        return;
    }
    if (sm->state == CELL_STATE_SAFE_STOP) {
        return;
    }
    if (fault_active) {
        sm->state = CELL_STATE_FAULT;
        return;
    }
    if (sm->state == CELL_STATE_FAULT) {
        return;
    }
    /* No override active: leave the state as-is; STARTING/RUNNING/STOPPING/IDLE only change
     * via the explicit command functions below. */
}

bool cell_sm_self_test_passed(cell_sm_t *sm) {
    if (sm->state != CELL_STATE_BOOT && sm->state != CELL_STATE_SELF_TEST) {
        return false;
    }
    sm->state = CELL_STATE_IDLE;
    return true;
}

bool cell_sm_start(cell_sm_t *sm) {
    if (sm->state != CELL_STATE_IDLE) {
        return false;
    }
    sm->state = CELL_STATE_STARTING;
    return true;
}

bool cell_sm_start_settled(cell_sm_t *sm) {
    if (sm->state != CELL_STATE_STARTING) {
        return false;
    }
    sm->state = CELL_STATE_RUNNING;
    return true;
}

bool cell_sm_stop(cell_sm_t *sm) {
    if (sm->state != CELL_STATE_RUNNING) {
        return false;
    }
    sm->state = CELL_STATE_STOPPING;
    return true;
}

bool cell_sm_stop_settled(cell_sm_t *sm) {
    if (sm->state != CELL_STATE_STOPPING) {
        return false;
    }
    sm->state = CELL_STATE_IDLE;
    return true;
}

bool cell_sm_reset(cell_sm_t *sm, bool estop_active, bool fault_active, bool safe_stop_active) {
    if (!cell_sm_is_latched(sm->state)) {
        return false;
    }
    if (sm->state == CELL_STATE_ESTOP && estop_active) {
        return false; /* cause not cleared */
    }
    if (sm->state == CELL_STATE_FAULT && fault_active) {
        return false;
    }
    if (sm->state == CELL_STATE_SAFE_STOP && safe_stop_active) {
        return false;
    }
    sm->state = CELL_STATE_IDLE;
    return true;
}
