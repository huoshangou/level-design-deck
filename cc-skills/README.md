# cc-skills/

Claude Code (cc) 的 skill 文件，让同事在自己工作目录用 cc 时也能调用 deck 工具链。

## 安装

```bash
mkdir -p ~/.claude/commands
cp ~/Desktop/level-design-deck/cc-skills/*.md ~/.claude/commands/
```

如果 deck 不在默认路径 `~/Desktop/level-design-deck`：

```bash
echo 'export LEVEL_DESIGN_DECK_HOME=/path/to/your/level-design-deck' >> ~/.zshrc
source ~/.zshrc
```

## 当前 skills

- **`/design-deck`** — spec 真源工作台。`new` / `add` / `check` / `render` / `open`
  - 详见 `design-deck.md`

## 用法

cc 启动后输入 `/design-deck help` 即可。

## 卸载

```bash
rm ~/.claude/commands/design-deck.md
```
