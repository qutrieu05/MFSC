/* Debounce filter for IF-HW-02/03 (RESET_BTN/START_BTN, 20-50 ms per HARDWARE_INTERFACE.md).
 * S1/S2 sensors use ISR timestamp + separate debounce per that doc; not covered here (that
 * belongs to product_tracker, deferred — see TASKS.md P1.5 detail).
 */
#ifndef MSFC_DEBOUNCE_H
#define MSFC_DEBOUNCE_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    bool stable_state;
    bool candidate_state;
    uint32_t candidate_since_mono_ms;
    uint32_t debounce_ms;
} debounce_t;

void debounce_init(debounce_t *d, uint32_t debounce_ms, bool initial_state);

/* Feed one raw reading + the current monotonic time; returns the debounced stable value. */
bool debounce_update(debounce_t *d, bool raw, uint32_t now_mono_ms);

#endif /* MSFC_DEBOUNCE_H */
