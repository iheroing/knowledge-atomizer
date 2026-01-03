"""Core data models for Knowledge Atomizer."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import uuid


class HeadingLevel(Enum):
    """文档标题层级枚举"""
    H1 = 1
    H2 = 2
    H3 = 3
    H4 = 4
    H5 = 5
    BODY = 0


@dataclass
class DocumentNode:
    """文档节点，表示一个标题或段落"""
    id: str
    title: str
    content: str
    level: HeadingLevel
    children: List['DocumentNode'] = field(default_factory=list)
    
    @staticmethod
    def create(title: str, content: str, level: HeadingLevel) -> 'DocumentNode':
        """创建新的文档节点，自动生成 UUID"""
        return DocumentNode(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            level=level,
            children=[]
        )


@dataclass
class DocumentTree:
    """文档树，表示整个文档的层级结构"""
    source_file: str
    root_nodes: List[DocumentNode] = field(default_factory=list)


@dataclass
class KnowledgeAtom:
    """知识原子，最小知识单元"""
    id: str
    title: str
    content: str
    level: int
    parent_id: Optional[str]
    parent_title: Optional[str]
    source_file: str
    children_ids: List[str] = field(default_factory=list)
    path: str = ""  # 完整知识路径，如 "章节1 > 小节1.1 > 知识点1.1.1"
    
    def is_valid(self) -> bool:
        """验证知识原子字段完整性"""
        try:
            # id 必须是有效的 UUID
            uuid.UUID(self.id)
        except (ValueError, TypeError):
            return False
        
        # title 必须是非空字符串
        if not isinstance(self.title, str) or not self.title.strip():
            return False
        
        # level 必须在 1-5 范围内
        if not isinstance(self.level, int) or not (1 <= self.level <= 5):
            return False
        
        # source_file 必须是非空字符串
        if not isinstance(self.source_file, str) or not self.source_file.strip():
            return False
        
        return True


@dataclass
class ExportResult:
    """导出结果"""
    success: bool
    message: str
    exported_count: int
    file_path: Optional[str] = None
