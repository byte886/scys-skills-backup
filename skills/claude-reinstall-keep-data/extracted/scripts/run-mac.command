#!/bin/zsh
# macOS 双击入口：在「终端」中运行卸载重装脚本
cd "$(dirname "$0")"
if ! command -v node >/dev/null 2>&1; then
  echo "未找到 node，请先安装 Node.js（https://nodejs.org）后重试。"
  read -k 1 "?按任意键退出"
  exit 1
fi
node ./claude-reinstall.mjs "$@"
echo
read -k 1 "?按任意键关闭窗口"
