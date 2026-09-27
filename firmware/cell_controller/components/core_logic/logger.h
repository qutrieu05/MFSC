/* Minimal leveled logger. Uses only <stdio.h>/<stdarg.h> (no ESP-IDF), so the same file
 * works unmodified on host and, later, on ESP32 (newlib's printf goes to UART by default) —
 * unlike hal_*, this one module doesn't need a separate host/esp32 implementation.
 */
#ifndef MSFC_LOGGER_H
#define MSFC_LOGGER_H

typedef enum {
    LOG_LEVEL_DEBUG = 0,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARNING,
    LOG_LEVEL_ERROR,
} log_level_t;

void logger_set_min_level(log_level_t level);
void logger_log(log_level_t level, const char *tag, const char *fmt, ...);

#define LOG_D(tag, ...) logger_log(LOG_LEVEL_DEBUG, tag, __VA_ARGS__)
#define LOG_I(tag, ...) logger_log(LOG_LEVEL_INFO, tag, __VA_ARGS__)
#define LOG_W(tag, ...) logger_log(LOG_LEVEL_WARNING, tag, __VA_ARGS__)
#define LOG_E(tag, ...) logger_log(LOG_LEVEL_ERROR, tag, __VA_ARGS__)

#endif /* MSFC_LOGGER_H */
