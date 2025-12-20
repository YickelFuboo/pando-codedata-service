#include <string>
#include <iostream>

class User {
private:
    int id;
    std::string name;
    
public:
    User(int id, const std::string& name) : id(id), name(name) {}
    
    int getId() const {
        return id;
    }
    
    std::string getName() const {
        return name;
    }
    
    void setName(const std::string& newName) {
        name = newName;
    }
};

