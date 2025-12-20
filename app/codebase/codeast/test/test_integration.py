import os
import tempfile
import pytest
from app.codeast.services.ast_analyzer import FileAstAnalyzer, FolderAstAnalyzer
from app.codeast.models.model import Language, FunctionType


class TestIntegration:
    """集成测试：验证完整AST分析流程的正确性"""

    @pytest.fixture
    def temp_project(self):
        """创建临时项目结构"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_structure = {
                "main.py": """
import os
from utils.helper import process_data

def main():
    \"\"\"主函数\"\"\"
    data = process_data()
    print(data)
    return data

if __name__ == "__main__":
    main()
""",
                "utils": {
                    "__init__.py": "",
                    "helper.py": """
def process_data() -> str:
    \"\"\"处理数据\"\"\"
    return "processed"
"""
                },
                "models": {
                    "__init__.py": "",
                    "user.py": """
class User:
    \"\"\"用户类\"\"\"
    def __init__(self, name: str):
        self.name = name
    
    def get_name(self) -> str:
        return self.name
"""
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
            
            create_structure(tmpdir, project_structure)
            yield tmpdir

    @pytest.mark.asyncio
    async def test_analyze_complete_project_structure(self, temp_project):
        """测试分析完整项目结构 - 验证文件组织"""
        analyzer = FolderAstAnalyzer(temp_project, temp_project)
        folder_info = await analyzer.analyze_folder()
        
        assert folder_info is not None
        assert len(folder_info.files) == 1
        assert len(folder_info.subfolders) == 2
        
        main_file = folder_info.files[0]
        assert main_file.file_path == "main.py"
        assert main_file.language == Language.PYTHON
        assert len(main_file.functions) == 1
        assert main_file.functions[0].name == "main"

    @pytest.mark.asyncio
    async def test_verify_import_analysis(self, temp_project):
        """测试验证导入分析 - 验证导入路径解析"""
        main_file_path = os.path.join(temp_project, "main.py")
        analyzer = FileAstAnalyzer(temp_project, main_file_path)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert len(file_info.imports) > 0
        
        imports_str = " ".join(file_info.imports)
        assert "os" in imports_str or any("os" in imp for imp in file_info.imports)

    @pytest.mark.asyncio
    async def test_verify_class_extraction(self, temp_project):
        """测试验证类提取 - 验证类和方法信息"""
        user_file_path = os.path.join(temp_project, "models", "user.py")
        analyzer = FileAstAnalyzer(temp_project, user_file_path)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert len(file_info.classes) == 1
        
        user_class = file_info.classes[0]
        assert user_class.name == "User"
        assert len(user_class.methods) == 2
        
        method_names = [m.name for m in user_class.methods]
        assert "__init__" in method_names
        assert "get_name" in method_names
        
        for method in user_class.methods:
            assert method.type == FunctionType.METHOD.value
            assert method.class_name == "User"

    @pytest.mark.asyncio
    async def test_verify_function_extraction(self, temp_project):
        """测试验证函数提取 - 验证函数信息"""
        helper_file_path = os.path.join(temp_project, "utils", "helper.py")
        analyzer = FileAstAnalyzer(temp_project, helper_file_path)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert len(file_info.functions) == 1
        
        func = file_info.functions[0]
        assert func.name == "process_data"
        assert func.type == FunctionType.FUNCTION.value
        assert func.docstring is not None

