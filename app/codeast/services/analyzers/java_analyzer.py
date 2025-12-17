import os
import javalang
from typing import Optional, List
from .base import LanguageAnalyzer
from ..models import FileNode, FunctionNode, ClassNode, NodeType, Language
from ..summary import LLMSummary


class JavaAnalyzer(LanguageAnalyzer):
    def __init__(self, project_id: str = None, project_dir: str = None):
        """初始化Java分析器"""
        super().__init__(project_id, project_dir)
    
    async def analyze_file(self, file_path: str) -> Optional[FileNode]:
        """分析Java文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        try:
            tree = javalang.parse.parse(content)
        except:
            return None
            
        functions = []
        classes = []
        
        # 分析Java类和方法
        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            class_node = await self._create_class_node(node, content)
            if class_node:
                classes.append(class_node)
            
        summary = await LLMSummary.llm_summarize(content, "file")
        
        # 转换为相对路径
        rel_path = os.path.relpath(file_path, self.project_dir) if self.project_dir else file_path
        
        return FileNode(
            project_id=self.project_id,
            file_path=rel_path,
            language=Language.JAVA,
            summary=summary,
            functions=functions,
            classes=classes,
            imports=self.get_imports(content)
        )
    
    def get_imports(self, content: str) -> List[str]:
        """获取Java文件的导入依赖"""
        imports = []
        try:
            tree = javalang.parse.parse(content)
            for path, node in tree.filter(javalang.tree.Import):
                imports.append(node.path)
        except:
            pass
        return imports

    async def _create_class_node(self, node, content: str) -> Optional[ClassNode]:
        """创建类节点"""
        methods = []
        for method in node.methods:
            if not method.name.startswith('_'):
                method_node = await self._create_method_node(method, content)
                if method_node:
                    methods.append(method_node)
        
        source_code = content[node.position.line:node.position.end_line]
        
        return ClassNode(
            project_id=self.project_id,
            file_path=self.file_path,
            name=node.name,
            node_type=NodeType.CLASS,
            source_code=source_code,
            summary=await LLMSummary.llm_summarize(source_code, "class"),
            methods=methods,
            attributes=self._get_class_attributes(node),
            docstring=self._get_comment(node)
        )

    async def _create_method_node(self, node, content: str) -> Optional[FunctionNode]:
        """创建方法节点"""
        source_code = content[node.position.line:node.position.end_line]
        
        return FunctionNode(
            project_id=self.project_id,
            file_path=self.file_path,
            name=node.name,
            signature=self._get_method_signature(node),
            source_code=source_code,
            summary=await LLMSummary.llm_summarize(source_code, "method"),
            params=self._get_method_params(node),
            param_types=self._get_param_types(node),
            returns=self._get_method_returns(node),
            return_types=self._get_return_types(node),
            docstring=self._get_comment(node)
        ) 