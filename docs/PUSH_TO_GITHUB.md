# 上传到 GitHub：逐步操作指南

> **本次交付的状态**：仓库所需文件已补齐，且**本地 `git init` + 首次 `commit` 已经完成**。
> 你只需要做 **第 1 步（网页建仓库）→ 第 2 步（生成令牌）→ 第 4 步（关联并推送）→ 第 5 步（验证）**。
> 第 3 步保留在这里作为参考，自己从头建仓库或换电脑时照做即可。

全程在 **Windows PowerShell** 里敲命令。路径含中文和空格，**双引号不能省**。

---

## 0. 先确认本地状态

```powershell
cd "C:\Users\15637\WorkBuddy\罗语卓的MacBook Air\2026秋大数据处理\大作业-完整版"
git status
git log --oneline -1
```

预期输出类似：

```
On branch main
nothing to commit, working tree clean
a1b2c3d  feat: MovieLens 推荐系统课程大作业完整代码与实验文档
```

看到 `nothing to commit, working tree clean` 说明本地已经干净地提交好了。

再确认大文件确实没被纳入版本管理：

```powershell
git ls-files | Select-String "bundle.tgz|\.whl|\.tgz"
git check-ignore -v bundle.tgz wheels/numpy-1.26.4-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

第一条应该**没有输出**；第二条应打印 `.gitignore` 里的对应规则。这两个检查能避免把 100 MB 的二进制推上去。

---

## 1. 在 GitHub 网页创建空仓库

1. 打开 <https://github.com>，登录（没有账号先注册，免费的 Public 仓库即可）。
2. 右上角 **+** → **New repository**。
3. 填写：
   - **Repository name**：`movielens-recommender`（建议这个英文名，PPT 里也好写）
   - **Description**：`基于 Hadoop/Spark MLlib ALS 的 MovieLens 电影推荐系统 | 课程大作业`
   - **Public** ✅（老师需要能直接打开链接，别选 Private）
   - **⚠️ 下面三项都不要勾选**：`Add a README file`、`Add .gitignore`、`Choose a license`。本地已经有这三个文件，勾了会导致推送冲突。
4. 点 **Create repository**。
5. 创建成功后页面上会显示一个地址，形如：

```
https://github.com/<你的GitHub用户名>/movielens-recommender.git
```

**把这个地址复制下来**，第 4 步要用。`<你的GitHub用户名>` 是个人主页地址里 `@` 后面那一段，不是昵称，也不是邮箱。

> 本地文件夹叫什么名字都行（中文、带空格都不影响），GitHub 仓库名才是链接里显示的那个。

---

## 2. 生成 Personal Access Token（推送用的"密码"）

GitHub 从 2021 年起**不允许用账号密码推送 HTTPS 仓库**，必须用令牌。

1. 打开 <https://github.com/settings/tokens>（或：右上角头像 → **Settings** → 左侧最底 **Developer settings** → **Personal access tokens** → **Tokens (classic)**）。
2. 点 **Generate new token** → **Generate new token (classic)**。
3. 填写：
   - **Note**：`bigdata-final`（随便写，方便以后认出用途）
   - **Expiration**：选 `90 days`（够交作业了；选 No expiration 也行但安全性差些）
   - **Select scopes**：勾选最上面的 **`repo`** 一整项即可，其它都不用勾。
4. 拉到最底点 **Generate token**。
5. 页面会显示一串 `ghp_` 开头的字符串，**立刻复制保存到记事本**。刷新页面后就再也看不到了（忘了只能重新生成一个）。

> 🔒 **安全**：这个令牌等同于推送权限，**绝对不要**写进 README、代码、截图或发给别人，也不要提交到仓库。作业 PPT 里只放仓库链接，不放令牌。

---

## 3. 【参考】本地初始化与首次提交

> 本次已代做，通常可跳过。只有在「换电脑 / 删了 .git / 想重来」时才需要。

```powershell
cd "C:\Users\15637\WorkBuddy\罗语卓的MacBook Air\2026秋大数据处理\大作业-完整版"

git init -b main

# 身份已在本机全局配置过（lyz4522），换电脑才需要重设：
# git config user.name "你的GitHub用户名"
# git config user.email "你的GitHub绑定邮箱"

git add .
git status --short          # 预览将被提交的文件，核对没有 .tgz / .whl / data/
git commit -m "feat: MovieLens 推荐系统课程大作业完整代码与实验文档"
```

`git status --short` 应该列出 `README.md`、`src/`、`results/`、`docs/` 等；**不该出现** `bundle.tgz`、`wheels/*.whl`、`results/*.tgz`。若出现了，先检查 `.gitignore` 是否在仓库根目录、文件名是不是 `.gitignore`（不是 `gitignore.txt`）。

---

## 4. 关联远程仓库并推送

```powershell
cd "C:\Users\15637\WorkBuddy\罗语卓的MacBook Air\2026秋大数据处理\大作业-完整版"

# 把地址换成第 1 步复制的那一串
git remote add origin https://github.com/<你的GitHub用户名>/movielens-recommender.git

git remote -v          # 核对地址有没有打错
git branch -M main     # 确保分支名是 main
git push -u origin main
```

**首次推送会弹出登录窗口**（Windows 凭据管理器或 Git Credential Manager）：

- **用户名**：GitHub 用户名
- **密码**：**粘贴第 2 步的 `ghp_...` 令牌**，不是 GitHub 账号密码

如果是命令行提示而不是弹窗，同样填用户名 + 令牌。成功后会保存在 Windows 凭据管理器里，以后 `git push` 不用再输。

预期输出：

```
Enumerating objects: 60, done.
Counting objects: 100% (60/60), done.
Writing objects: 100% (60/60), 9.42 MiB | 1.20 MiB/s, done.
To https://github.com/<用户名>/movielens-recommender.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
```

> 9 MB 左右是正常的（含 `similar_all.csv` 8 MB 与 7 张 PNG）。如果显示几十上百 MB，说明 `.gitignore` 没生效，**先停下来**回到第 0 步检查。

---

## 5. 验证并拿到交付链接

1. 浏览器打开 `https://github.com/<你的GitHub用户名>/movielens-recommender` 刷新。
2. 应看到 README 渲染出的项目介绍和两张统计图；点开 `src/`、`docs/`、`results/figures/` 确认文件都在。
3. 仓库链接就是 PPT「相关资源」页要填的地址：

```
源代码：https://github.com/<你的GitHub用户名>/movielens-recommender
```

（`README.md` 第 8 节已经写好了一整段可直接复制的内容，记得把占位符替换掉。）

---

## 6. 以后改了文件，怎么更新仓库

```powershell
cd "C:\Users\15637\WorkBuddy\罗语卓的MacBook Air\2026秋大数据处理\大作业-完整版"
git status                # 看看改了哪些
git add .
git commit -m "fix: 说明这次改了什么"
git push
```

---

## 7. 【选做】用 Release 附件提供大文件

`.gitignore` 排除了 `bundle.tgz`（53 MB）和 `wheels/*.whl`（55 MB），这是 Git 的正确用法，但老师 clone 后要自己下载 wheel。如果想让资源链接更完整，可以用 GitHub Release 附件（单文件上限 2 GB，不走 Git）：

1. 仓库页面右侧点 **Releases** → **Create a new release**。
2. **Choose a tag** 输入 `v1.0` → **Create new tag on publish**。
3. **Release title** 填 `课程大作业提交版 v1.0`。
4. 在 **Attach binaries by dropping them here** 区域拖入 `bundle.tgz`（本地已生成）。
5. 点 **Publish release**。

之后 PPT 可写：

```
离线脚本包：https://github.com/<用户名>/movielens-recommender/releases/tag/v1.0
```

> 不做这一步也完全可以交：README 与 `scripts/make_bundle.sh`、`scripts/fetch_wheels.py` 已说明如何从源码重建所有大文件，符合「资源链接可访问」的要求。

---

## 8. 报错速查

| 报错 | 原因 / 处理 |
|---|---|
| `fatal: not a git repository` | 没 `cd` 到 `大作业-完整版` 目录，或路径引号漏了 |
| `remote origin already exists` | 已经关联过。改地址用 `git remote set-url origin <新地址>`，不要重复 `add` |
| `Authentication failed for 'https://github.com/...'` | ① 密码栏要贴 **PAT** 不是账号密码；② 令牌过期或没勾 `repo`；③ 输错了被 Windows 记住 → 控制面板 → 凭据管理器 → Windows 凭据 → 删除 `git:https://github.com` 后重试 |
| `src refspec main does not match any` | 还没有任何 commit，回到第 3 步执行 `git add .` + `git commit` |
| `! [rejected] main -> main (fetch first)` | 建仓库时误勾了 README/.gitignore。执行 `git pull --rebase origin main` 再 `git push`；别用 `-f` 强推 |
| `Failed to connect to github.com port 443` | 网络问题。换个网络（手机热点）重试；若用代理，先 `git config --global http.proxy http://127.0.0.1:端口`（**别把代理地址提交进仓库**） |
| `GH001: Large files detected. You may want to try Git Large File Storage` | 有超过 100 MB 的文件被 add。先 `git rm --cached <文件>`，确认 `.gitignore` 规则后再提交 |
| `warning: LF will be replaced by CRLF` | 正常警告，`.gitattributes` 已保证仓库内是 LF，容器里能正常执行 |
| 推送成功但网页看不到 README | 刷新页面 / 确认推的是 `main` 分支 / 看仓库右上角分支下拉 |

### 不想敲命令：GitHub Desktop 图形界面

1. 下载安装 <https://desktop.github.com/>，用 GitHub 账号登录（OAuth 登录，**不用手动生成令牌**）。
2. **File → Add Local Repository…** → 选择 `大作业-完整版` 文件夹。
3. 左下角填提交说明 → **Commit to main** → 右上 **Publish repository**。
4. 名字填 `movielens-recommender`，取消勾选 *Keep this code private*，点 **Publish repository**。

命令行和图形界面**二选一**即可，不要两边同时操作。

---

## 8.1 隐私提醒：提交作者信息会公开

公开仓库的每次 commit 都会显示**作者名和邮箱**，它们来自本机的 Git 全局配置。可先查看：

```powershell
git config --global user.name
git config --global user.email
```

如果不想公开常用邮箱，推荐改用 GitHub 提供的 `noreply` 邮箱：

1. GitHub → **Settings** → **Emails**，找到形如 `12345678+<用户名>@users.noreply.github.com` 的地址（勾选了 *Keep my email addresses private* 就会有）。
2. 在**本仓库内**单独设置（不影响其它项目）：

```powershell
cd "C:\Users\15637\WorkBuddy\罗语卓的MacBook Air\2026秋大数据处理\大作业-完整版"
git config user.name "你的GitHub用户名"
git config user.email "12345678+你的GitHub用户名@users.noreply.github.com"
```

3. 如果已经 commit 但**还没 push**，重写这唯一一次提交的作者信息：

```powershell
git commit --amend --reset-author --no-edit
```

（只在尚未推送时这样做；已经推送过就别改历史了。）

其它不要放进公开仓库的内容：Personal Access Token、虚拟机 IP、SSH 私钥、课程平台账号密码。本仓库的 `.gitignore` 已排除数据卷与日志文件。

---

## 9. 最后检查清单

- [ ] 仓库是 **Public**，老师能直接打开
- [ ] README 首页能正常显示图片和表格
- [ ] `src/` 有 7 个脚本，`docs/` 有 3 个说明，`results/figures/` 有 7 张图
- [ ] `bundle.tgz` / `*.whl` / `data/` / `*.log` 没有出现在仓库里
- [ ] 令牌没有出现在任何文件、截图或 PPT 中
- [ ] PPT「相关资源」页已填入最终仓库链接
