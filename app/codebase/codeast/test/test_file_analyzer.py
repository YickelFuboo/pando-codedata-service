import os
import tempfile
import pytest
from app.codeast.services.ast_analyzer import FileAstAnalyzer
from app.codeast.models.model import Language


class TestFileAstAnalyzer:
    """测试FileAstAnalyzer语言检测功能"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_detect_python_language(self, temp_dir):
        """测试检测Python语言"""
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def test(): pass")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.PYTHON

    @pytest.mark.asyncio
    async def test_detect_java_language(self, temp_dir):
        """测试检测Java语言"""
        test_file = os.path.join(temp_dir, "Test.java")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("public class Test {}")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.JAVA

    @pytest.mark.asyncio
    async def test_detect_go_language(self, temp_dir):
        """测试检测Go语言"""
        test_file = os.path.join(temp_dir, "test.go")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("package main\nfunc main() {}")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.GO

    @pytest.mark.asyncio
    async def test_unknown_language(self, temp_dir):
        """测试未知语言返回None"""
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("This is a text file")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is None

