# Requirements Document

## Introduction

Knowledge Atomizer（知识原子化中台）是一个 Python ETL 系统，用于将 Word 文档中的非结构化教研内容转换为结构化数据。系统支持输出到飞书多维表格和 Obsidian 本地知识库，为 AI 应用和知识图谱提供"原子燃料"。

## Glossary

- **Parser（解析器）**：基于 python-docx 和正则状态机的文档解析模块，负责识别文档层级结构
- **Knowledge_Atom（知识原子）**：从文档中提取的最小知识单元，包含标题、内容、层级等元数据
- **ETL_Pipeline（ETL管道）**：Extract-Transform-Load 数据处理流水线
- **Lark_Base（飞书多维表格）**：飞书云端数据库，作为云端数据出口
- **Obsidian_Vault（Obsidian知识库）**：本地 Markdown 文件集合，支持双向链接和知识图谱可视化
- **Heading_Level（标题层级）**：文档结构层级，支持 H1-H5 五级标题
- **Web_UI（Web界面）**：基于 Streamlit 的图形操作界面

## Requirements

### Requirement 1: Word 文档解析

**User Story:** As a 教研人员, I want to 上传 Word 文档并自动识别其层级结构, so that 我可以将非结构化内容转换为结构化数据。

#### Acceptance Criteria

1. WHEN 用户上传一个 .docx 文件 THEN THE Parser SHALL 成功读取文件内容
2. WHEN 文档包含标题样式（Heading 1-5）THEN THE Parser SHALL 正确识别并标记对应的层级（H1-H5）
3. WHEN 文档包含表格 THEN THE Parser SHALL 将表格转换为 Markdown 格式
4. WHEN 文档包含普通段落 THEN THE Parser SHALL 将其归属到最近的上级标题下
5. IF 上传的文件格式不是 .docx THEN THE Parser SHALL 返回明确的错误提示
6. WHEN 文档解析完成 THEN THE Parser SHALL 输出包含层级关系的结构化数据

### Requirement 2: 知识原子提取

**User Story:** As a 内容运营人员, I want to 将文档内容拆解为独立的知识原子, so that 每个知识点可以被独立检索和复用。

#### Acceptance Criteria

1. WHEN 文档解析完成 THEN THE ETL_Pipeline SHALL 为每个标题节点创建一个 Knowledge_Atom
2. THE Knowledge_Atom SHALL 包含以下字段：id、title、content、level、parent_id、source_file
3. WHEN 一个标题下有子标题 THEN THE ETL_Pipeline SHALL 建立父子关系（parent_id 指向父节点）
4. WHEN 提取知识原子 THEN THE ETL_Pipeline SHALL 保留原始文档中的格式信息（加粗、斜体、列表等）
5. WHEN 知识原子包含表格 THEN THE ETL_Pipeline SHALL 将表格内容作为 Markdown 存储在 content 字段中

### Requirement 3: 飞书多维表格导出

**User Story:** As a 团队管理者, I want to 将知识原子同步到飞书多维表格, so that 团队成员可以协作编辑并为 AI Agent 提供数据源。

#### Acceptance Criteria

1. WHEN 用户配置飞书 App ID 和 App Secret THEN THE Lark_Base SHALL 成功建立 API 连接
2. WHEN 用户选择导出到飞书 THEN THE ETL_Pipeline SHALL 将知识原子批量写入指定的多维表格
3. WHEN 写入飞书时发生网络错误 THEN THE ETL_Pipeline SHALL 自动重试最多 3 次
4. IF 飞书 API 返回权限错误 THEN THE ETL_Pipeline SHALL 显示明确的权限配置指引
5. WHEN 导出完成 THEN THE ETL_Pipeline SHALL 返回成功写入的记录数量

### Requirement 4: Obsidian 知识库导出

**User Story:** As a 个人学习者, I want to 将知识原子导出为 Obsidian 格式, so that 我可以在本地构建可视化知识图谱。

#### Acceptance Criteria

1. WHEN 用户选择导出到 Obsidian THEN THE ETL_Pipeline SHALL 为每个知识原子生成一个 Markdown 文件
2. THE Markdown 文件 SHALL 包含 YAML front matter（title、level、parent、source）
3. WHEN 知识原子有父节点 THEN THE ETL_Pipeline SHALL 在文件中添加双向链接 [[parent_title]]
4. WHEN 知识原子有子节点 THEN THE ETL_Pipeline SHALL 在文件末尾列出所有子节点链接
5. WHEN 导出完成 THEN THE ETL_Pipeline SHALL 将所有文件打包为 ZIP 供用户下载

### Requirement 5: CSV 格式导出

**User Story:** As a 数据分析师, I want to 将知识原子导出为 CSV 格式, so that 我可以在 Excel 或其他工具中进行进一步分析。

#### Acceptance Criteria

1. WHEN 用户选择导出为 CSV THEN THE ETL_Pipeline SHALL 生成包含所有知识原子的 CSV 文件
2. THE CSV 文件 SHALL 使用 UTF-8 编码并包含 BOM 以支持 Excel 正确显示中文
3. THE CSV 文件 SHALL 包含列：id、title、content、level、parent_id、parent_title、source_file
4. WHEN content 字段包含换行符 THEN THE ETL_Pipeline SHALL 正确转义以保持 CSV 格式完整性

### Requirement 6: Web 图形界面

**User Story:** As a 非技术用户, I want to 通过图形界面操作整个流程, so that 我无需编写代码即可完成知识原子化工作。

#### Acceptance Criteria

1. WHEN 用户访问 Web_UI THEN THE Web_UI SHALL 显示文件上传区域
2. WHEN 用户上传文件后 THEN THE Web_UI SHALL 显示解析进度和预览结果
3. THE Web_UI SHALL 提供导出格式选择（飞书/Obsidian/CSV）
4. WHEN 用户选择飞书导出 THEN THE Web_UI SHALL 显示 API 配置表单
5. WHEN 发生错误 THEN THE Web_UI SHALL 显示用户友好的错误信息而非技术堆栈
6. THE Web_UI SHALL 支持中文界面

### Requirement 7: 解析结果预览

**User Story:** As a 用户, I want to 在导出前预览解析结果, so that 我可以确认解析是否正确。

#### Acceptance Criteria

1. WHEN 文档解析完成 THEN THE Web_UI SHALL 以树形结构展示知识原子层级
2. WHEN 用户点击某个知识原子 THEN THE Web_UI SHALL 显示该原子的详细内容
3. THE Web_UI SHALL 显示解析统计信息（总原子数、各层级数量）
