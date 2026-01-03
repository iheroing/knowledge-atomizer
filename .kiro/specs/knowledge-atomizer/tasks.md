# Implementation Plan: Knowledge Atomizer

## Overview

本实现计划将 Knowledge Atomizer 分解为增量式的编码任务，从核心解析逻辑开始，逐步构建转换器、导出器，最后完成 Web 界面。每个任务都包含对应的测试子任务，确保代码质量。

## Tasks

- [x] 1. 项目初始化和基础结构
  - [x] 1.1 创建项目目录结构和配置文件
    - 创建 `src/`, `tests/`, `tests/unit/`, `tests/property/` 目录
    - 创建 `pyproject.toml` 配置 pytest 和 hypothesis
    - 创建 `requirements.txt` 包含依赖：python-docx, streamlit, requests, hypothesis, pytest
    - _Requirements: 项目基础设施_

  - [x] 1.2 定义核心数据模型
    - 创建 `src/models.py`
    - 实现 `HeadingLevel` 枚举
    - 实现 `DocumentNode` 和 `DocumentTree` 数据类
    - 实现 `KnowledgeAtom` 和 `ExportResult` 数据类
    - _Requirements: 2.2_

  - [x] 1.3 编写数据模型属性测试
    - **Property 6: Atom Field Completeness**
    - **Validates: Requirements 2.2**

- [x] 2. Document Parser 实现
  - [x] 2.1 实现 Word 文档解析核心逻辑
    - 创建 `src/parser.py`
    - 实现 `DocumentParser.parse()` 方法，读取 .docx 文件
    - 实现 `_extract_heading_level()` 从段落样式识别 H1-H5
    - 实现段落归属逻辑，将普通段落归属到最近的上级标题
    - _Requirements: 1.1, 1.2, 1.4, 1.6_

  - [x] 2.2 编写标题层级识别属性测试
    - **Property 1: Heading Level Recognition**
    - **Validates: Requirements 1.2**

  - [x] 2.3 编写段落归属属性测试
    - **Property 3: Paragraph Attribution**
    - **Validates: Requirements 1.4**

  - [x] 2.4 实现表格转 Markdown 功能
    - 实现 `_convert_table_to_markdown()` 方法
    - 处理合并单元格、空单元格等边界情况
    - _Requirements: 1.3_

  - [x] 2.5 编写表格转换属性测试
    - **Property 2: Table to Markdown Conversion**
    - **Validates: Requirements 1.3, 2.5**

  - [x] 2.6 实现文件格式验证和错误处理
    - 验证文件扩展名为 .docx
    - 处理文件不存在、损坏等异常情况
    - 返回明确的错误信息
    - _Requirements: 1.5_

  - [x] 2.7 编写无效文件拒绝属性测试
    - **Property 4: Invalid File Rejection**
    - **Validates: Requirements 1.5**

- [x] 3. Checkpoint - Parser 完成
  - 确保所有 Parser 测试通过，如有问题请询问用户

- [x] 4. Knowledge Transformer 实现
  - [x] 4.1 实现知识原子转换逻辑
    - 创建 `src/transformer.py`
    - 实现 `KnowledgeTransformer.transform()` 方法
    - 实现 `_flatten_tree()` 递归扁平化文档树
    - 为每个节点生成 UUID，建立 parent_id 关系
    - 保留格式信息（加粗、斜体转为 Markdown）
    - _Requirements: 2.1, 2.3, 2.4_

  - [x] 4.2 编写原子数量一致性属性测试
    - **Property 5: Atom Count Consistency**
    - **Validates: Requirements 2.1**

  - [x] 4.3 编写父子关系完整性属性测试
    - **Property 7: Parent-Child Relationship Integrity**
    - **Validates: Requirements 2.3**

- [x] 5. Checkpoint - Transformer 完成
  - 确保所有 Transformer 测试通过，如有问题请询问用户

- [x] 6. CSV Exporter 实现
  - [x] 6.1 实现 CSV 导出功能
    - 创建 `src/exporters/csv_exporter.py`
    - 实现 `CSVExporter.export()` 方法
    - 使用 UTF-8 with BOM 编码
    - 实现 `_escape_content()` 处理换行符和特殊字符
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 6.2 编写 CSV 往返一致性属性测试
    - **Property 11: CSV Round-Trip Consistency**
    - **Validates: Requirements 5.1, 5.3, 5.4**

  - [x] 6.3 编写 CSV UTF-8 BOM 编码属性测试
    - **Property 12: CSV UTF-8 BOM Encoding**
    - **Validates: Requirements 5.2**

- [x] 7. Obsidian Exporter 实现
  - [x] 7.1 实现 Obsidian Markdown 生成
    - 创建 `src/exporters/obsidian_exporter.py`
    - 实现 `_generate_frontmatter()` 生成 YAML front matter
    - 实现 `_generate_backlinks()` 生成双向链接
    - 实现 `_generate_markdown()` 组合完整文件内容
    - _Requirements: 4.2, 4.3, 4.4_

  - [x] 7.2 编写 Obsidian Frontmatter 有效性属性测试
    - **Property 9: Obsidian Frontmatter Validity**
    - **Validates: Requirements 4.2**

  - [x] 7.3 编写 Obsidian 双向链接属性测试
    - **Property 10: Obsidian Bidirectional Links**
    - **Validates: Requirements 4.3, 4.4**

  - [x] 7.4 实现 ZIP 打包功能
    - 实现 `export()` 方法，将所有 Markdown 文件打包为 ZIP
    - _Requirements: 4.1, 4.5_

  - [x] 7.5 编写 Obsidian 文件数量属性测试
    - **Property 8: Obsidian File Count**
    - **Validates: Requirements 4.1**

- [x] 8. Checkpoint - Exporters 完成
  - 确保所有 Exporter 测试通过，如有问题请询问用户

- [x] 9. Lark Exporter 实现
  - [x] 9.1 实现飞书 API 客户端
    - 创建 `src/exporters/lark_exporter.py`
    - 实现 `LarkClient.get_access_token()` 获取 tenant_access_token
    - 实现 `LarkClient.batch_create_records()` 批量创建记录
    - 实现自动重试逻辑（最多 3 次）
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 9.2 实现飞书导出器
    - 实现 `LarkExporter.export()` 方法
    - 实现 `_convert_to_lark_record()` 字段映射
    - 实现权限错误的友好提示
    - _Requirements: 3.4, 3.5_

  - [x] 9.3 编写飞书重试逻辑单元测试
    - 使用 mock 模拟网络错误
    - 验证重试次数不超过 3 次
    - _Requirements: 3.3_

- [x] 10. Statistics 实现
  - [x] 10.1 实现统计计算功能
    - 创建 `src/statistics.py`
    - 实现 `compute_statistics()` 计算总数和各层级数量
    - _Requirements: 7.3_

  - [x] 10.2 编写统计一致性属性测试
    - **Property 13: Statistics Count Consistency**
    - **Validates: Requirements 7.3**

- [x] 11. Streamlit Web UI 实现
  - [x] 11.1 实现主应用框架
    - 创建 `src/app.py`
    - 实现 `KnowledgeAtomizerApp.run()` 主入口
    - 配置页面标题和布局
    - 实现中文界面
    - _Requirements: 6.1, 6.6_

  - [x] 11.2 实现文件上传和解析预览
    - 实现 `_render_upload_section()` 文件上传区域
    - 实现 `_render_preview_section()` 树形结构预览
    - 显示解析进度和统计信息
    - _Requirements: 6.2, 7.1, 7.2, 7.3_

  - [x] 11.3 实现导出功能界面
    - 实现 `_render_export_section()` 导出选项
    - 实现飞书 API 配置表单
    - 实现下载按钮（CSV、Obsidian ZIP）
    - _Requirements: 6.3, 6.4_

  - [x] 11.4 实现错误处理和用户提示
    - 捕获所有异常，显示用户友好的错误信息
    - 隐藏技术堆栈信息
    - _Requirements: 6.5_

- [x] 12. Final Checkpoint - 全部完成
  - 确保所有测试通过
  - 运行 `streamlit run src/app.py` 验证 Web 界面
  - 如有问题请询问用户

## Notes

- 所有任务均为必需，包括测试任务
- 每个任务都引用了具体的需求编号以便追溯
- Checkpoint 任务用于阶段性验证，确保增量开发的稳定性
- 属性测试验证通用正确性，单元测试验证具体边界情况
