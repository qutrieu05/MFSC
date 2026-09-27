#include "logger.h"
#include <stdarg.h>
#include <stdio.h>

static log_level_t s_min_level = LOG_LEVEL_INFO;

static const char *level_name(log_level_t level) {
    switch (level) {
        case LOG_LEVEL_DEBUG: return "DEBUG";
        case LOG_LEVEL_INFO: return "INFO";
        case LOG_LEVEL_WARNING: return "WARN";
        case LOG_LEVEL_ERROR: return "ERROR";
        default: return "?";
    }
}

void logger_set_min_level(log_level_t level) {
    s_min_level = level;
}

void logger_log(log_level_t level, const char *tag, const char *fmt, ...) {
    if (level < s_min_level) {
        return;
    }
    printf("[%s] %s: ", level_name(level), tag);
    va_list args;
    va_start(args, fmt);
    vprintf(fmt, args);
    va_end(args);
    printf("\n");
}
