import pytest
from app.codeast.models.model import (
    FileInfo, FolderInfo, ClassInfo, FunctionInfo, CallInfo,
    Language, FunctionType
)


class TestModels:
    """测试数据模型结构"""

    def test_file_info_structure(self):
        """验证FileInfo数据结构"""
        file_info = FileInfo(
            file_path="test.py",
            language=Language.PYTHON,
            summary="",
            functions=[],
            classes=[],
            imports=[]
        )
        assert hasattr(file_info, 'file_path')
        assert hasattr(file_info, 'language')
        assert hasattr(file_info, 'functions')
        assert hasattr(file_info, 'classes')
        assert hasattr(file_info, 'imports')

    def test_function_info_structure(self):
        """验证FunctionInfo数据结构"""
        func_info = FunctionInfo(
            project_id="test_project",
            name="test_function",
            full_name="test.module.test_function",
            signature="test_function",
            type=FunctionType.FUNCTION.value,
            source_code="def test_function(): pass",
            params=[],
            param_types=[],
            returns=[],
            return_types=[]
        )
        assert hasattr(func_info, 'name')
        assert hasattr(func_info, 'full_name')
        assert hasattr(func_info, 'signature')
        assert hasattr(func_info, 'type')
        assert hasattr(func_info, 'params')
        assert hasattr(func_info, 'calls')

    def test_class_info_structure(self):
        """验证ClassInfo数据结构"""
        class_info = ClassInfo(
            project_id="test_project",
            name="TestClass",
            full_name="test.module.TestClass"
        )
        assert hasattr(class_info, 'name')
        assert hasattr(class_info, 'full_name')
        assert hasattr(class_info, 'methods')
        assert hasattr(class_info, 'base_classes')

