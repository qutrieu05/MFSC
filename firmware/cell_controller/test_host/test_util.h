/* Minimal host-test harness. Not Unity (ADR-0006 named Unity, but vendoring a third-party
 * framework wasn't approved this round) -- kept structurally close so swapping to real Unity
 * later is a small change: each CHECK() here maps to one TEST_ASSERT_*, each test_xxx()
 * function maps to one RUN_TEST(test_xxx). Each test file is its own translation unit/
 * executable, so the `static` counters below don't collide across files.
 */
#ifndef MSFC_TEST_UTIL_H
#define MSFC_TEST_UTIL_H

#include <stdio.h>

static int g_tests_run = 0;
static int g_tests_failed = 0;

#define CHECK(cond) do { \
    g_tests_run++; \
    if (!(cond)) { g_tests_failed++; printf("  FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); } \
} while (0)

#define CHECK_EQ(expected, actual) do { \
    g_tests_run++; \
    long _e = (long)(expected); \
    long _a = (long)(actual); \
    if (_e != _a) { \
        g_tests_failed++; \
        printf("  FAIL %s:%d: expected %ld, got %ld\n", __FILE__, __LINE__, _e, _a); \
    } \
} while (0)

#define TEST_SUMMARY_AND_RETURN() do { \
    printf("SUMMARY: %d run, %d failed (%s)\n", g_tests_run, g_tests_failed, __FILE__); \
    return g_tests_failed ? 1 : 0; \
} while (0)

#endif /* MSFC_TEST_UTIL_H */
