import os
import json
import pytest
from enum import Enum
from dataclasses import asdict, fields
from app.codebase.codeast.services.ast_analyzer import FileAstAnalyzer
from app.codebase.codeast.models.model import Language, FunctionType


class TestPythonASTAnalysis:
    """测试Python AST分析功能 - 验证分析结果的正确性"""

    @pytest.fixture
    def test_sources_dir(self):
        """获取测试源文件目录"""
        return os.path.join(os.path.dirname(__file__), "test_sources", "python")

    @pytest.fixture
    def base_path(self, test_sources_dir):
        """获取基础路径（用于相对路径计算）"""
        return os.path.dirname(test_sources_dir)

    def _dataclass_to_dict(self, obj):
        """将 dataclass 对象转换为字典，处理嵌套结构"""
        if hasattr(obj, '__dataclass_fields__'):
            result = {}
            for field in fields(obj):
                value = getattr(obj, field.name)
                if value is None:
                    result[field.name] = None
                elif isinstance(value, list):
                    result[field.name] = [self._dataclass_to_dict(item) if hasattr(item, '__dataclass_fields__') else item for item in value]
                elif hasattr(value, '__dataclass_fields__'):
                    result[field.name] = self._dataclass_to_dict(value)
                elif isinstance(value, Enum):
                    result[field.name] = value.value
                else:
                    result[field.name] = value
            return result
        return obj

    def _print_analysis_result(self, file_info, test_name: str):
        """打印AST解析结果，使用JSON格式输出"""
        print(f"\n{'='*80}")
        print(f"测试用例: {test_name}")
        print(f"{'='*80}")
        
        # 转换为字典
        result_dict = self._dataclass_to_dict(file_info)
        
        # 使用JSON格式打印，确保中文正确显示
        print(json.dumps(result_dict, indent=2, ensure_ascii=False))
        
        print(f"{'='*80}\n")

    @pytest.mark.asyncio
    async def test_extract_simple_function(self, test_sources_dir, base_path):
        """测试提取简单函数 - 验证函数名、参数、返回类型、文档字符串等完整信息"""
        test_file = os.path.join(test_sources_dir, "simple_function.py")
        
        analyzer = FileAstAnalyzer(base_path, test_file)
        file_info = await analyzer.analyze_file()
        
        # 打印解析结果
        self._print_analysis_result(file_info, "test_extract_simple_function")
        
        assert file_info is not None
        assert file_info.name == "simple_function.py"
        assert file_info.language == Language.PYTHON
        assert file_info.file_path.endswith("python/simple_function.py") or file_info.file_path.endswith("simple_function.py")
        assert len(file_info.functions) == 1
        assert len(file_info.classes) == 0
        assert len(file_info.imports) == 0
        
        func = file_info.functions[0]
        assert func.name == "calculate_sum"
        assert func.full_name.endswith(".calculate_sum")
        assert func.signature == "calculate_sum(int, int) -> int"
        assert func.type == FunctionType.FUNCTION.value
        assert func.file_path.endswith("simple_function.py") or "simple_function.py" in func.file_path
        assert func.start_line == 1
        assert func.end_line == 3
        assert "a" in func.params
        assert "b" in func.params
        assert len(func.params) == 2
        assert len(func.param_types) == 2
        assert "int" in func.param_types
        assert len(func.returns) >= 0
        assert len(func.return_types) == 1
        assert "int" in func.return_types
        assert func.docstring is not None
        assert "计算" in func.docstring or "sum" in func.docstring.lower()
        assert func.source_code is not None
        assert "def calculate_sum" in func.source_code
        assert func.calls is not None

    @pytest.mark.asyncio
    async def test_extract_class_with_methods(self, test_sources_dir, base_path):
        """测试提取类和方法 - 验证类名、方法名、方法类型、完整信息"""
        test_file = os.path.join(test_sources_dir, "class_with_methods.py")
        
        analyzer = FileAstAnalyzer(base_path, test_file)
        file_info = await analyzer.analyze_file()
        
        # 打印解析结果
        self._print_analysis_result(file_info, "test_extract_class_with_methods")
        
        assert file_info is not None
        assert file_info.name == "class_with_methods.py"
        assert file_info.language == Language.PYTHON
        assert len(file_info.classes) == 1
        assert len(file_info.functions) == 0
        
        cls = file_info.classes[0]
        assert cls.name == "UserService"
        assert cls.full_name.endswith(".UserService")
        assert cls.node_type is not None
        assert cls.file_path.endswith("class_with_methods.py") or "class_with_methods.py" in cls.file_path
        assert cls.start_line == 1
        assert cls.end_line == 11
        assert cls.docstring is not None
        assert "用户服务类" in cls.docstring or "UserService" in cls.docstring
        assert cls.source_code is not None
        assert "class UserService" in cls.source_code
        assert cls.attributes is not None
        
        assert len(cls.methods) == 3
        method_names = [m.name for m in cls.methods]
        assert "__init__" in method_names
        assert "get_name" in method_names
        assert "set_name" in method_names
        
        for method in cls.methods:
            assert method.type == FunctionType.METHOD.value
            assert method.class_name == "UserService"
            assert method.full_name.endswith(f".UserService.{method.name}")
            assert method.file_path.endswith("class_with_methods.py") or "class_with_methods.py" in method.file_path
            assert method.start_line is not None
            assert method.end_line is not None
            assert method.source_code is not None
            assert method.params is not None
            assert method.param_types is not None
            assert method.returns is not None
            assert method.return_types is not None
            assert method.calls is not None

    @pytest.mark.asyncio
    async def test_extract_imports(self, test_sources_dir, base_path):
        """测试提取导入语句 - 验证导入路径解析"""
        test_file = os.path.join(test_sources_dir, "imports_example.py")
        
        analyzer = FileAstAnalyzer(base_path, test_file)
        file_info = await analyzer.analyze_file()
        
        # 打印解析结果
        self._print_analysis_result(file_info, "test_extract_imports")
        
        assert file_info is not None
        assert file_info.name == "imports_example.py"
        assert file_info.language == Language.PYTHON
        assert len(file_info.imports) > 0
        
        imports_str = " ".join(file_info.imports)
        assert "os" in imports_str
        assert "typing" in imports_str or "List" in imports_str or "Dict" in imports_str
        assert "app.utils" in imports_str or "helper" in imports_str
        assert "app.models.user" in imports_str or "User" in imports_str
        
        assert len(file_info.functions) == 1
        test_func = file_info.functions[0]
        assert test_func.name == "test_function"

    @pytest.mark.asyncio
    async def test_extract_relative_imports(self, test_sources_dir, base_path):
        """测试提取相对导入 - 验证相对导入转换为绝对路径"""
        test_file = os.path.join(test_sources_dir, "relative_imports.py")
        
        analyzer = FileAstAnalyzer(base_path, test_file)
        file_info = await analyzer.analyze_file()
        
        # 打印解析结果
        self._print_analysis_result(file_info, "test_extract_relative_imports")
        
        assert file_info is not None
        assert file_info.name == "relative_imports.py"
        assert file_info.language == Language.PYTHON
        assert len(file_info.imports) > 0
        
        imports_str = " ".join(file_info.imports)
        assert "helper" in imports_str or "BaseModel" in imports_str
        
        assert len(file_info.functions) == 1
        use_helper_func = file_info.functions[0]
        assert use_helper_func.name == "use_helper"

    @pytest.mark.asyncio
    async def test_extract_inheritance(self, test_sources_dir, base_path):
        """测试提取继承关系 - 验证父类识别"""
        test_file = os.path.join(test_sources_dir, "inheritance_example.py")
        
        analyzer = FileAstAnalyzer(base_path, test_file)
        file_info = await analyzer.analyze_file()
        
        # 打印解析结果
        self._print_analysis_result(file_info, "test_extract_inheritance")
        
        assert file_info is not None
        assert file_info.name == "inheritance_example.py"
        assert file_info.language == Language.PYTHON
        assert len(file_info.classes) == 3
        
        animal_class = next((c for c in file_info.classes if c.name == "Animal"), None)
        dog_class = next((c for c in file_info.classes if c.name == "Dog"), None)
        cat_class = next((c for c in file_info.classes if c.name == "Cat"), None)
        
        assert animal_class is not None
        assert dog_class is not None
        assert cat_class is not None
        
        assert dog_class.base_classes is not None
        assert len(dog_class.base_classes) > 0
        assert any(b.name == "Animal" for b in dog_class.base_classes)
        
        assert cat_class.base_classes is not None
        assert len(cat_class.base_classes) > 0
        assert any(b.name == "Animal" for b in cat_class.base_classes)

    @pytest.mark.asyncio
    async def test_extract_function_calls(self, test_sources_dir, base_path):
        """测试提取函数调用关系 - 验证调用信息"""
        test_file = os.path.join(test_sources_dir, "function_calls.py")
        
        analyzer = FileAstAnalyzer(base_path, test_file)
        file_info = await analyzer.analyze_file()
        
        # 打印解析结果
        self._print_analysis_result(file_info, "test_extract_function_calls")
        
        assert file_info is not None
        assert file_info.name == "function_calls.py"
        assert file_info.language == Language.PYTHON
        assert len(file_info.functions) == 2
        
        helper_func = next((f for f in file_info.functions if f.name == "helper_function"), None)
        main_func = next((f for f in file_info.functions if f.name == "main_function"), None)
        
        assert helper_func is not None
        assert main_func is not None
        
        assert main_func.calls is not None
        assert len(main_func.calls) > 0
        
        call_names = [c.name for c in main_func.calls]
        assert "helper_function" in call_names or "join" in call_names
        
        for call in main_func.calls:
            assert call.name is not None
            assert call.full_name is not None
            assert call.signature is not None

    @pytest.mark.asyncio
    async def test_extract_async_function(self, test_sources_dir, base_path):
        """测试提取异步函数"""
        test_file = os.path.join(test_sources_dir, "async_function.py")
        
        analyzer = FileAstAnalyzer(base_path, test_file)
        file_info = await analyzer.analyze_file()
        
        # 打印解析结果
        self._print_analysis_result(file_info, "test_extract_async_function")
        
        assert file_info is not None
        assert file_info.name == "async_function.py"
        assert file_info.language == Language.PYTHON
        assert len(file_info.functions) == 1
        
        func = file_info.functions[0]
        assert func.name == "fetch_data"
        assert func.full_name.endswith(".fetch_data")
        assert func.signature == "fetch_data(str) -> dict"
        assert func.type == FunctionType.FUNCTION.value
        assert "url" in func.params
        assert len(func.params) == 1
        assert len(func.param_types) == 1
        assert "str" in func.param_types
        assert len(func.return_types) == 1
        assert "dict" in func.return_types
        assert func.source_code is not None
        assert "async def fetch_data" in func.source_code
        assert func.start_line == 1
        assert func.end_line == 5

    @pytest.mark.asyncio
    async def test_extract_complex_function_signature(self, test_sources_dir, base_path):
        """测试提取复杂函数签名"""
        test_file = os.path.join(test_sources_dir, "complex_signature.py")
        
        analyzer = FileAstAnalyzer(base_path, test_file)
        file_info = await analyzer.analyze_file()
        
        # 打印解析结果
        self._print_analysis_result(file_info, "test_extract_complex_function_signature")
        
        assert file_info is not None
        assert file_info.name == "complex_signature.py"
        assert file_info.language == Language.PYTHON
        assert len(file_info.imports) > 0
        
        imports_str = " ".join(file_info.imports)
        assert "typing" in imports_str or "List" in imports_str or "Dict" in imports_str
        
        assert len(file_info.functions) == 1
        func = file_info.functions[0]
        assert func.name == "complex_function"
        assert func.full_name.endswith(".complex_function")
        assert len(func.params) == 3
        assert "items" in func.params
        assert "config" in func.params
        assert "callback" in func.params
        assert len(func.param_types) == 3
        assert len(func.return_types) == 1
        assert func.source_code is not None
        assert "def complex_function" in func.source_code
        assert func.start_line is not None
        assert func.end_line is not None

    @pytest.mark.asyncio
    async def test_extract_class_method_calls(self, test_sources_dir, base_path):
        """测试提取类方法调用 - 验证类方法中的self.xxx调用"""
        test_file = os.path.join(test_sources_dir, "class_method_calls.py")
        
        analyzer = FileAstAnalyzer(base_path, test_file)
        file_info = await analyzer.analyze_file()
        
        # 打印解析结果
        self._print_analysis_result(file_info, "test_extract_class_method_calls")
        
        assert file_info is not None
        assert file_info.name == "class_method_calls.py"
        assert file_info.language == Language.PYTHON
        assert len(file_info.classes) == 1
        assert len(file_info.functions) == 0
        
        calc_class = file_info.classes[0]
        assert calc_class.name == "Calculator"
        assert calc_class.full_name.endswith(".Calculator")
        assert len(calc_class.methods) == 3
        
        method_names = [m.name for m in calc_class.methods]
        assert "add" in method_names
        assert "multiply" in method_names
        assert "calculate" in method_names
        
        calculate_method = next((m for m in calc_class.methods if m.name == "calculate"), None)
        assert calculate_method is not None
        assert calculate_method.type == FunctionType.METHOD.value
        assert calculate_method.class_name == "Calculator"
        assert calculate_method.full_name.endswith(".Calculator.calculate")
        assert calculate_method.calls is not None
        assert len(calculate_method.calls) >= 2
        
        call_names = [c.name for c in calculate_method.calls]
        assert "add" in call_names
        assert "multiply" in call_names
        
        for call in calculate_method.calls:
            assert call.name is not None
            assert call.full_name is not None
            assert call.full_name.endswith(f".Calculator.{call.name}")
            assert call.signature is not None
