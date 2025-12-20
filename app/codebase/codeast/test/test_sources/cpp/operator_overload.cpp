class Complex {
private:
    double real;
    double imag;
    
public:
    Complex(double r, double i) : real(r), imag(i) {}
    
    Complex operator+(const Complex& other) const {
        return Complex(real + other.real, imag + other.imag);
    }
    
    bool operator==(const Complex& other) const {
        return real == other.real && imag == other.imag;
    }
};

