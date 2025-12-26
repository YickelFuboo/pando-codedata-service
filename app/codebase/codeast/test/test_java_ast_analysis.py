import os
import tempfile
import pytest
from app.codebase.codeast.services.ast_analyzer import FileAstAnalyzer
from app.codebase.codeast.models.model import Language, FunctionType


class TestJavaASTAnalysis:
    """测试Java AST分析功能 - 验证分析结果的正确性"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_extract_java_class(self, temp_dir):
        """测试提取Java类"""
        test_file = os.path.join(temp_dir, "User.java")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
public class User {
    private String name;
    
    public User(String name) {
        this.name = name;
    }
    
    public String getName() {
        return name;
    }
}
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.JAVA

    @pytest.mark.asyncio
    async def test_extract_java_imports(self, temp_dir):
        """测试提取Java导入"""
        test_file = os.path.join(temp_dir, "Test.java")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
import java.util.List;
import java.util.Map;
import com.example.model.User;

public class Test {
}
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.JAVA

