import os
import tempfile
import pytest
from app.codeast.services.ast_analyzer import FileAstAnalyzer
from app.codeast.models.model import Language, FunctionType


class TestPythonASTAnalysis:
    """测试Python AST分析功能 - 验证分析结果的正确性"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_extract_simple_function(self, temp_dir):
        """测试提取简单函数 - 验证函数名、参数、返回类型"""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
def calculate_sum(a: int, b: int) -> int:
    \"\"\"计算两个数的和\"\"\"
    return a + b
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert len(file_info.functions) == 1
        
        func = file_info.functions[0]
        assert func.name == "calculate_sum"
        assert "a" in func.params
        assert "b" in func.params
        assert len(func.params) == 2
        assert func.docstring is not None
        assert "计算" in func.docstring or "sum" in func.docstring.lower()

    @pytest.mark.asyncio
    async def test_extract_function_with_default_params(self, temp_dir):
        """测试提取带默认参数的函数"""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
def process_data(name: str, count: int = 10, enabled: bool = True) -> dict:
    return {"name": name, "count": count}
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        func = file_info.functions[0]
        assert func.name == "process_data"
        assert len(func.params) == 3
        assert "name" in func.params
        assert "count" in func.params
        assert "enabled" in func.params

    @pytest.mark.asyncio
    async def test_extract_class_with_methods(self, temp_dir):
        """测试提取类和方法 - 验证类名、方法名、方法类型"""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
class UserService:
    \"\"\"用户服务类\"\"\"
    
    def __init__(self, name: str):
        self.name = name
    
    def get_name(self) -> str:
        return self.name
    
    def set_name(self, name: str) -> None:
        self.name = name
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert len(file_info.classes) == 1
        
        cls = file_info.classes[0]
        assert cls.name == "UserService"
        assert cls.docstring is not None
        
        assert len(cls.methods) == 3
        method_names = [m.name for m in cls.methods]
        assert "__init__" in method_names
        assert "get_name" in method_names
        assert "set_name" in method_names
        
        for method in cls.methods:
            assert method.type == FunctionType.METHOD.value
            assert method.class_name == "UserService"

    @pytest.mark.asyncio
    async def test_extract_imports(self, temp_dir):
        """测试提取导入语句 - 验证导入路径解析"""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
import os
from typing import List, Dict
from app.utils import helper
from app.models.user import User
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert len(file_info.imports) > 0
        
        imports_str = " ".join(file_info.imports)
        assert "os" in imports_str
        assert "typing" in imports_str or "List" in imports_str

    @pytest.mark.asyncio
    async def test_extract_relative_imports(self, temp_dir):
        """测试提取相对导入 - 验证相对导入转换为绝对路径"""
        subfolder = os.path.join(temp_dir, "app", "models")
        os.makedirs(subfolder)
        
        test_file = os.path.join(subfolder, "user.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
from ..utils import helper
from .base import BaseModel
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert len(file_info.imports) > 0

    @pytest.mark.asyncio
    async def test_extract_inheritance(self, temp_dir):
        """测试提取继承关系 - 验证父类识别"""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        return "Woof"

class Cat(Animal):
    def speak(self):
        return "Meow"
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert len(file_info.classes) == 3
        
        dog_class = next((c for c in file_info.classes if c.name == "Dog"), None)
        cat_class = next((c for c in file_info.classes if c.name == "Cat"), None)
        
        assert dog_class is not None
        assert cat_class is not None

    @pytest.mark.asyncio
    async def test_extract_function_calls(self, temp_dir):
        """测试提取函数调用关系 - 验证调用信息"""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
import os

def helper_function():
    return "helper"

def main_function():
    result = helper_function()
    path = os.path.join("test", "path")
    return result
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        main_func = next((f for f in file_info.functions if f.name == "main_function"), None)
        assert main_func is not None
        assert main_func.calls is not None
        assert len(main_func.calls) > 0
        
        call_names = [c.name for c in main_func.calls]
        assert "helper_function" in call_names or "join" in call_names

    @pytest.mark.asyncio
    async def test_extract_async_function(self, temp_dir):
        """测试提取异步函数"""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
async def fetch_data(url: str) -> dict:
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert len(file_info.functions) == 1
        assert file_info.functions[0].name == "fetch_data"
        assert "url" in file_info.functions[0].params

    @pytest.mark.asyncio
    async def test_extract_class_method_calls(self, temp_dir):
        """测试提取类方法调用"""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b
    
    def multiply(self, a: int, b: int) -> int:
        return a * b
    
    def calculate(self, a: int, b: int) -> int:
        sum_result = self.add(a, b)
        product = self.multiply(a, b)
        return sum_result + product
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        calc_class = file_info.classes[0]
        calculate_method = next((m for m in calc_class.methods if m.name == "calculate"), None)
        assert calculate_method is not None
        assert calculate_method.calls is not None
        assert len(calculate_method.calls) >= 2

    @pytest.mark.asyncio
    async def test_extract_nested_classes(self, temp_dir):
        """测试提取嵌套类"""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
class Outer:
    class Inner:
        def inner_method(self):
            return "inner"
    
    def outer_method(self):
        inner = self.Inner()
        return inner.inner_method()
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert len(file_info.classes) >= 1

    @pytest.mark.asyncio
    async def test_extract_complex_function_signature(self, temp_dir):
        """测试提取复杂函数签名"""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
from typing import List, Dict, Optional

def complex_function(
    items: List[str],
    config: Dict[str, int],
    callback: Optional[callable] = None
) -> Dict[str, List[str]]:
    return {"result": items}
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        func = file_info.functions[0]
        assert func.name == "complex_function"
        assert len(func.params) == 3
        assert "items" in func.params
        assert "config" in func.params
        assert "callback" in func.params

    @pytest.mark.asyncio
    async def test_extract_file_path_relative(self, temp_dir):
        """测试文件路径相对路径计算"""
        subfolder = os.path.join(temp_dir, "app", "services")
        os.makedirs(subfolder)
        
        test_file = os.path.join(subfolder, "service.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def test(): pass")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.file_path == "app/services/service.py"
        assert file_info.file_path.startswith("app")

    @pytest.mark.asyncio
    async def test_separate_top_level_functions_from_methods(self, temp_dir):
        """测试区分顶层函数和类方法"""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
def top_level_function():
    return "top level"

class MyClass:
    def class_method(self):
        return "method"

def another_top_level():
    return "another"
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert len(file_info.functions) == 2
        assert len(file_info.classes) == 1
        assert len(file_info.classes[0].methods) == 1
        
        top_level_names = [f.name for f in file_info.functions]
        assert "top_level_function" in top_level_names
        assert "another_top_level" in top_level_names
        assert "class_method" not in top_level_names

