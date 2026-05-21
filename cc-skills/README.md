# cc-skills/

Claude Code (cc) 的 skill 文件，让同事在自己工作目录用 cc 时也能调用 deck 工具链。

## 安装

推荐用 symlink，这样以后 deck 里改 skill 立刻生效，不用每次都 cp：

```bash
mkdir -p ~/.claude/commands
ln -sf ~/Desktop/level-design-deck/cc-skills/*.md ~/.claude/commands/
```

如果不想用 symlink（比如想脱离 deck 单独留一份），可以 cp：

```bash
cp ~/Desktop/level-design-deck/cc-skills/*.md ~/.claude/commands/
```

注意 cp 之后改 deck 内 skill 不会自动同步，需要重新 cp。

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
rm ~/.claude/commands/design-deck.md ~/.claude/commands/fill-gamedoc.md ~/.claude/commands/fill-doc.md
```

（无论 symlink 还是 cp 都用 rm 删；symlink 删的是链接本体，不动 deck 内的原文件。）
