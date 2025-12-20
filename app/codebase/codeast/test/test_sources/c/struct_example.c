#include <string.h>
#include <stdlib.h>

struct User {
    int id;
    char name[100];
    char email[100];
};

struct User* create_user(int id, const char* name) {
    struct User* user = malloc(sizeof(struct User));
    user->id = id;
    strcpy(user->name, name);
    return user;
}

