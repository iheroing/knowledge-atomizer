"""Markdown Parser for knowledge atoms."""

import re
import uuid
from typing import List, Optional, Tuple

from .models import DocumentNode, DocumentTree, HeadingLevel


class MarkdownParser:
    """Markdown 文档解析器
    
    解析 Markdown 文件的标题层级结构，提取知识原子。
    支持 ATX 风格标题 (# ## ### 等)
    """
    
    # ATX heading pattern: # to ###### followed by space and text
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    
    def parse(self, file_path: str) -> DocumentTree:
        """解析 Markdown 文件
        
        Args:
            file_path: Markdown 文件路径
            
        Returns:
            DocumentTree 结构
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_content(content, file_path)
    
    def parse_content(self, content: str, source_file: str = "unknown.md") -> DocumentTree:
        """解析 Markdown 内容
        
        Args:
            content: Markdown 文本内容
            source_file: 来源文件名
            
        Returns:
            DocumentTree 结构
        """
        # Extract filename from path
        if '/' in source_file:
            source_file = source_file.split('/')[-1]
        if '\\' in source_file:
            source_file = source_file.split('\\')[-1]
        
        # Split content into sections by headings
        sections = self._split_by_headings(content)
        
        # Build document tree
        nodes = []
        for level, title, body in sections:
            node = DocumentNode(
                id=str(uuid.uuid4()),
                title=title.strip(),
                content=body.strip() if body else "",
                level=HeadingLevel(min(level, 5)),  # Cap at H5
                children=[]
            )
            nodes.append(node)
        
        # Build hierarchy
        root_nodes = self._build_hierarchy(nodes)
        
        return DocumentTree(
            root_nodes=root_nodes,
            source_file=source_file
        )
    
    def _split_by_headings(self, content: str) -> List[Tuple[int, str, str]]:
        """将内容按标题分割
        
        Args:
            content: Markdown 内容
            
        Returns:
            List of (level, title, body) tuples
        """
        sections = []
        lines = content.split('\n')
        
        current_level = 0
        current_title = ""
        current_body_lines = []
        
        for line in lines:
            heading_match = self.HEADING_PATTERN.match(line)
            
            if heading_match:
                # Save previous section if exists
                if current_title:
                    body = '\n'.join(current_body_lines).strip()
                    sections.append((current_level, current_title, body))
                
                # Start new section
                hashes = heading_match.group(1)
                current_level = len(hashes)
                current_title = heading_match.group(2)
                current_body_lines = []
            else:
                # Add to current body
                current_body_lines.append(line)
        
        # Don't forget the last section
        if current_title:
            body = '\n'.join(current_body_lines).strip()
            sections.append((current_level, current_title, body))
        
        # Handle case where there's content before any heading
        # (treat as intro, skip for now or could add as H1)
        
        return sections
    
    def _build_hierarchy(self, nodes: List[DocumentNode]) -> List[DocumentNode]:
        """构建层级关系
        
        Args:
            nodes: 扁平的节点列表
            
        Returns:
            根节点列表（带有正确的 parent_id 和 children）
        """
        if not nodes:
            return []
        
        # Stack to track parent candidates at each level
        # stack[i] = node at level i+1
        stack: List[Optional[DocumentNode]] = [None] * 6
        root_nodes = []
        
        for node in nodes:
            level = node.level.value
            
            # Find parent (nearest node with smaller level)
            parent = None
            for i in range(level - 1, 0, -1):
                if stack[i - 1] is not None:
                    parent = stack[i - 1]
                    break
            
            if parent:
                parent.children.append(node)
            else:
                root_nodes.append(node)
            
            # Update stack
            stack[level - 1] = node
            # Clear deeper levels
            for i in range(level, 6):
                stack[i] = None
        
        return root_nodes
