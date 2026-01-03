"""Markdown Parser for knowledge atoms."""

import re
import uuid
from typing import List, Optional, Tuple

from .models import DocumentNode, DocumentTree, HeadingLevel


class MarkdownParser:
    """Markdown 文件解析器
    
    解析 Markdown 文件的标题层级结构，生成 DocumentTree
    """
    
    # Heading pattern: # to ###### at start of line
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    
    def parse(self, file_path: str) -> DocumentTree:
        """解析 Markdown 文件
        
        Args:
            file_path: Path to markdown file
            
        Returns:
            DocumentTree with parsed structure
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_content(content, file_path)
    
    def parse_content(self, content: str, source_file: str = "unknown.md") -> DocumentTree:
        """解析 Markdown 内容
        
        Args:
            content: Markdown content string
            source_file: Source file name for reference
            
        Returns:
            DocumentTree with parsed structure
        """
        # Extract filename from path
        import os
        filename = os.path.basename(source_file)
        
        # Find all headings with their positions
        headings = self._extract_headings(content)
        
        if not headings:
            # No headings found, treat entire content as single node
            root = DocumentNode(
                id=str(uuid.uuid4()),
                title=filename.rsplit('.', 1)[0],
                content=content.strip(),
                level=HeadingLevel.H1,
                children=[]
            )
            return DocumentTree(root=root, source_file=filename)
        
        # Build tree from headings
        root = self._build_tree(content, headings, filename)
        
        return DocumentTree(root=root, source_file=filename)
    
    def _extract_headings(self, content: str) -> List[Tuple[int, int, str, int]]:
        """Extract all headings with positions.
        
        Args:
            content: Markdown content
            
        Returns:
            List of (start_pos, level, title, end_of_title_pos)
        """
        headings = []
        
        for match in self.HEADING_PATTERN.finditer(content):
            level = len(match.group(1))  # Number of # characters
            title = match.group(2).strip()
            start_pos = match.start()
            end_pos = match.end()
            
            headings.append((start_pos, level, title, end_pos))
        
        return headings
    
    def _build_tree(
        self, 
        content: str, 
        headings: List[Tuple[int, int, str, int]],
        filename: str
    ) -> DocumentNode:
        """Build document tree from headings.
        
        Args:
            content: Full markdown content
            headings: List of (start_pos, level, title, end_pos)
            filename: Source filename
            
        Returns:
            Root DocumentNode
        """
        # Create virtual root if first heading is not H1
        first_level = headings[0][1] if headings else 1
        
        if first_level > 1:
            # Create virtual root
            root = DocumentNode(
                id=str(uuid.uuid4()),
                title=filename.rsplit('.', 1)[0],
                content="",
                level=HeadingLevel.H1,
                children=[]
            )
            # Get content before first heading
            first_heading_pos = headings[0][0]
            if first_heading_pos > 0:
                root.content = content[:first_heading_pos].strip()
        else:
            # First heading is H1, use it as root
            _, level, title, end_pos = headings[0]
            
            # Get content until next heading
            next_pos = headings[1][0] if len(headings) > 1 else len(content)
            node_content = content[end_pos:next_pos].strip()
            
            root = DocumentNode(
                id=str(uuid.uuid4()),
                title=title,
                content=node_content,
                level=HeadingLevel(level),
                children=[]
            )
            headings = headings[1:]  # Remove first heading
        
        # Build children recursively
        self._add_children(root, content, headings, 0, len(headings))
        
        return root
    
    def _add_children(
        self,
        parent: DocumentNode,
        content: str,
        headings: List[Tuple[int, int, str, int]],
        start_idx: int,
        end_idx: int
    ):
        """Recursively add children to parent node.
        
        Args:
            parent: Parent node to add children to
            content: Full markdown content
            headings: All headings list
            start_idx: Start index in headings list
            end_idx: End index in headings list
        """
        if start_idx >= end_idx:
            return
        
        parent_level = parent.level.value
        i = start_idx
        
        while i < end_idx:
            start_pos, level, title, end_pos = headings[i]
            
            # Only process direct children (level = parent_level + 1)
            # Or any heading if parent is virtual root
            if level <= parent_level:
                break
            
            if level == parent_level + 1 or (parent_level == 1 and level == 2):
                # Find where this section ends
                section_end = i + 1
                while section_end < end_idx:
                    next_level = headings[section_end][1]
                    if next_level <= level:
                        break
                    section_end += 1
                
                # Get content for this node
                content_start = end_pos
                if i + 1 < len(headings):
                    content_end = headings[i + 1][0]
                else:
                    content_end = len(content)
                
                node_content = content[content_start:content_end].strip()
                
                # Remove any sub-heading content from this node's content
                if section_end > i + 1:
                    next_heading_pos = headings[i + 1][0]
                    node_content = content[content_start:next_heading_pos].strip()
                
                # Create child node
                child = DocumentNode(
                    id=str(uuid.uuid4()),
                    title=title,
                    content=node_content,
                    level=HeadingLevel(min(level, 5)),  # Cap at H5
                    children=[]
                )
                
                parent.children.append(child)
                
                # Recursively add grandchildren
                self._add_children(child, content, headings, i + 1, section_end)
                
                i = section_end
            else:
                i += 1
