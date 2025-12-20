#include <stdlib.h>

int* allocate_array(int size) {
    return malloc(size * sizeof(int));
}

void process_array(int* arr, int size) {
    for (int i = 0; i < size; i++) {
        arr[i] = i * 2;
    }
}

