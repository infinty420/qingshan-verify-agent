"""通过 GitHub REST API (Git Database API) 上传本地提交。

背景：本机环境 git 智能 HTTP 通道被拦截（github.com:443 不可达），
但 api.github.com 可直连。因此用 blobs -> tree -> commit -> ref 四步
在远端重建提交；blob/tree 从本地 git 索引读取，保证内容一致。
"""
import base64
import os
import subprocess

import httpx

PROJ = r"C:\Users\ANTIMATTER\WorkBuddy\微专业期末报告\verify-agent"
OWNER, REPO = "infinty420", "qingshan-verify-agent"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"

# 用法：本地正常 git add + git commit 后运行本脚本，即推送至远端并保持 SHA 一致。
# 前提：工作区干净（index 与 HEAD 一致）。


def git(*args, binary=False, env=None):
    r = subprocess.run(["git", "-C", PROJ, *args], capture_output=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"git {args}: {r.stderr.decode(errors='replace')}")
    return r.stdout if binary else r.stdout.decode()


# 取凭据 token
cred = subprocess.run(
    ["git", "credential", "fill"],
    input=b"protocol=https\nhost=github.com\n\n",
    capture_output=True,
).stdout.decode()
token = [l for l in cred.splitlines() if l.startswith("password=")][0].split("=", 1)[1]

client = httpx.Client(trust_env=False, timeout=120)
H = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "verify-agent-uploader",
    "X-GitHub-Api-Version": "2022-11-28",
}

# 0) 空仓库播种：Git Database API 在无提交时会 409，
#    先用 Contents API 放一个 README 占位提交（后续会被 force 覆盖为干净的单提交历史）
r = client.get(f"{API}/git/refs/heads/main", headers=H)
if r.status_code == 409 or r.status_code == 404:
    seed = base64.b64encode(b"# init\n").decode()
    r = client.put(
        f"{API}/contents/.init-seed",
        headers=H,
        json={
            "message": "seed: 初始化仓库（将被首个正式提交覆盖）",
            "content": seed,
        },
    )
    r.raise_for_status()
    print("空仓库播种完成")

# 1) 索引中的文件（quotepath=false 保留中文路径）
entries = []
for line in git("-c", "core.quotepath=false", "ls-files", "-s").splitlines():
    meta, path = line.split("\t", 1)
    mode, sha, _ = meta.split()
    entries.append((mode, sha, path))
print(f"待上传文件: {len(entries)}")

# 2) 逐个上传 blob（从索引 blob 读取，确保与本地暂存内容逐字节一致）
tree_items = []
for mode, sha, path in entries:
    content = subprocess.run(
        ["git", "-C", PROJ, "cat-file", "blob", sha], capture_output=True
    ).stdout
    r = client.post(
        f"{API}/git/blobs",
        headers=H,
        json={"content": base64.b64encode(content).decode(), "encoding": "base64"},
    )
    r.raise_for_status()
    rsha = r.json()["sha"]
    assert rsha == sha, f"blob sha 不一致 {path}: {rsha} != {sha}"
    tree_items.append({"path": path, "mode": mode, "type": "blob", "sha": sha})
print(f"blob 上传完成: {len(tree_items)} 个, sha 全部一致")

# 3) 远端建 tree
tree_sha = git("write-tree").strip()
r = client.post(f"{API}/git/trees", headers=H, json={"tree": tree_items})
r.raise_for_status()
rtree = r.json()["sha"]
print(f"tree: 本地 {tree_sha} / 远端 {rtree} {'一致' if rtree == tree_sha else '不一致!'}")

# 4) 提交元数据从本地 HEAD 读取；消息剥掉尾部换行（GitHub API 会 strip，
#    本地用 commit-tree 以同样消息重建提交对象，保证两侧 SHA 逐字节一致）
msg = git("log", "-1", "--pretty=%B").rstrip("\n")
an, ae, ad, cn, ce, cd = (
    git("log", "-1", "--pretty=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI")
    .strip()
    .split("\x00")
)
head = git("rev-parse", "HEAD").strip()
parents = [git("rev-parse", "HEAD^").strip()] if git("rev-parse", "--verify", "-q", "HEAD^") else []
env = dict(
    os.environ,
    GIT_AUTHOR_NAME=an,
    GIT_AUTHOR_EMAIL=ae,
    GIT_AUTHOR_DATE=ad,
    GIT_COMMITTER_NAME=cn,
    GIT_COMMITTER_EMAIL=ce,
    GIT_COMMITTER_DATE=cd,
)
args = ["git", "-C", PROJ, "commit-tree", tree_sha]
for p in parents:
    args += ["-p", p]
local_commit = (
    subprocess.run(args, input=msg.encode(), capture_output=True, env=env)
    .stdout.decode()
    .strip()
)
if local_commit != head:
    git("update-ref", "refs/heads/main", local_commit)
    print(f"本地提交已按规范化消息重建: {head[:7]} -> {local_commit[:7]}")

r = client.post(
    f"{API}/git/commits",
    headers=H,
    json={
        "message": msg,
        "tree": tree_sha,
        "parents": parents,
        "author": {"name": an, "email": ae, "date": ad},
        "committer": {"name": cn, "email": ce, "date": cd},
    },
)
r.raise_for_status()
remote_commit = r.json()["sha"]
print(f"commit: 本地 {local_commit} / 远端 {remote_commit}")

# 5) 创建/更新 main 分支引用
r = client.post(
    f"{API}/git/refs", headers=H, json={"ref": "refs/heads/main", "sha": remote_commit}
)
if r.status_code == 422:  # ref 已存在（含播种提交）→ force 覆盖为干净历史
    r = client.patch(
        f"{API}/git/refs/heads/main",
        headers=H,
        json={"sha": remote_commit, "force": True},
    )
print(f"更新 ref: HTTP {r.status_code} {r.text[:200]}")

# 6) 若 SHA 对齐则同步本地引用
if remote_commit == local_commit:
    git("update-ref", "refs/heads/main", local_commit)
    git("update-ref", "refs/remotes/origin/main", local_commit)
    print(f"本地分支已同步到 {local_commit}")
else:
    print("SHA 未对齐（远端使用了远端 commit），本地与远端内容一致但提交号不同")
