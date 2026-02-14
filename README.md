# iFlow Manager

跨平台自动化部署管理工具

## 功能特性

- 跨平台支持 (Windows / macOS / Linux)
- 自动化部署流程
- 配置文件管理
- 实时日志监控

## 平台支持

### Windows

**下载安装：**

1. 从 [Releases](https://github.com/your-repo/iflow-manager/releases) 页面下载 `iFlowManager-win64.exe`
2. 双击运行即可

**使用方式：**

```powershell
# 直接运行
.\iFlowManager-win64.exe

# 带参数运行
.\iFlowManager-win64.exe --config config.json
```

---

### macOS

**下载安装：**

1. 从 [Releases](https://github.com/your-repo/iflow-manager/releases) 页面下载 `iFlowManager-macos.zip`
2. 解压文件
3. 将 `iFlowManager.app` 拖入 Applications 文件夹

**使用方式：**

```bash
# 终端运行
open /Applications/iFlowManager.app

# 或者在终端中直接运行
/Applications/iFlowManager.app/Contents/MacOS/iFlowManager
```

**首次运行注意事项：**

> 首次运行时，系统可能会提示 "无法打开" 因为应用来自身份不明的开发者"。
> 解决方法：右键点击应用 -> 选择"打开" -> 在弹窗中再次点击"打开"

---

### Linux

**下载安装：**

1. 从 [Releases](https://github.com/your-repo/iflow-manager/releases) 页面下载 `iFlowManager-linux-x64.tar.gz`
2. 解压文件：

```bash
tar -xzvf iFlowManager-linux-x64.tar.gz
```

**使用方式：**

```bash
# 进入目录
cd iFlowManager

# 赋予执行权限
chmod +x iFlowManager

# 运行程序
./iFlowManager
```

---

## 从源码运行

### 环境要求

- Python 3.11+
- PyInstaller 6.0+

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/iflow-manager.git
cd iflow-manager

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行程序
python iflow_manager.py
```

### 构建可执行文件

```bash
# 使用 PyInstaller 构建
pyinstaller iFlowManager.spec
```

构建产物将位于 `dist/iFlowManager` 目录。

---

## 开发

### GitHub Actions 自动构建

本项目使用 GitHub Actions 进行跨平台自动构建。

**触发构建：**

1. **推送版本标签：**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **发布 Release：**
   - 前往 GitHub Releases 页面
   - 点击 "Draft a new release"
   - 填写版本号并发布

3. **手动触发：**
   - 前往 Actions 页面
   - 选择 "Build Release" workflow
   - 点击 "Run workflow"

---

## 许可证

MIT License
