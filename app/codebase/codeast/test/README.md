# CodeAST 测试文档

本目录包含 CodeAST 模块的AST分析功能验证测试代码。测试通过构造不同的源码文件，验证AST分析结果的正确性。

## 测试结构

- `test_models.py` - 数据模型结构验证
- `test_file_analyzer.py` - 语言检测功能测试
- `test_python_ast_analysis.py` - **Python AST分析功能验证**（核心测试）
- `test_java_ast_analysis.py` - Java AST分析功能验证
- `test_go_ast_analysis.py` - Go AST分析功能验证
- `test_folder_ast_analysis.py` - 文件夹分析功能验证
- `test_integration.py` - 集成测试：完整项目分析验证

## 测试重点

### Python AST分析验证 (`test_python_ast_analysis.py`)
- ✅ 函数提取：函数名、参数、返回类型、文档字符串
- ✅ 类和方法提取：类名、方法名、方法类型、类属性
- ✅ 导入语句解析：绝对导入、相对导入、导入路径转换
- ✅ 继承关系识别：父类识别
- ✅ 函数调用关系：函数调用信息提取
- ✅ 异步函数支持
- ✅ 复杂函数签名：类型注解、默认参数
- ✅ 顶层函数与类方法区分
- ✅ 相对路径计算

### 文件夹分析验证 (`test_folder_ast_analysis.py`)
- ✅ 项目结构分析
- ✅ 隐藏目录排除
- ✅ 多语言文件支持
- ✅ 相对路径计算

## 运行测试

### 运行所有测试
```bash
pytest app/codeast/test/
```

### 运行Python AST分析测试（核心测试）
```bash
pytest app/codeast/test/test_python_ast_analysis.py -v
```

### 运行特定测试类
```bash
pytest app/codeast/test/test_python_ast_analysis.py::TestPythonASTAnalysis
```

### 运行特定测试方法
```bash
pytest app/codeast/test/test_python_ast_analysis.py::TestPythonASTAnalysis::test_extract_simple_function
```

### 显示详细输出
```bash
pytest app/codeast/test/ -v
```

### 显示覆盖率
```bash
pytest app/codeast/test/ --cov=app.codeast --cov-report=html
```

## 测试验证点

### 函数分析验证
- 函数名是否正确提取
- 参数列表是否完整
- 参数类型注解是否正确识别
- 返回类型是否正确识别
- 文档字符串是否正确提取
- 函数调用关系是否正确识别

### 类分析验证
- 类名是否正确提取
- 方法列表是否完整
- 方法类型（METHOD）是否正确
- 类属性是否正确识别
- 继承关系是否正确识别

### 导入分析验证
- 绝对导入是否正确解析
- 相对导入是否正确转换为绝对路径
- 导入路径映射是否正确

### 路径验证
- 文件相对路径计算是否正确
- 文件夹相对路径计算是否正确

## 注意事项

1. 测试使用临时目录，不会影响实际文件系统
2. 测试通过构造不同的源码场景来验证AST分析的正确性
3. 每个测试都验证特定的AST分析功能点
4. 集成测试验证完整项目的分析流程

