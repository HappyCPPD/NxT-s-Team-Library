#define _GNU_SOURCE
#include <libfvde.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void die(const char *where, libfvde_error_t **error) {
    fprintf(stderr, "error: %s\n", where);
    if (error && *error) {
        libfvde_error_backtrace_fprint(*error, stderr);
        libfvde_error_free(error);
    }
    exit(2);
}

int main(int argc, char **argv) {
    if (argc != 6 || (strcmp(argv[5], "password") && strcmp(argv[5], "recovery"))) {
        fprintf(stderr, "usage: %s plist ssd_partition hdd_partition dictionary password|recovery\n", argv[0]);
        return 2;
    }

    libfvde_error_t *error = NULL;
    libfvde_volume_t *volume = NULL;
    libfvde_volume_group_t *group = NULL;
    char *sources[2] = { argv[2], argv[3] };

    if (libfvde_volume_initialize(&volume, &error) != 1)
        die("volume_initialize", &error);
    if (libfvde_volume_read_encrypted_root_plist(volume, argv[1], &error) != 1)
        die("read_encrypted_root_plist", &error);
    if (libfvde_volume_open(volume, sources[0], LIBFVDE_OPEN_READ, &error) != 1)
        die("open_initial_volume", &error);
    if (libfvde_volume_open_physical_volume_files(volume, sources, 2, &error) != 1)
        die("open_physical_volume_files", &error);
    if (libfvde_volume_get_volume_group(volume, &group, &error) != 1)
        die("get_volume_group", &error);

    FILE *dictionary = strcmp(argv[4], "-") ? fopen(argv[4], "rb") : stdin;
    if (!dictionary) {
        perror(argv[4]);
        return 2;
    }

    char *candidate = NULL;
    size_t capacity = 0;
    ssize_t length;
    unsigned long long attempts = 0;
    int found = 0;

    while ((length = getline(&candidate, &capacity, dictionary)) >= 0) {
        while (length > 0 && (candidate[length - 1] == '\n' || candidate[length - 1] == '\r'))
            candidate[--length] = '\0';
        if (length == 0)
            continue;

        libfvde_logical_volume_t *logical = NULL;
        if (libfvde_volume_group_get_logical_volume_by_index(group, 0, &logical, &error) != 1)
            die("get_logical_volume", &error);

        int result;
        if (!strcmp(argv[5], "password"))
            result = libfvde_logical_volume_set_utf8_password(logical, (const uint8_t *)candidate, (size_t)length, &error);
        else
            result = libfvde_logical_volume_set_utf8_recovery_password(logical, (const uint8_t *)candidate, (size_t)length, &error);

        if (result < 0)
            die("set_candidate", &error);

        result = libfvde_logical_volume_unlock(logical, &error);
        attempts++;
        if (result < 0)
            die("unlock", &error);
        if (result == 1) {
            printf("FOUND\t%s\n", candidate);
            fflush(stdout);
            found = 1;
            libfvde_logical_volume_free(&logical, &error);
            break;
        }
        if ((attempts % 1000) == 0) {
            fprintf(stderr, "attempts=%llu\n", attempts);
            fflush(stderr);
        }
        if (libfvde_logical_volume_free(&logical, &error) != 1)
            die("logical_volume_free", &error);
    }

    fprintf(stderr, "tested=%llu found=%d\n", attempts, found);
    free(candidate);
    if (dictionary != stdin)
        fclose(dictionary);
    libfvde_volume_group_free(&group, &error);
    libfvde_volume_close(volume, &error);
    libfvde_volume_free(&volume, &error);
    libfvde_error_free(&error);
    return found ? 0 : 1;
}
