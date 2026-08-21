# 在 Windows 安装 AEDT Student

只从 Ansys 官方学生页面下载 Ansys Electronics Desktop Student，并遵循当前安装程序和 clickwrap。AEDT Student 与基于 Workbench 的 Student 套件相互独立，HFSS/Maxwell 限制也可能随版本变化。

官方安装完成后：

```bash
python tools/bootstrap.py --extras dev,aedt
agentic-sim doctor
agentic-sim info electromagnetics electrostatic
agentic-sim run electromagnetics --case electrostatic --dry-run
```

不要使用未记录的传输绕过方式、修改可执行文件检查、改变许可证或启动任意 `ansysedt` 二进制。适配器只能使用已验证的官方安装。Student 版本缺少请求模式时应保留 `BLOCKED`。
