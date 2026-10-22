/*
 * urftopjl - CUPS filter: wraps an Apple Raster (URF) stream in PJL so that
 * Xerox Phaser 3020 / Samsung-based SPL printers accept it over raw USB.
 *
 * Over IPP the document-format attribute tells the printer what it is
 * receiving. A raw USB connection carries no such metadata, so the firmware
 * needs an explicit "@PJL ENTER LANGUAGE=URF" or it discards the job without
 * reporting an error.
 *
 * Usage (CUPS filter interface): urftopjl job user title copies options [file]
 *
 * SPDX-License-Identifier: MIT
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define UEL "\033%-12345X"
#define BUFSZ 65536

/* PJL strings are quoted; strip quotes/control chars and cap the length. */
static void sanitize(const char *src, char *dst, size_t cap)
{
    size_t j = 0;
    if (!src) src = "";
    for (size_t i = 0; src[i] && j + 1 < cap; i++) {
        unsigned char c = (unsigned char)src[i];
        if (c == '"' || c == '\\' || c < 0x20 || c == 0x7f) continue;
        dst[j++] = (char)c;
    }
    dst[j] = '\0';
    if (j == 0) snprintf(dst, cap, "CUPS");
}

int main(int argc, char *argv[])
{
    FILE *in = stdin;
    char title[80];
    char buf[BUFSZ];
    size_t n;

    if (argc < 6 || argc > 7) {
        fputs("ERROR: urftopjl job-id user title copies options [file]\n", stderr);
        return 1;
    }

    if (argc == 7) {
        if (!(in = fopen(argv[6], "rb"))) {
            fprintf(stderr, "ERROR: Unable to open %s\n", argv[6]);
            return 1;
        }
    }

    sanitize(argv[3], title, sizeof title);

    fputs(UEL, stdout);
    printf("@PJL JOB NAME=\"%s\"\r\n", title);
    fputs("@PJL ENTER LANGUAGE=URF\r\n", stdout);

    while ((n = fread(buf, 1, sizeof buf, in)) > 0) {
        if (fwrite(buf, 1, n, stdout) != n) {
            fputs("ERROR: Short write sending print data\n", stderr);
            if (in != stdin) fclose(in);
            return 1;
        }
    }

    if (ferror(in)) {
        fputs("ERROR: Read error on input stream\n", stderr);
        if (in != stdin) fclose(in);
        return 1;
    }

    fputs(UEL, stdout);
    fputs("@PJL EOJ\r\n", stdout);
    fputs(UEL, stdout);

    if (fflush(stdout) != 0) {
        fputs("ERROR: Unable to flush print data\n", stderr);
        if (in != stdin) fclose(in);
        return 1;
    }

    if (in != stdin) fclose(in);
    return 0;
}
