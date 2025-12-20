import os
import tempfile
import pytest
from app.codeast.services.ast_analyzer import FileAstAnalyzer
from app.codeast.models.model import Language


class TestGoASTAnalysis:
    """测试Go AST分析功能 - 验证分析结果的正确性"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_extract_go_package(self, temp_dir):
        """测试提取Go包和函数"""
        test_file = os.path.join(temp_dir, "main.go")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}

func calculate(a int, b int) int {
    return a + b
}
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.GO

    @pytest.mark.asyncio
    async def test_extract_go_struct(self, temp_dir):
        """测试提取Go结构体"""
        test_file = os.path.join(temp_dir, "user.go")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
package model

type User struct {
    Name  string
    Email string
}

func (u *User) GetName() string {
    return u.Name
}
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.GO

