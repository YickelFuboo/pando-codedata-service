#include <string>

namespace utils {
    std::string format(const std::string& str) {
        return "[" + str + "]";
    }
}

namespace app {
    namespace models {
        class User {
        public:
            std::string name;
        };
    }
}

