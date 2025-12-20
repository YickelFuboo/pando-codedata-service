import os
import tempfile
import pytest
from app.codeast.services.ast_analyzer import FolderAstAnalyzer
from app.codeast.models.model import Language


class TestFolderASTAnalysis:
    """测试文件夹AST分析功能 - 验证分析结果的正确性"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_analyze_project_structure(self, temp_dir):
        """测试分析项目结构 - 验证文件组织"""
        project_structure = {
            "main.py": "def main(): pass",
            "utils": {
                "helper.py": "def helper(): pass",
                "__init__.py": ""
            },
            "models": {
                "user.py": "class User: pass",
                "__init__.py": ""
            }
        }
        
        def create_structure(base_path, structure):
            for key, value in structure.items():
                path = os.path.join(base_path, key)
                if isinstance(value, dict):
                    os.makedirs(path, exist_ok=True)
                    create_structure(path, value)
                else:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(value)
        
        create_structure(temp_dir, project_structure)
        
        analyzer = FolderAstAnalyzer(temp_dir, temp_dir)
        folder_info = await analyzer.analyze_folder()
        
        assert folder_info is not None
        assert len(folder_info.files) == 1
        assert len(folder_info.subfolders) == 2
        
        utils_folder = next((f for f in folder_info.subfolders if "utils" in f.path), None)
        assert utils_folder is not None
        assert len(utils_folder.files) == 1

    @pytest.mark.asyncio
    async def test_exclude_hidden_directories(self, temp_dir):
        """测试排除隐藏目录"""
        os.makedirs(os.path.join(temp_dir, ".git"))
        os.makedirs(os.path.join(temp_dir, "__pycache__"))
        
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def test(): pass")
        
        analyzer = FolderAstAnalyzer(temp_dir, temp_dir)
        folder_info = await analyzer.analyze_folder()
        
        assert folder_info is not None
        assert len(folder_info.subfolders) == 0

    @pytest.mark.asyncio
    async def test_analyze_multiple_languages(self, temp_dir):
        """测试分析多种语言文件"""
        with open(os.path.join(temp_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write("def main(): pass")
        
        with open(os.path.join(temp_dir, "Main.java"), "w", encoding="utf-8") as f:
            f.write("public class Main {}")
        
        with open(os.path.join(temp_dir, "main.go"), "w", encoding="utf-8") as f:
            f.write("package main\nfunc main() {}")
        
        analyzer = FolderAstAnalyzer(temp_dir, temp_dir)
        folder_info = await analyzer.analyze_folder()
        
        assert folder_info is not None
        assert len(folder_info.files) == 3
        
        languages = [f.language for f in folder_info.files]
        assert Language.PYTHON in languages
        assert Language.JAVA in languages
        assert Language.GO in languages

    @pytest.mark.asyncio
    async def test_relative_path_calculation(self, temp_dir):
        """测试相对路径计算"""
        subfolder = os.path.join(temp_dir, "app", "services")
        os.makedirs(subfolder)
        
        test_file = os.path.join(subfolder, "service.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def service(): pass")
        
        analyzer = FolderAstAnalyzer(temp_dir, temp_dir)
        folder_info = await analyzer.analyze_folder()
        
        assert folder_info is not None
        assert folder_info.path == "."
        
        services_folder = folder_info.subfolders[0].subfolders[0]
        assert "app" in services_folder.path or "services" in services_folder.path

