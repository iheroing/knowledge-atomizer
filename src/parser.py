"""Document Parser for Word documents."""

import os
import re
import uuid
from typing import List, Optional

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from .models import DocumentNode, DocumentTree, HeadingLevel


class ParserError(Exception):
    """Base exception for parser errors."""
    pass


class FileNotFoundError(ParserError):
    """Raised when file does not exist."""
    pass


class InvalidFileFormatError(ParserError):
    """Raised when file is not a valid .docx file."""
    pass


class CorruptedDocumentError(ParserError):
    """Raised when document is corrupted."""
    pass


class DocumentParser:
    """Word 文档解析器"""
    
    # Mapping of Word heading styles to HeadingLevel
    HEADING_STYLE_MAP = {
        'Heading 1': HeadingLevel.H1,
        'Heading 2': HeadingLevel.H2,
        'Heading 3': HeadingLevel.H3,
        'Heading 4': HeadingLevel.H4,
        'Heading 5': HeadingLevel.H5,
        '标题 1': HeadingLevel.H1,
        '标题 2': HeadingLevel.H2,
        '标题 3': HeadingLevel.H3,
        '标题 4': HeadingLevel.H4,
        '标题 5': HeadingLevel.H5,
    }
    
    def parse(self, file_path: str) -> DocumentTree:
        """解析 Word 文档，返回文档树
        
        Args:
            file_path: Path to the .docx file
            
        Returns:
            DocumentTree containing the parsed structure
            
        Raises:
            FileNotFoundError: If file does not exist
            InvalidFileFormatError: If file is not a valid .docx
            CorruptedDocumentError: If document is corrupted
        """
        # Validate file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # Validate file extension
        if not file_path.lower().endswith('.docx'):
            raise InvalidFileFormatError(
                f"不支持的文件格式: {os.path.splitext(file_path)[1]}。"
                f"请上传 .docx 格式的文件。"
            )
        
        # Try to open and parse the document
        try:
            doc = Document(file_path)
        except Exception as e:
            raise CorruptedDocumentError(
                f"文档损坏或无法解析: {str(e)}。请尝试重新导出文档。"
            )
        
        source_file = os.path.basename(file_path)
        root_nodes = self._build_tree(doc)
        
        return DocumentTree(source_file=source_file, root_nodes=root_nodes)
    
    def _build_tree(self, doc: Document) -> List[DocumentNode]:
        """Build document tree from Word document."""
        root_nodes: List[DocumentNode] = []
        # Stack to track parent nodes at each level
        # Index 0 is unused, 1-5 correspond to H1-H5
        level_stack: List[Optional[DocumentNode]] = [None] * 6
        current_content_parts: List[str] = []
        current_node: Optional[DocumentNode] = None
        
        for element in doc.element.body:
            # Check if element is a paragraph
            if element.tag.endswith('p'):
                para = Paragraph(element, doc)
                level = self._extract_heading_level(para)
                text = para.text.strip()
                
                if level != HeadingLevel.BODY:
                    # It's a heading - save accumulated content to current node
                    if current_node is not None and current_content_parts:
                        current_node.content = '\n\n'.join(current_content_parts)
                        current_content_parts = []
                    
                    # Create new node for this heading
                    new_node = DocumentNode(
                        id=str(uuid.uuid4()),
                        title=text,
                        content='',
                        level=level,
                        children=[]
                    )
                    
                    level_value = level.value
                    
                    # Find parent (nearest heading with lower level number)
                    parent = None
                    for i in range(level_value - 1, 0, -1):
                        if level_stack[i] is not None:
                            parent = level_stack[i]
                            break
                    
                    if parent is not None:
                        parent.children.append(new_node)
                    else:
                        root_nodes.append(new_node)
                    
                    # Update level stack
                    level_stack[level_value] = new_node
                    # Clear lower levels
                    for i in range(level_value + 1, 6):
                        level_stack[i] = None
                    
                    current_node = new_node
                else:
                    # It's body text - accumulate content
                    if text:
                        formatted_text = self._extract_formatted_text(para)
                        current_content_parts.append(formatted_text)
            
            # Check if element is a table
            elif element.tag.endswith('tbl'):
                table = Table(element, doc)
                markdown_table = self._convert_table_to_markdown(table)
                if markdown_table:
                    current_content_parts.append(markdown_table)
        
        # Save any remaining content
        if current_node is not None and current_content_parts:
            current_node.content = '\n\n'.join(current_content_parts)
        
        return root_nodes
    
    def _extract_heading_level(self, paragraph: Paragraph) -> HeadingLevel:
        """从段落样式中提取标题层级
        
        Args:
            paragraph: Word paragraph object
            
        Returns:
            HeadingLevel enum value
        """
        style_name = paragraph.style.name if paragraph.style else None
        
        if style_name in self.HEADING_STYLE_MAP:
            return self.HEADING_STYLE_MAP[style_name]
        
        # Also check for outline level in paragraph properties
        if paragraph._p.pPr is not None:
            outline_lvl = paragraph._p.pPr.find(
                '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}outlineLvl'
            )
            if outline_lvl is not None:
                level = int(outline_lvl.get(
                    '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val'
                ))
                if 0 <= level <= 4:
                    return HeadingLevel(level + 1)
        
        return HeadingLevel.BODY
    
    def _extract_formatted_text(self, paragraph: Paragraph) -> str:
        """Extract text with Markdown formatting (bold, italic)."""
        parts = []
        for run in paragraph.runs:
            text = run.text
            if not text:
                continue
            
            # Apply formatting
            if run.bold and run.italic:
                text = f"***{text}***"
            elif run.bold:
                text = f"**{text}**"
            elif run.italic:
                text = f"*{text}*"
            
            parts.append(text)
        
        return ''.join(parts)
    
    def _convert_table_to_markdown(self, table: Table) -> str:
        """将 Word 表格转换为 Markdown 格式
        
        Args:
            table: Word table object
            
        Returns:
            Markdown formatted table string
        """
        if not table.rows:
            return ''
        
        rows_data = []
        for row in table.rows:
            row_cells = []
            for cell in row.cells:
                # Get cell text, replace newlines with <br>
                cell_text = cell.text.strip().replace('\n', '<br>')
                # Escape pipe characters
                cell_text = cell_text.replace('|', '\\|')
                row_cells.append(cell_text)
            rows_data.append(row_cells)
        
        if not rows_data:
            return ''
        
        # Build Markdown table
        lines = []
        
        # Header row
        header = '| ' + ' | '.join(rows_data[0]) + ' |'
        lines.append(header)
        
        # Separator row
        separator = '| ' + ' | '.join(['---'] * len(rows_data[0])) + ' |'
        lines.append(separator)
        
        # Data rows
        for row in rows_data[1:]:
            # Pad row if needed
            while len(row) < len(rows_data[0]):
                row.append('')
            line = '| ' + ' | '.join(row) + ' |'
            lines.append(line)
        
        return '\n'.join(lines)
