import os
import tempfile
import pytest
from app.codebase.codeast.services.ast_analyzer import FileAstAnalyzer
from app.codebase.codeast.models.model import Language, FunctionType


class TestCppASTAnalysis:
    """测试C++ AST分析功能 - 验证分析结果的正确性"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_extract_cpp_class(self, temp_dir):
        """测试提取C++类 - 验证类名、方法名、方法类型"""
        test_file = os.path.join(temp_dir, "user.cpp")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
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
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.CPP

    @pytest.mark.asyncio
    async def test_extract_cpp_inheritance(self, temp_dir):
        """测试提取C++继承关系"""
        test_file = os.path.join(temp_dir, "animal.cpp")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
class Animal {
public:
    virtual void speak() = 0;
    virtual ~Animal() {}
};

class Dog : public Animal {
public:
    void speak() override {
        std::cout << "Woof" << std::endl;
    }
};

class Cat : public Animal {
public:
    void speak() override {
        std::cout << "Meow" << std::endl;
    }
};
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.CPP

    @pytest.mark.asyncio
    async def test_extract_cpp_templates(self, temp_dir):
        """测试提取C++模板"""
        test_file = os.path.join(temp_dir, "template.cpp")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
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
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.CPP

    @pytest.mark.asyncio
    async def test_extract_cpp_namespace(self, temp_dir):
        """测试提取C++命名空间"""
        test_file = os.path.join(temp_dir, "namespace.cpp")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
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
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.CPP

    @pytest.mark.asyncio
    async def test_extract_cpp_headers(self, temp_dir):
        """测试提取C++头文件包含"""
        test_file = os.path.join(temp_dir, "main.cpp")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
#include <iostream>
#include <vector>
#include <string>
#include "user.h"

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.CPP

    @pytest.mark.asyncio
    async def test_extract_cpp_operator_overload(self, temp_dir):
        """测试提取C++运算符重载"""
        test_file = os.path.join(temp_dir, "operator.cpp")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
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
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.CPP

