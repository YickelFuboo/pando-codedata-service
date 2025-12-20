template<typename T>
class Vector {
private:
    T* data;
    int size;
    
public:
    Vector(int size) : size(size) {
        data = new T[size];
    }
    
    ~Vector() {
        delete[] data;
    }
    
    T& operator[](int index) {
        return data[index];
    }
};

template<typename T>
T max(T a, T b) {
    return a > b ? a : b;
}

