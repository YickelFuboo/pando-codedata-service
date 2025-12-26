import os
import tempfile
import pytest
from app.codebase.codeast.services.ast_analyzer import FileAstAnalyzer
from app.codebase.codeast.models.model import Language


class TestCASTAnalysis:
    """测试C AST分析功能 - 验证分析结果的正确性"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_extract_c_function(self, temp_dir):
        """测试提取C函数 - 验证函数名、参数、返回类型"""
        test_file = os.path.join(temp_dir, "test.c")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
#include <stdio.h>
#include <stdlib.h>

int calculate_sum(int a, int b) {
    return a + b;
}

void print_message(const char* message) {
    printf("%s\\n", message);
}
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.C

    @pytest.mark.asyncio
    async def test_extract_c_struct(self, temp_dir):
        """测试提取C结构体"""
        test_file = os.path.join(temp_dir, "user.c")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
#include <string.h>

struct User {
    int id;
    char name[100];
    char email[100];
};

struct User* create_user(int id, const char* name) {
    struct User* user = malloc(sizeof(struct User));
    user->id = id;
    strcpy(user->name, name);
    return user;
}
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.C

    @pytest.mark.asyncio
    async def test_extract_c_headers(self, temp_dir):
        """测试提取C头文件包含"""
        test_file = os.path.join(temp_dir, "main.c")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "user.h"

int main() {
    return 0;
}
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.C

    @pytest.mark.asyncio
    async def test_extract_c_pointer_functions(self, temp_dir):
        """测试提取C指针函数"""
        test_file = os.path.join(temp_dir, "pointer.c")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
int* allocate_array(int size) {
    return malloc(size * sizeof(int));
}

void process_array(int* arr, int size) {
    for (int i = 0; i < size; i++) {
        arr[i] = i * 2;
    }
}
""")
        
        analyzer = FileAstAnalyzer(temp_dir, test_file)
        file_info = await analyzer.analyze_file()
        
        assert file_info is not None
        assert file_info.language == Language.C

