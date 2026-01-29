import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.codebase.codechunk.models.model import RepoClasses
from app.codebase.codechunk.schemes.scheme import ClassDataCreate, ClassDataUpdate, SearchResponse, SearchResult, SearchRequest as SearchRequestDto
from app.codebase.codechunk.constants import get_class_vector_space
from app.codebase.codesummary.services.code_summary import CodeSummary
from app.codebase.codesummary.models.model import ContentType
from app.infrastructure.llms import embedding_factory
from app.infrastructure.vector_store import VECTOR_STORE_CONN, SearchRequest, MatchDenseExpr
import numpy as np


class RepoClassesMgmt:
    """管理类数据表及对应内容的向量化"""
    
    def __init__(self, db_session: AsyncSession, repo_id: Optional[str] = None):
        self.db_session = db_session
        self.repo_id = repo_id
    
    async def create(self, data: ClassDataCreate) -> RepoClasses:
        """创建类数据记录"""
        try:
            class_data = RepoClasses(
                repo_id=data.repo_id,
                source_code=data.source_code,
                file_path=data.file_path,
                start_line=data.start_line,
                end_line=data.end_line,
                class_name=data.class_name,
                class_type=data.class_type,
                summary=None,
                is_summarized=False,
                is_vectorized=False
            )
            self.db_session.add(class_data)
            await self.db_session.commit()
            await self.db_session.refresh(class_data)
            return class_data
        except Exception as e:
            await self.db_session.rollback()
            logging.error(f"创建类数据失败: {e}")
            raise
    
    async def get_by_id(self, class_id: str) -> Optional[RepoClasses]:
        """根据ID获取类数据"""
        try:
            result = await self.db_session.execute(
                select(RepoClasses).where(RepoClasses.id == class_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logging.error(f"获取类数据失败: {e}")
            return None
    
    async def get_by_repo_id(self, repo_id: str, limit: int = 100, offset: int = 0) -> List[RepoClasses]:
        """根据代码仓ID获取类数据列表"""
        try:
            result = await self.db_session.execute(
                select(RepoClasses)
                .where(RepoClasses.repo_id == repo_id)
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
        except Exception as e:
            logging.error(f"获取类数据列表失败: {e}")
            return []
    
    async def get_unvectorized(self, limit: int = 100) -> List[RepoClasses]:
        """获取未向量化的类数据"""
        try:
            if not self.repo_id:
                logging.error("repo_id不能为空")
                return []
            query = select(RepoClasses).where(
                RepoClasses.is_vectorized == False,
                RepoClasses.repo_id == self.repo_id
            )
            query = query.limit(limit)
            result = await self.db_session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logging.error(f"获取未向量化类数据失败: {e}")
            return []
    
    async def get_unsummarized(self, limit: int = 100) -> List[RepoClasses]:
        """获取未生成summary的类数据"""
        try:
            if not self.repo_id:
                logging.error("repo_id不能为空")
                return []
            query = select(RepoClasses).where(
                RepoClasses.is_summarized == False,
                RepoClasses.repo_id == self.repo_id
            )
            query = query.limit(limit)
            result = await self.db_session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logging.error(f"获取未生成summary的类数据失败: {e}")
            return []
    
    async def update(self, class_id: str, data: ClassDataUpdate) -> Optional[RepoClasses]:
        """更新类数据"""
        try:
            class_data = await self.get_by_id(class_id)
            if not class_data:
                return None
            
            if data.summary is not None:
                class_data.summary = data.summary
            if data.is_summarized is not None:
                class_data.is_summarized = data.is_summarized
            if data.is_vectorized is not None:
                class_data.is_vectorized = data.is_vectorized
            if data.vector_id is not None:
                class_data.vector_id = data.vector_id
            
            await self.db_session.commit()
            await self.db_session.refresh(class_data)
            return class_data
        except Exception as e:
            await self.db_session.rollback()
            logging.error(f"更新类数据失败: {e}")
            return None
    
    async def delete(self, class_id: str) -> bool:
        """删除类数据"""
        try:
            class_data = await self.get_by_id(class_id)
            if not class_data:
                return False
            
            await self.db_session.delete(class_data)
            await self.db_session.commit()
            return True
        except Exception as e:
            await self.db_session.rollback()
            logging.error(f"删除类数据失败: {e}")
            return False
    
    async def generate_summary(self, class_data: RepoClasses) -> str:
        """生成类功能描述"""
        try:
            content_type = ContentType.CLASS
            if class_data.class_type == "struct":
                content_type = ContentType.STRUCT
            elif class_data.class_type == "interface":
                content_type = ContentType.INTERFACE
            
            summary = await CodeSummary.llm_summarize(
                class_data.source_code,
                content_type
            )
            return summary
        except Exception as e:
            logging.error(f"生成类摘要失败: {e}")
            return ""
    
    async def vectorize(self, class_data: RepoClasses) -> bool:
        """向量化类数据"""
        try:
            if class_data.is_vectorized and class_data.vector_id:
                return True
            
            text_to_vectorize = class_data.summary or class_data.source_code
            
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
                "id": class_data.id,
                "repo_id": class_data.repo_id,
                "source_code": class_data.source_code,
                "file_path": class_data.file_path,
                "start_line": class_data.start_line,
                "end_line": class_data.end_line,
                "class_name": class_data.class_name,
                "class_type": class_data.class_type,
                "summary": class_data.summary,
                "vector": vector
            }
            
            space_name = await get_class_vector_space(class_data.repo_id, vector_size=len(vector))
            vector_ids = await VECTOR_STORE_CONN.insert_records(space_name, [record])
            if vector_ids and len(vector_ids) > 0:
                await self.update(class_data.id, ClassDataUpdate(
                    is_vectorized=True,
                    vector_id=vector_ids[0]
                ))
                return True
            return False
        except Exception as e:
            logging.error(f"向量化类数据失败: {e}")
            return False
    
    async def batch_generate_summary(self, limit: int = 100) -> int:
        """批量生成类功能描述"""
        try:
            unsummarized = await self.get_unsummarized(limit=limit)
            count = 0
            for class_data in unsummarized:
                try:
                    summary = await self.generate_summary(class_data)
                    if summary:
                        await self.update(class_data.id, ClassDataUpdate(
                            summary=summary,
                            is_summarized=True
                        ))
                        count += 1
                except Exception as e:
                    logging.error(f"生成类{class_data.id}摘要失败: {e}")
                    continue
            return count
        except Exception as e:
            logging.error(f"批量生成summary失败: {e}")
            return 0
    
    async def batch_vectorize(self, limit: int = 100) -> int:
        """批量向量化未向量化的类数据"""
        try:
            unvectorized = await self.get_unvectorized(limit=limit)
            count = 0
            for class_data in unvectorized:
                if await self.vectorize(class_data):
                    count += 1
            return count
        except Exception as e:
            logging.error(f"批量向量化失败: {e}")
            return 0
    
    async def search(self, request: SearchRequestDto) -> SearchResponse:
        """向量搜索类数据"""
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
            
            space_name = f"repo_{repo_id}_class"
            space_names = [space_name]
            if request.file_path:
                search_request.filter = {"term": {"file_path": request.file_path}}
            
            result = await VECTOR_STORE_CONN.search(space_names, search_request)
            
            total = VECTOR_STORE_CONN.get_total(result)
            chunk_ids = VECTOR_STORE_CONN.get_chunk_ids(result)
            fields = VECTOR_STORE_CONN.get_fields(result, ["id", "source_code", "file_path", "start_line", "end_line", "summary", "class_name"])
            
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
            logging.error(f"搜索类数据失败: {e}")
            return SearchResponse(results=[], total=0)
    
    async def text_search(self, request: SearchRequestDto) -> SearchResponse:
        """文本搜索类数据"""
        try:
            repo_id = request.repo_id or self.repo_id
            if not repo_id:
                logging.error("repo_id不能为空")
                return SearchResponse(results=[], total=0)
            
            query = select(RepoClasses).where(RepoClasses.repo_id == repo_id)
            
            if request.file_path:
                query = query.where(RepoClasses.file_path == request.file_path)
            
            if request.query:
                query = query.where(
                    (RepoClasses.source_code.contains(request.query)) |
                    (RepoClasses.summary.contains(request.query)) |
                    (RepoClasses.class_name.contains(request.query))
                )
            
            query = query.limit(request.top_k)
            
            result = await self.db_session.execute(query)
            classes = list(result.scalars().all())
            
            results = [
                SearchResult(
                    id=cls.id,
                    source_code=cls.source_code,
                    file_path=cls.file_path,
                    start_line=cls.start_line,
                    end_line=cls.end_line,
                    summary=cls.summary
                )
                for cls in classes
            ]
            
            return SearchResponse(results=results, total=len(results))
        except Exception as e:
            logging.error(f"文本搜索类数据失败: {e}")
            return SearchResponse(results=[], total=0)

