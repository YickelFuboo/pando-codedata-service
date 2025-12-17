import re
import os
from tree_sitter import Language, Parser
from typing import Optional, List
from .base import LanguageAnalyzer
from ..models import FileNode, FunctionNode, ClassNode, NodeType, Language as Lang
from ..summary import LLMSummary

# 全局变量存储已加载的语言
LANGUAGES = {}

def get_language():
    """获取或初始化 C++ 语言解析器"""
    if 'cpp' not in LANGUAGES:
        try:
            # 构建语言库
            Language.build_library(
                'build/my-languages.so',
                [
                    'vendor/tree-sitter-cpp'
                ]
            )
            # 加载语言
            LANGUAGES['cpp'] = Parser()
            LANGUAGES['cpp'].set_language(
                Language.load('build/my-languages.so')
            )
        except Exception as e:
            print(f"Error loading C++ language: {str(e)}")
            return None
    return LANGUAGES['cpp']

class CppAnalyzer(LanguageAnalyzer):
    def __init__(self, project_id: str = None, project_dir: str = None):
        """初始化C++分析器"""
        super().__init__(project_id, project_dir)        
        # 获取解析器
        self.parser = get_language()
    
    async def analyze_file(self, file_path: str) -> Optional[FileNode]:
        """分析C++文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        try:
            tree = self.parser.parse(bytes(content, 'utf8'))
            if not tree:
                return None
                
            functions = []
            classes = []
            
            # 遍历语法树
            cursor = tree.walk()
            
            async def visit_node(node):
                if node.type == 'function_definition':
                    func_name = self._get_function_name(node)
                    if not func_name.startswith('_'):
                        func_node = await self._create_function_node(node, content)
                        if func_node:
                            functions.append(func_node)
                elif node.type == 'class_definition':
                    class_node = await self._create_class_node(node, content)
                    if class_node:
                        classes.append(class_node)
                
                for child in node.children:
                    await visit_node(child)
            
            await visit_node(tree.root_node)
            
            # 生成文件摘要
            summary =await LLMSummary.llm_summarize(content, "file")
            
            # 转换为相对路径
            rel_path = os.path.relpath(file_path, self.project_dir) if self.project_dir else file_path
            
            return FileNode(
                project_id=self.project_id,
                file_path=rel_path,
                language=Lang.CPP,
                summary=summary,
                functions=functions,
                classes=classes,
                imports=self.get_imports(content)
            )
        except Exception as e:
            print(f"Error analyzing C++ file {file_path}: {str(e)}")
            return None
    
    def get_imports(self, content: str) -> List[str]:
        """获取C++文件的导入依赖"""
        imports = []
        include_pattern = r'#include\s*[<"]([^>"]+)[>"]'
        for match in re.finditer(include_pattern, content):
            imports.append(match.group(1))
        return imports
        
    def _get_function_name(self, node) -> str:
        """获取函数名"""
        for child in node.children:
            if child.type == 'identifier':
                return child.text.decode('utf8')
        return ''
        
    async def _create_function_node(self, node, content: str) -> Optional[FunctionNode]:
        """创建函数节点"""
        func_name = self._get_function_name(node)
        if not func_name:
            return None
            
        source_code = content[node.start_byte:node.end_byte]
        
        return FunctionNode(
            project_id=self.project_id,
            file_path=self.file_path,
            name=func_name,
            signature=self._get_function_signature(node, content),
            source_code=source_code,
            summary=await LLMSummary.llm_summarize(source_code, "function"),
            params=self._get_function_params(node),
            param_types=self._get_param_types(node),
            returns=self._get_function_returns(node),
            return_types=self._get_return_types(node),
            docstring=self._get_comment(node, content)
        )
        
    async def _create_class_node(self, node, content: str) -> Optional[ClassNode]:
        """创建类节点"""
        class_name = self._get_class_name(node)
        if not class_name:
            return None
            
        source_code = content[node.start_byte:node.end_byte]
        
        return ClassNode(
            project_id=self.project_id,
            file_path=self.file_path,
            name=class_name,
            node_type=NodeType.CLASS,
            source_code=source_code,
            summary=await LLMSummary.llm_summarize(source_code, "class"),
            methods=await self._get_class_methods(node, content),
            attributes=self._get_class_attributes(node),
            docstring=self._get_comment(node, content)
        ) 