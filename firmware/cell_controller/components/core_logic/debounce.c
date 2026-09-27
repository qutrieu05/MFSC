#include "debounce.h"

void debounce_init(debounce_t *d, uint32_t debounce_ms, bool initial_state) {
    d->stable_state = initial_state;
    d->candidate_state = initial_state;
    d->candidate_since_mono_ms = 0;
    d->debounce_ms = debounce_ms;
}

bool debounce_update(debounce_t *d, bool raw, uint32_t now_mono_ms) {
    if (raw != d->candidate_state) {
        d->candidate_state = raw;
        d->candidate_since_mono_ms = now_mono_ms;
    } else if (raw != d->stable_state && (now_mono_ms - d->candidate_since_mono_ms) >= d->debounce_ms) {
        d->stable_state = raw;
    }
    return d->stable_state;
}
