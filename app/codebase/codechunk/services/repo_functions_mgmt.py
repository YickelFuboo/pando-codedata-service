import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.codebase.codechunk.models.model import RepoFunctions
from app.codebase.codechunk.schemes.scheme import FunctionDataCreate, FunctionDataUpdate, SearchResponse, SearchResult, SearchRequest as SearchRequestDto
from app.codebase.codechunk.constants import get_function_vector_space
from app.codebase.codesummary.services.code_summary import CodeSummary
from app.codebase.codesummary.models.model import ContentType
from app.infrastructure.llms import embedding_factory
from app.infrastructure.vector_store import VECTOR_STORE_CONN, SearchRequest, MatchDenseExpr
import numpy as np


class RepoFunctionsMgmt:
    """管理函数数据表及对应内容的向量化"""
    
    def __init__(self, db_session: AsyncSession, repo_id: Optional[str] = None):
        self.db_session = db_session
        self.repo_id = repo_id
    
    async def create(self, data: FunctionDataCreate) -> RepoFunctions:
        """创建函数数据记录"""
        try:
            function_data = RepoFunctions(
                repo_id=data.repo_id,
                source_code=data.source_code,
                file_path=data.file_path,
                start_line=data.start_line,
                end_line=data.end_line,
                function_name=data.function_name,
                function_signature=data.function_signature,
                summary=None,
                is_summarized=False,
                is_vectorized=False
            )
            self.db_session.add(function_data)
            await self.db_session.commit()
            await self.db_session.refresh(function_data)
            return function_data
        except Exception as e:
            await self.db_session.rollback()
            logging.error(f"创建函数数据失败: {e}")
            raise
    
    async def get_by_id(self, function_id: str) -> Optional[RepoFunctions]:
        """根据ID获取函数数据"""
        try:
            result = await self.db_session.execute(
                select(RepoFunctions).where(RepoFunctions.id == function_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logging.error(f"获取函数数据失败: {e}")
            return None
    
    async def get_by_repo_id(self, repo_id: str, limit: int = 100, offset: int = 0) -> List[RepoFunctions]:
        """根据代码仓ID获取函数数据列表"""
        try:
            result = await self.db_session.execute(
                select(RepoFunctions)
                .where(RepoFunctions.repo_id == repo_id)
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
        except Exception as e:
            logging.error(f"获取函数数据列表失败: {e}")
            return []
    
    async def get_unvectorized(self, limit: int = 100) -> List[RepoFunctions]:
        """获取未向量化的函数数据"""
        try:
            if not self.repo_id:
                logging.error("repo_id不能为空")
                return []
            query = select(RepoFunctions).where(
                RepoFunctions.is_vectorized == False,
                RepoFunctions.repo_id == self.repo_id
            )
            query = query.limit(limit)
            result = await self.db_session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logging.error(f"获取未向量化函数数据失败: {e}")
            return []
    
    async def get_unsummarized(self, limit: int = 100) -> List[RepoFunctions]:
        """获取未生成summary的函数数据"""
        try:
            if not self.repo_id:
                logging.error("repo_id不能为空")
                return []
            query = select(RepoFunctions).where(
                RepoFunctions.is_summarized == False,
                RepoFunctions.repo_id == self.repo_id
            )
            query = query.limit(limit)
            result = await self.db_session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logging.error(f"获取未生成summary的函数数据失败: {e}")
            return []
    
    async def update(self, function_id: str, data: FunctionDataUpdate) -> Optional[RepoFunctions]:
        """更新函数数据"""
        try:
            function_data = await self.get_by_id(function_id)
            if not function_data:
                return None
            
            if data.summary is not None:
                function_data.summary = data.summary
            if data.is_summarized is not None:
                function_data.is_summarized = data.is_summarized
            if data.is_vectorized is not None:
                function_data.is_vectorized = data.is_vectorized
            if data.vector_id is not None:
                function_data.vector_id = data.vector_id
            
            await self.db_session.commit()
            await self.db_session.refresh(function_data)
            return function_data
        except Exception as e:
            await self.db_session.rollback()
            logging.error(f"更新函数数据失败: {e}")
            return None
    
    async def delete(self, function_id: str) -> bool:
        """删除函数数据"""
        try:
            function_data = await self.get_by_id(function_id)
            if not function_data:
                return False
            
            await self.db_session.delete(function_data)
            await self.db_session.commit()
            return True
        except Exception as e:
            await self.db_session.rollback()
            logging.error(f"删除函数数据失败: {e}")
            return False
    
    async def generate_summary(self, function_data: RepoFunctions) -> str:
        """生成函数功能描述"""
        try:
            summary = await CodeSummary.llm_summarize(
                function_data.source_code,
                ContentType.FUNCTION
            )
            return summary
        except Exception as e:
            logging.error(f"生成函数摘要失败: {e}")
            return ""
    
    async def vectorize(self, function_data: RepoFunctions) -> bool:
        """向量化函数数据"""
        try:
            if function_data.is_vectorized and function_data.vector_id:
                return True
            
            text_to_vectorize = function_data.summary or function_data.source_code
            
            embedding_model = embedding_factory.create_model()
            if not embedding_model:
                logging.error("无法创建嵌入模型")
                return False
            
            vectors, _ = await embedding_model.encode([text_to_vectorize])
            if vectors is None or len(vectors) == 0:
                logging.error("向量化失败")
                return False
            
            vector = vectors[0].tolist()
            
            record = {
                "id": function_data.id,
                "repo_id": function_data.repo_id,
                "source_code": function_data.source_code,
                "file_path": function_data.file_path,
                "start_line": function_data.start_line,
                "end_line": function_data.end_line,
                "function_name": function_data.function_name,
                "function_signature": function_data.function_signature,
                "summary": function_data.summary,
                "vector": vector
            }
            
            space_name = await get_function_vector_space(function_data.repo_id, vector_size=len(vector))
            vector_ids = await VECTOR_STORE_CONN.insert_records(space_name, [record])
            if vector_ids and len(vector_ids) > 0:
                await self.update(function_data.id, FunctionDataUpdate(
                    is_vectorized=True,
                    vector_id=vector_ids[0]
                ))
                return True
            return False
        except Exception as e:
            logging.error(f"向量化函数数据失败: {e}")
            return False
    
    async def batch_generate_summary(self, limit: int = 100) -> int:
        """批量生成函数功能描述"""
        try:
            unsummarized = await self.get_unsummarized(limit=limit)
            count = 0
            for function_data in unsummarized:
                try:
                    summary = await self.generate_summary(function_data)
                    if summary:
                        await self.update(function_data.id, FunctionDataUpdate(
                            summary=summary,
                            is_summarized=True
                        ))
                        count += 1
                except Exception as e:
                    logging.error(f"生成函数{function_data.id}摘要失败: {e}")
                    continue
            return count
        except Exception as e:
            logging.error(f"批量生成summary失败: {e}")
            return 0
    
    async def batch_vectorize(self, limit: int = 100) -> int:
        """批量向量化未向量化的函数数据"""
        try:
            unvectorized = await self.get_unvectorized(limit=limit)
            count = 0
            for function_data in unvectorized:
                if await self.vectorize(function_data):
                    count += 1
            return count
        except Exception as e:
            logging.error(f"批量向量化失败: {e}")
            return 0
    
    async def search(self, request: SearchRequestDto) -> SearchResponse:
        """向量搜索函数数据"""
        try:
            repo_id = request.repo_id or self.repo_id
            if not repo_id:
                logging.error("repo_id不能为空")
                return SearchResponse(results=[], total=0)
            
            embedding_model = embedding_factory.create_model()
            if not embedding_model:
                logging.error("无法创建嵌入模型")
                return SearchResponse(results=[], total=0)
            
            query_vector, _ = await embedding_model.encode_queries(request.query)
            if query_vector is None:
                logging.error("查询向量化失败")
                return SearchResponse(results=[], total=0)
            
            vector_expr = MatchDenseExpr(
                field="vector",
                vector=query_vector.tolist(),
                top_k=request.top_k
            )
            
            search_request = SearchRequest(
                query=vector_expr,
                top_k=request.top_k
            )
            
            space_name = f"repo_{repo_id}_function"
            space_names = [space_name]
            if request.file_path:
                search_request.filter = {"term": {"file_path": request.file_path}}
            
            result = await VECTOR_STORE_CONN.search(space_names, search_request)
            
            total = VECTOR_STORE_CONN.get_total(result)
            chunk_ids = VECTOR_STORE_CONN.get_chunk_ids(result)
            fields = VECTOR_STORE_CONN.get_fields(result, ["id", "source_code", "file_path", "start_line", "end_line", "summary", "function_name"])
            
            results = []
            for i, chunk_id in enumerate(chunk_ids):
                field_data = fields.get(chunk_id, {})
                results.append(SearchResult(
                    id=field_data.get("id", chunk_id),
                    source_code=field_data.get("source_code", ""),
                    file_path=field_data.get("file_path", ""),
                    start_line=field_data.get("start_line", 0),
                    end_line=field_data.get("end_line", 0),
                    summary=field_data.get("summary"),
                    score=field_data.get("_score")
                ))
            
            return SearchResponse(results=results, total=total)
        except Exception as e:
            logging.error(f"搜索函数数据失败: {e}")
            return SearchResponse(results=[], total=0)
    
    async def text_search(self, request: SearchRequestDto) -> SearchResponse:
        """文本搜索函数数据"""
        try:
            repo_id = request.repo_id or self.repo_id
            if not repo_id:
                logging.error("repo_id不能为空")
                return SearchResponse(results=[], total=0)
            
            query = select(RepoFunctions).where(RepoFunctions.repo_id == repo_id)
            
            if request.file_path:
                query = query.where(RepoFunctions.file_path == request.file_path)
            
            if request.query:
                query = query.where(
                    (RepoFunctions.source_code.contains(request.query)) |
                    (RepoFunctions.summary.contains(request.query)) |
                    (RepoFunctions.function_name.contains(request.query))
                )
            
            query = query.limit(request.top_k)
            
            result = await self.db_session.execute(query)
            functions = list(result.scalars().all())
            
            results = [
                SearchResult(
                    id=func.id,
                    source_code=func.source_code,
                    file_path=func.file_path,
                    start_line=func.start_line,
                    end_line=func.end_line,
                    summary=func.summary
                )
                for func in functions
            ]
            
            return SearchResponse(results=results, total=len(results))
        except Exception as e:
            logging.error(f"文本搜索函数数据失败: {e}")
            return SearchResponse(results=[], total=0)

