import os
import javalang
import logging
from typing import Optional, List
from .base import LanguageAnalyzer
from ...models.model import FileInfo, FunctionInfo, ClassInfo, ClassType, FunctionType, Language as Lang


class JavaAnalyzer(LanguageAnalyzer):
    def __init__(self, base_path: str, file_path: str):
        """初始化Java分析器"""
        super().__init__(base_path, file_path)
    
    async def analyze_file(self) -> Optional[FileInfo]:
        """分析Java文件"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = javalang.parse.parse(content)
            if not tree:
                raise Exception(f"Failed to parse Java file: {self.file_path}")
                
            functions = []
            classes = []
            
            # 分析Java类和方法
            for path, node in tree.filter(javalang.tree.ClassDeclaration):
                class_node = await self._create_class_node(node, content)
                if class_node:
                    classes.append(class_node)
            
            return FileInfo(
                file_path=os.path.relpath(self.file_path, self.base_path),
                language=Lang.JAVA,
                functions=functions,
                classes=classes,
                imports=self.get_imports(content)
            )

        except Exception as e:
            logging.error(f"Error analyzing Java file {self.file_path}: {str(e)}")
            return None
        
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

    async def _create_class_node(self, node, content: str) -> Optional[ClassInfo]:
        """创建类节点"""
        methods = []
        for method in node.methods:
            if not method.name.startswith('_'):
                method_node = await self._create_method_node(method, content)
                if method_node:
                    methods.append(method_node)
        
        source_code = content[node.position.line:node.position.end_line]
        
        return ClassInfo(
            file_path=os.path.relpath(self.file_path, self.base_path),
            name=node.name,
            node_type=ClassType.CLASS,
            source_code=source_code,
            start_line=node.position.line,
            end_line=node.position.end_line,
            methods=methods,
            attributes=self._get_class_attributes(node),
            docstring=self._get_comment(node)
        )

    async def _create_method_node(self, node, content: str) -> Optional[FunctionInfo]:
        """创建方法节点"""
        source_code = content[node.position.line:node.position.end_line]
        
        return FunctionInfo(
            file_path=os.path.relpath(self.file_path, self.base_path),
            name=node.name,
            signature=self._get_method_signature(node),
            type=FunctionType.METHOD,
            source_code=source_code,
            start_line=node.position.line,
            end_line=node.position.end_line,
            params=self._get_method_params(node),
            param_types=self._get_param_types(node),
            returns=self._get_method_returns(node),
            return_types=self._get_return_types(node),
            docstring=self._get_comment(node)
        ) 