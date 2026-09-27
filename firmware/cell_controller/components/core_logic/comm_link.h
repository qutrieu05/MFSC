/* Communication interface boundary — the shape core_logic/app talk through to reach MQTT,
 * WITHOUT core_logic knowing MQTT/esp-mqtt/cJSON exist (README rule 1 + ARCHITECTURE.md's
 * comm/ package). This round defines the boundary only: no .c implementation is provided,
 * because a real implementation needs esp-mqtt (ESP-IDF) and there is no hardware to run it
 * on yet (HARDWARE AVAILABLE = NONE). A host test double or the future esp-mqtt-backed
 * implementation both just need to fill in this struct of function pointers.
 *
 * Payload shapes (state_changed, fault, heartbeat) follow contracts/schemas/*.json — this
 * header does not redefine them; a real implementation encodes via msg_codec (planned,
 * mirrors msfc.sim.codec on the Edge Server side) before calling into MQTT.
 */
#ifndef MSFC_COMM_LINK_H
#define MSFC_COMM_LINK_H

#include <stdint.h>

typedef struct {
    void (*send_state_changed)(void *ctx, const char *from_state, const char *to_state, uint32_t mono_ms);
    void (*send_fault)(void *ctx, const char *code, const char *event, uint32_t mono_ms);
    void (*send_heartbeat)(void *ctx, uint32_t seq, uint32_t mono_ms);
    void *ctx; /* opaque, passed back to every callback (e.g. the real MQTT client handle) */
} comm_link_t;

#endif /* MSFC_COMM_LINK_H */
