"""CSV Exporter for knowledge atoms."""

import csv
import io
import os
import tempfile
from typing import List

from ..models import KnowledgeAtom, ExportResult
from .base import BaseExporter


class CSVExporter(BaseExporter):
    """CSV 导出器 - 生成 UTF-8 with BOM 编码的 CSV 文件"""
    
    # UTF-8 BOM bytes
    UTF8_BOM = b'\xef\xbb\xbf'
    
    # CSV column headers
    HEADERS = ['id', 'title', 'content', 'level', 'parent_id', 'parent_title', 'source_file', 'path']
    
    def export(self, atoms: List[KnowledgeAtom], output_path: str = None) -> ExportResult:
        """生成 UTF-8 with BOM 编码的 CSV 文件
        
        Args:
            atoms: List of KnowledgeAtom objects to export
            output_path: Optional output file path. If None, creates a temp file.
            
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
            # Generate CSV content
            csv_content = self._generate_csv_content(atoms)
            
            # Determine output path
            if output_path is None:
                fd, output_path = tempfile.mkstemp(suffix='.csv')
                os.close(fd)
            
            # Write with UTF-8 BOM
            with open(output_path, 'wb') as f:
                f.write(self.UTF8_BOM)
                f.write(csv_content.encode('utf-8'))
            
            return ExportResult(
                success=True,
                message=f"成功导出 {len(atoms)} 个知识原子到 CSV",
                exported_count=len(atoms),
                file_path=output_path
            )
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"CSV 导出失败: {str(e)}",
                exported_count=0,
                file_path=None
            )
    
    def _generate_csv_content(self, atoms: List[KnowledgeAtom]) -> str:
        """Generate CSV content as string.
        
        Args:
            atoms: List of KnowledgeAtom objects
            
        Returns:
            CSV content as string
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        # Write header
        writer.writerow(self.HEADERS)
        
        # Write data rows
        for atom in atoms:
            row = [
                atom.id,
                atom.title,
                self._escape_content(atom.content),
                atom.level,
                atom.parent_id or '',
                atom.parent_title or '',
                atom.source_file,
                atom.path or ''
            ]
            writer.writerow(row)
        
        return output.getvalue()
    
    def _escape_content(self, content: str) -> str:
        """转义内容中的特殊字符
        
        CSV library handles most escaping, but we ensure newlines are preserved.
        
        Args:
            content: Original content string
            
        Returns:
            Escaped content string
        """
        if content is None:
            return ''
        return content
    
    @staticmethod
    def parse_csv(file_path: str) -> List[dict]:
        """Parse a CSV file back into records.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of dictionaries with CSV data
        """
        records = []
        
        with open(file_path, 'rb') as f:
            content = f.read()
            
            # Skip BOM if present
            if content.startswith(CSVExporter.UTF8_BOM):
                content = content[3:]
            
            # Decode and parse
            text = content.decode('utf-8')
            reader = csv.DictReader(io.StringIO(text))
            
            for row in reader:
                # Convert level back to int
                if 'level' in row:
                    row['level'] = int(row['level'])
                records.append(row)
        
        return records
