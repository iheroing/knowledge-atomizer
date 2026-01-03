"""Anki Flashcard Exporter for knowledge atoms."""

import csv
import io
import os
import tempfile
from typing import List

from ..models import KnowledgeAtom, ExportResult
from .base import BaseExporter


class AnkiExporter(BaseExporter):
    """Anki 闪卡导出器 - 生成可导入 Anki 的 TSV 文件
    
    生成格式：
    - 正面：标题 + 知识路径
    - 背面：内容
    - 标签：层级标签 + 来源标签
    """
    
    def export(self, atoms: List[KnowledgeAtom], output_path: str = None) -> ExportResult:
        """生成 Anki 导入格式的 TSV 文件
        
        Args:
            atoms: List of KnowledgeAtom objects to export
            output_path: Optional output file path
            
        Returns:
            ExportResult with success status and file path
        """
        if not atoms:
            return ExportResult(
                success=True,
                message="没有知识原子需要导出",
                exported_count=0,
                file_path=None
            )
        
        try:
            # Filter atoms with content (no point in flashcards without content)
            atoms_with_content = [a for a in atoms if a.content and a.content.strip()]
            
            if not atoms_with_content:
                return ExportResult(
                    success=True,
                    message="没有包含内容的知识原子可导出为闪卡",
                    exported_count=0,
                    file_path=None
                )
            
            # Generate TSV content
            tsv_content = self._generate_tsv(atoms_with_content)
            
            # Determine output path
            if output_path is None:
                fd, output_path = tempfile.mkstemp(suffix='.txt')
                os.close(fd)
            
            # Write file (Anki uses UTF-8 without BOM)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(tsv_content)
            
            return ExportResult(
                success=True,
                message=f"成功导出 {len(atoms_with_content)} 张闪卡到 Anki 格式",
                exported_count=len(atoms_with_content),
                file_path=output_path
            )
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"Anki 导出失败: {str(e)}",
                exported_count=0,
                file_path=None
            )
    
    def _generate_tsv(self, atoms: List[KnowledgeAtom]) -> str:
        """Generate Anki-compatible TSV content.
        
        Format: Front<TAB>Back<TAB>Tags
        
        Args:
            atoms: List of KnowledgeAtom objects with content
            
        Returns:
            TSV content string
        """
        lines = []
        
        for atom in atoms:
            # Front: Title with path context
            front = self._generate_front(atom)
            
            # Back: Content (clean up for display)
            back = self._clean_content(atom.content)
            
            # Tags: Level and source tags
            tags = self._generate_tags(atom)
            
            # Escape tabs and newlines for TSV
            front = self._escape_field(front)
            back = self._escape_field(back)
            
            lines.append(f"{front}\t{back}\t{tags}")
        
        return '\n'.join(lines)
    
    def _generate_front(self, atom: KnowledgeAtom) -> str:
        """Generate flashcard front (question side).
        
        Args:
            atom: KnowledgeAtom
            
        Returns:
            Front text with title and context
        """
        parts = []
        
        # Add path context if available
        if atom.path and '>' in atom.path:
            # Show parent context
            path_parts = atom.path.split('>')
            if len(path_parts) > 1:
                context = ' > '.join(p.strip() for p in path_parts[:-1])
                parts.append(f"<small>📍 {context}</small><br><br>")
        
        # Main title as question
        parts.append(f"<b>{atom.title}</b>")
        
        return ''.join(parts)
    
    def _clean_content(self, content: str) -> str:
        """Clean content for Anki display.
        
        Args:
            content: Raw content
            
        Returns:
            Cleaned content with HTML formatting
        """
        if not content:
            return ""
        
        # Convert markdown-style formatting to HTML
        text = content.strip()
        
        # Convert **bold** to <b>bold</b>
        import re
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        
        # Convert *italic* to <i>italic</i>
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        
        # Convert newlines to <br>
        text = text.replace('\n\n', '<br><br>')
        text = text.replace('\n', '<br>')
        
        return text
    
    def _generate_tags(self, atom: KnowledgeAtom) -> str:
        """Generate Anki tags.
        
        Args:
            atom: KnowledgeAtom
            
        Returns:
            Space-separated tags string
        """
        tags = []
        
        # Level tag
        level_names = {1: '章节', 2: '小节', 3: '主题', 4: '概念', 5: '细节'}
        level_name = level_names.get(atom.level, f'L{atom.level}')
        tags.append(f"level::{level_name}")
        
        # Source tag (sanitize for Anki)
        if atom.source_file:
            source = atom.source_file.rsplit('.', 1)[0]
            source = source.replace(' ', '_').replace('/', '_')
            tags.append(f"source::{source}")
        
        # Knowledge atom marker
        tags.append("知识原子")
        
        return ' '.join(tags)
    
    def _escape_field(self, text: str) -> str:
        """Escape text for TSV format.
        
        Args:
            text: Raw text
            
        Returns:
            Escaped text safe for TSV
        """
        # Replace tabs with spaces
        text = text.replace('\t', '    ')
        return text
