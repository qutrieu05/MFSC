/* Fault manager — subset of the catalog in msfc.domain.faults / SAFETY_CONCEPT.md section 5
 * that the firmware itself can raise (device-local faults). The Edge Server's own faults
 * (F020/F021/F030/etc. that depend on vision/tracking) are NOT duplicated here; firmware only
 * owns the codes it can detect from its own inputs.
 */
#ifndef MSFC_FAULT_MANAGER_H
#define MSFC_FAULT_MANAGER_H

#include <stdbool.h>

typedef enum {
    FAULT_F001_ESTOP_ACTIVE = 0,     /* SAF-11 */
    FAULT_F010_COMM_LOSS_EDGE,       /* SF-02 */
    FAULT_F050_SELF_TEST_FAILED,
    FAULT_F051_WATCHDOG_RESET,
    FAULT_CODE_COUNT,
} fault_code_t;

typedef struct {
    const char *code;   /* e.g. "F001", matches msfc.domain.faults.FAULT_CATALOG */
    const char *name;
    bool latching;       /* persists until fault_manager_ack(); false = self-clears */
} fault_meta_t;

extern const fault_meta_t FAULT_TABLE[FAULT_CODE_COUNT];

typedef struct {
    bool active[FAULT_CODE_COUNT];
} fault_manager_t;

void fault_manager_init(fault_manager_t *fm);
void fault_manager_raise(fault_manager_t *fm, fault_code_t code);
/* No-op for a latching fault (must go through fault_manager_ack, a controlled reset). */
void fault_manager_clear_if_not_latching(fault_manager_t *fm, fault_code_t code);
/* Explicit controlled reset (SAFETY_CONCEPT.md section 4): clears even a latching fault. */
void fault_manager_ack(fault_manager_t *fm, fault_code_t code);
bool fault_manager_is_active(const fault_manager_t *fm, fault_code_t code);
bool fault_manager_any_latched_active(const fault_manager_t *fm);

#endif /* MSFC_FAULT_MANAGER_H */
