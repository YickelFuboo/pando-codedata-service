# 测试源文件目录

本目录包含用于测试AST分析功能的各种语言的示例源码文件。

## 目录结构

```
test_sources/
├── python/          # Python测试源文件
├── java/            # Java测试源文件
├── go/              # Go测试源文件
├── c/               # C测试源文件
└── cpp/             # C++测试源文件
```

## 文件说明

### Python测试文件
- `simple_function.py` - 简单函数示例
- `class_with_methods.py` - 类和方法示例
- `imports_example.py` - 导入语句示例
- `inheritance_example.py` - 继承关系示例
- `function_calls.py` - 函数调用示例
- `async_function.py` - 异步函数示例
- `complex_signature.py` - 复杂函数签名示例
- `relative_imports.py` - 相对导入示例

### Java测试文件
- `SimpleClass.java` - 简单类示例
- `InheritanceExample.java` - 继承示例
- `InterfaceExample.java` - 接口实现示例
- `ImportsExample.java` - 导入语句示例

### Go测试文件
- `simple_function.go` - 简单函数示例
- `struct_example.go` - 结构体示例
- `interface_example.go` - 接口示例

### C测试文件
- `simple_function.c` - 简单函数示例
- `struct_example.c` - 结构体示例
- `pointer_function.c` - 指针函数示例
- `headers_example.c` - 头文件包含示例

### C++测试文件
- `simple_class.cpp` - 简单类示例
- `inheritance_example.cpp` - 继承示例
- `template_example.cpp` - 模板示例
- `namespace_example.cpp` - 命名空间示例
- `operator_overload.cpp` - 运算符重载示例
- `headers_example.cpp` - 头文件包含示例

## 使用方式

测试代码可以通过读取这些文件来验证AST分析功能：

```python
import os
from pathlib import Path

# 获取测试源文件路径
test_sources_dir = Path(__file__).parent / "test_sources"
python_file = test_sources_dir / "python" / "simple_function.py"

# 在测试中使用
analyzer = FileAstAnalyzer(base_path, str(python_file))
file_info = await analyzer.analyze_file()
```

