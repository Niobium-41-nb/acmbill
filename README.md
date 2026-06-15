# ACM 报销材料管理系统

基于 Flask 的报销材料管理 Web 应用，支持用户注册/登录、项目管理、备案条目管理、文件上传与预览、多种格式导出等功能。

## 功能特性

### 用户系统
- 邮箱注册与登录（需邮箱验证码）
- 个人信息修改（真实姓名、学号、班级）
- 密码修改（需邮箱验证码）
- 管理员可编辑所有用户信息

### 项目管理
- 创建/编辑/删除报销项目
- 项目状态管理（待提交/审核中/已通过/已驳回）
- 团队管理（最多 3 名成员，含创建者）

### 备案条目管理
- 添加/编辑/删除备案条目
- 报账内容分类：报名费、住宿费、大交通费（机票、火车票）、小交通
- 大交通费支持填写：往/返、起点、终点、机票/车票
- 文件关联：除小交通外，其他类别必须关联发票与支付记录
- 文件预览（图片、PDF 等）

### 文件管理
- 上传发票、支付记录、辅助材料
- 文件预览（图片内联显示、PDF 使用 iframe）
- 文件删除
- 文件与具体备案条目关联

### 导出功能
- **Excel 导出**：格式化备案表，自动合并单元格
- **HTML 导出**：网页版备案表，适合打印
- **ZIP 导出**：包含备案表 + 发票/支付记录/辅助材料三个文件夹
  - 文件自动转换为 PNG 图片
  - 支付记录图片拼接为 A4 大小（N×M 网格排列）

### 管理功能
- 用户管理（查看/编辑/删除/切换角色）
- 项目管理（查看所有项目）
- 管理员可删除用户及其所有关联数据

## 技术栈

- **后端**：Flask + Flask-SQLAlchemy + Flask-Login
- **数据库**：MySQL（支持 SQLite 回退）
- **前端**：Bootstrap 5 + jQuery
- **模板引擎**：Jinja2
- **邮件**：SMTP（163 邮箱）
- **导出**：openpyxl（Excel）、zipfile（ZIP）、Pillow（图片处理）、PyMuPDF（PDF 转换）

## 快速开始

### 方式一：Docker 部署（推荐）

使用 Docker Compose 一键部署，自动创建 MySQL 数据库并启动应用。

#### 前置条件

安装 [Docker](https://docs.docker.com/get-docker/) 和 [Docker Compose](https://docs.docker.com/compose/install/)（Linux 或 macOS）。

#### 1. 克隆项目

```bash
git clone https://github.com/Niobium-41-nb/acmbill.git
cd acmbill
```

#### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，至少配置邮箱信息（用于发送验证码）
```

必填配置项（邮箱）：
```env
MAIL_USERNAME=your_email@qq.com
MAIL_PASSWORD=your_email_authorization_code
MAIL_DEFAULT_SENDER=your_email@qq.com
```

其他配置（可选）：
- `ADMIN_PASSWORD` - 管理员密码
- `DB_PASSWORD` - 数据库密码
- `SECRET_KEY` - 应用密钥

#### 3. 启动应用

```bash
# 构建并启动（后台运行）
docker compose up -d

# 查看日志
docker compose logs -f

# 停止应用
docker compose down

# 停止并删除数据卷（⚠️ 会清空数据库和上传文件）
docker compose down -v
```

应用启动后访问 `http://localhost:1444`。

#### 4. 常用 Docker 命令

```bash
# 查看运行状态
docker compose ps

# 重启应用（不重启数据库）
docker compose restart app

# 重新构建镜像（代码变更后需要）
docker compose build app
docker compose up -d

# 进入应用容器
docker compose exec app bash
```

### 方式二：本地开发（直接运行）

#### 1. 克隆项目

```bash
git clone https://github.com/Niobium-41-nb/acmbill.git
cd acmbill
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

#### 3. 配置环境变量

复制并编辑 `.env` 文件：

```env
# 邮箱配置（用于发送验证码）
MAIL_SERVER=smtp.163.com
MAIL_PORT=25
MAIL_USE_TLS=true
MAIL_USE_SSL=false
MAIL_USERNAME=your_email@163.com
MAIL_PASSWORD=your_email_password
MAIL_DEFAULT_SENDER=your_email@163.com

# 管理员账号
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@example.com

# 数据库配置（MySQL，留空则自动使用 SQLite）
DB_HOST=your_mysql_host
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_db_password
DB_NAME=acmbill
```

#### 4. 启动应用

```bash
# 方式一：直接启动
python app.py

# 方式二：使用启动脚本（后台运行）
./start.sh

# 停止应用
./stop.sh
```

应用默认运行在 `http://localhost:1444`。

## 项目结构

```
acmbill/
├── app.py                    # 应用入口
├── config.py                 # 配置文件
├── auth.py                   # 认证路由（登录/注册/个人信息）
├── project.py                # 项目路由（项目管理/条目/文件/导出）
├── models.py                 # 数据模型
├── requirements.txt          # Python 依赖
├── start.sh                  # 启动脚本
├── stop.sh                   # 停止脚本
├── .env                      # 环境变量配置
├── .gitignore                # Git 忽略规则
├── README.md                 # 项目说明
├── templates/                # Jinja2 模板
│   ├── base.html             # 基础模板
│   ├── login.html            # 登录页
│   ├── register.html         # 注册页
│   ├── dashboard.html        # 用户仪表盘
│   ├── profile.html          # 个人信息页
│   ├── project_detail.html   # 项目详情页
│   ├── project_form.html     # 项目创建/编辑页
│   ├── reimbursement_table.html  # HTML 导出模板
│   ├── admin_users.html      # 管理员用户管理
│   ├── admin_projects.html   # 管理员项目管理
│   └── admin_edit_user.html  # 管理员编辑用户
└── uploads/                  # 文件上传目录
```

## 数据模型

- **User** - 用户（用户名、邮箱、密码、真实姓名、学号、班级、角色）
- **EmailVerificationCode** - 邮箱验证码
- **Project** - 项目（名称、指导老师、比赛名称、比赛时间、状态）
- **TeamMember** - 团队成员
- **ReimbursementItem** - 备案条目（报账内容、金额、报账人、学号、班级、大交通详情）
- **ProjectFile** - 项目文件（发票、支付记录、辅助材料，可关联到具体条目）
