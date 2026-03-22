### 数据库设计
- ` SQL/mysql-design/ ` 目录下设计存放多份 MySQL 设计，设计文件的命名为 ` design-日期 `。
    - 日期最新的是最新的设计，之后平台 ` project ` 有关后端、数据库的一切动作都将严格按照最新的设计来。
        - 当前前后端代码中的一切设计都可忽略，当不存在，技术栈也有更换，将主要使用 Django
    - 设计以 ` .csv ` 文件呈现，数据表、字段名、数据类型、说明、约束等基本已规定。
        - 如果有未规定的，可以自行修改、添加等，但一定要在 ` SQL/mysql-design/mod/ ` 目录下生成 ` .md ` 格式文档对相关行为做出说明。
- ` SQL/sql/ ` 目录下存放对 MySQL 数据库的操作文件 ` .sql `。
    - 目录下暂时仅设计有两个文件 ` init.sql ` 和 ` operate.sql `。
    - ` init.sql ` 为数据库初始化文件，即建表文件，严格依据 ` SQL/mysql-design/ ` 的最新设计建表。
        - 如果有可以优化、需要修改的设计，一定要在 ` SQL/suggestions/ ` 目录下生成 ` .md ` 格式文档说明，由人类阅读文档、修改设计、上传设计后，再行修改。
    - ` operate.sql ` 为建表后各种可能的操作文件。
- ` SQL/scripts/ ` 目录下存放着处理 ` data/unclean/前4800家企业数据汇总.xlsx ` (人工获取的企业数据的)的 python 文件
    - python 文件必须完成以下任务：
        - ` data/unclean/前4800家企业数据汇总.xlsx ` 中的各种数据需要严格按照 ` SQL/mysql-design/ ` 中最新设计，通过 python 文件上传至 MySQL 的对应表中
    - ` SQL/data/ ` 目录下存放的是即将通过 python 文件 (` SQL/scripts/ `) 导入 MySQL 的各表的数据 (` .json ` 格式)
        - 每个表一个文件，文件命名为 ` 数据表名.json `
        - ` data/unclean/前4800家企业数据汇总.xlsx ` 中的数据仅囊括了设计中的部分字段，那么仅填充这部分字段即可，严格按照已有数据和数据库设计填充，不要虚构

### 下一步
1. 严格按照 ` SQL/mysql-design/design-2026-3-16.csv ` 生成 ` init.sql ` 文件
    - 确保 ` data/unclean/前4800家企业数据汇总.xlsx ` 中所有的字段数据可导入即可，与 xlsx 数据无关的字段可不用抠细节
2. 将 ` data/unclean/前4800家企业数据汇总.xlsx ` 解析成各表数据 (` .json `)，并生成可直接使用（导入 MySQL）的 python 脚本
3. 待前两步完成后，我们来再行后端重构

### 注意
- 项目要求在各个设备可简单快速部署
    - 在 ` SQL/ ` 目录下生成一个 README.md
    - 让团队成员只用几个 bash 即可快速部署协作
