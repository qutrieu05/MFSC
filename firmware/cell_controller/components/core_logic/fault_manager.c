#include "fault_manager.h"
#include <string.h>

const fault_meta_t FAULT_TABLE[FAULT_CODE_COUNT] = {
    [FAULT_F001_ESTOP_ACTIVE]   = {"F001", "ESTOP_ACTIVE", true},
    [FAULT_F010_COMM_LOSS_EDGE] = {"F010", "COMM_LOSS_EDGE", true},
    [FAULT_F050_SELF_TEST_FAILED] = {"F050", "SELF_TEST_FAILED", true},
    [FAULT_F051_WATCHDOG_RESET] = {"F051", "WATCHDOG_RESET", false},
};

void fault_manager_init(fault_manager_t *fm) {
    memset(fm->active, 0, sizeof(fm->active));
}

void fault_manager_raise(fault_manager_t *fm, fault_code_t code) {
    fm->active[code] = true;
}

void fault_manager_clear_if_not_latching(fault_manager_t *fm, fault_code_t code) {
    if (!FAULT_TABLE[code].latching) {
        fm->active[code] = false;
    }
}

void fault_manager_ack(fault_manager_t *fm, fault_code_t code) {
    fm->active[code] = false;
}

bool fault_manager_is_active(const fault_manager_t *fm, fault_code_t code) {
    return fm->active[code];
}

bool fault_manager_any_latched_active(const fault_manager_t *fm) {
    for (int i = 0; i < FAULT_CODE_COUNT; i++) {
        if (FAULT_TABLE[i].latching && fm->active[i]) {
            return true;
        }
    }
    return false;
}
