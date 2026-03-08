# ETF管理系统 - 云服务器部署指南

## 概述
将本地 ETF_manager 项目部署到腾讯云轻量服务器，实现：
- 云端运行后端服务
- 定时自动爬取ETF净值
- 浏览器随时访问

---

## 服务器信息
- **IP**: 81.70.53.162
- **系统**: Ubuntu Server 24.04 LTS
- **配置**: 2核2G + 50G SSD

---

## 第一步：上传项目到服务器

### 1.1 本地操作 - 打包项目

在本地 PowerShell 中执行：

```powershell
# 进入项目目录
cd e:/LXY_learn/ETF_manager

# 打包项目（排除venv和node_modules）
Compress-Archive -Path "backend", "data", "frontend", "scripts", "config.py", "requirements.txt", "start.py" -DestinationPath "etf_manager.zip" -Force
```

### 1.2 上传文件到服务器

```powershell
# 上传压缩包（会提示输入密码）
scp etf_manager.zip ubuntu@81.70.53.162:/home/ubuntu/
```

### 1.3 服务器操作 - 解压

SSH登录服务器并解压：

```bash
ssh ubuntu@81.70.53.162

# 解压
unzip -q etf_manager.zip -d ETF_manager

# 进入项目目录
cd ETF_manager

# 创建必要目录
mkdir -p log output
```

---

## 第二步：安装Python环境

### 2.1 安装系统依赖

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Python和工具
sudo apt install -y python3 python3-pip python3-venv python3-full
```

### 2.2 创建虚拟环境

```bash
cd /home/ubuntu/ETF_manager

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

---

## 第三步：初始化数据库

### 3.1 检查数据库文件

```bash
# 查看data目录
ls -la data/
```

如果已有 `etf_manager.db`，直接使用；
如果需要初始化：

```bash
# 初始化数据库（在项目目录下执行）
python scripts/init_db.py
```

### 3.2 测试脚本运行

```bash
# 测试获取净值（只获取已有持仓的基金）
python scripts/fetch_daily_quotes.py
```

看到类似输出说明成功：
```
==================================================
开始获取ETF净值 - 2024-01-15 21:30:00
==================================================
共 X 只基金需要更新
...
完成 - 成功: X, 跳过: X, 失败: X
```

---

## 第四步：配置定时任务

### 4.1 编辑crontab

```bash
# 编辑当前用户的定时任务
crontab -e

# 第一次会提示选择编辑器，选 nano (输入1)
```

### 4.2 添加定时任务

在文件末尾添加以下两行：

```cron
# ETF净值定时获取（工作日21:30执行）
30 21 * * 1-5 cd /home/ubuntu/ETF_manager && /home/ubuntu/ETF_manager/venv/bin/python scripts/fetch_daily_quotes.py >> log/cron.log 2>&1
```

保存：按 `Ctrl+O` → 回车 → `Ctrl+X`

### 4.3 验证定时任务

```bash
# 查看当前用户的定时任务
crontab -l

# 查看cron服务状态
sudo systemctl status cron
```

### 4.4 手动测试定时命令

复制crontab里的命令手动执行，确保无误：

```bash
cd /home/ubuntu/ETF_manager && /home/ubuntu/ETF_manager/venv/bin/python scripts/fetch_daily_quotes.py >> log/cron.log 2>&1

# 查看日志
cat log/cron.log
```

---

## 第五步：启动后端服务

### 5.1 直接启动（测试用）

```bash
cd /home/ubuntu/ETF_manager
source venv/bin/activate

# 启动服务
python start.py

# 或
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5.2 配置安全组放行端口

登录腾讯云控制台 → 轻量应用服务器 → 防火墙 → 添加规则：

| 协议 | 端口 | 策略 |
|-----|------|------|
| TCP | 8000 | 允许 |

### 5.3 使用systemd后台运行（推荐）

创建服务文件：

```bash
sudo tee /etc/systemd/system/etf-manager.service << 'EOF'
[Unit]
Description=ETF Manager Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ETF_manager
Environment=PATH=/home/ubuntu/ETF_manager/venv/bin
ExecStart=/home/ubuntu/ETF_manager/venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

启动服务：

```bash
# 重新加载systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start etf-manager

# 设置开机自启
sudo systemctl enable etf-manager

# 查看状态
sudo systemctl status etf-manager

# 查看日志
sudo journalctl -u etf-manager -f
```

---

## 第六步：访问系统

浏览器访问：

```
http://81.70.53.162:8000
```

---

## 日常维护命令

### 查看日志
```bash
# 爬取脚本日志
tail -f /home/ubuntu/ETF_manager/log/fetch_quotes.log

# 定时任务日志
tail -f /home/ubuntu/ETF_manager/log/cron.log

# 后端服务日志
sudo journalctl -u etf-manager -f
```

### 手动触发爬取
```bash
cd /home/ubuntu/ETF_manager
source venv/bin/activate
python scripts/fetch_daily_quotes.py
```

### 获取某基金历史数据
```bash
python scripts/fetch_daily_quotes.py --history 159770 --days 60
```

### 重启服务
```bash
sudo systemctl restart etf-manager
```

### 更新代码后
```bash
cd /home/ubuntu/ETF_manager
source venv/bin/activate

# 如果有新依赖
pip install -r requirements.txt

# 重启服务
sudo systemctl restart etf-manager
```

---

## 常见问题

### Q1: 提示权限不足
```bash
# 给脚本执行权限
chmod +x scripts/*.py
```

### Q2: 数据库被锁定
```bash
# 查找并删除锁定文件
find . -name "*.db-journal" -delete
find . -name "*.db-wal" -delete
```

### Q3: 端口被占用
```bash
# 查看8000端口占用
sudo lsof -i :8000

# 结束进程
sudo kill -9 <PID>
```

### Q4: 定时任务没执行
```bash
# 检查cron日志
grep CRON /var/log/syslog

# 确保cron服务运行
sudo systemctl restart cron
```

---

## 文件结构（服务器上）

```
/home/ubuntu/ETF_manager/
├── venv/                   # Python虚拟环境
├── backend/                # 后端代码
├── data/
│   └── etf_manager.db     # SQLite数据库
├── frontend/              # 前端代码
├── scripts/               # 工具脚本
│   └── fetch_daily_quotes.py
├── log/                   # 日志目录
│   ├── fetch_quotes.log
│   └── cron.log
├── config.py
├── requirements.txt
└── start.py
```

---

## 部署完成检查清单

- [ ] 项目上传到 `/home/ubuntu/ETF_manager`
- [ ] Python虚拟环境创建并激活
- [ ] 依赖安装完成
- [ ] 数据库文件就位
- [ ] 手动执行脚本成功
- [ ] 定时任务配置完成
- [ ] crontab中能看到任务
- [ ] 后端服务能启动
- [ ] 安全组放行8000端口
- [ ] 浏览器能访问
- [ ] 服务设置了开机自启

---

*部署日期: 2024年*
