#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用 .pkpass 构建器（免签壳）

输入：一个 .pkpass 骨架（含 pass.json + 6 张图片 + manifest.json）
输出：重算 manifest SHA-1 后的合法 .pkpass

这个脚本不关心业务字段，只做一件事：把你对 pass.json / 图片的修改，
重新打包并算出正确的 manifest。因为 .pkpass 本质是个 zip，而 manifest.json
里每个文件的 SHA-1 必须和实际内容对上，否则 iOS 直接拒收。

用法：
    # 改完 demo-template.pkpass 里的 pass.json 后：
    python build_pass.py demo-template.pkpass
    # 会原地重算 manifest，前后文件大小不变（仅哈希更新）

也可以直接当库用：
    from build_pass import rebuild
    rebuild("demo-template.pkpass")
"""
import hashlib, json, os, sys, zipfile

def rebuild(path):
    """重算 path 这个 .pkpass 的 manifest.json（就地更新），返回是否成功。"""
    assert path.endswith(".pkpass"), "输入必须是 .pkpass"
    tmp = path + ".tmp"
    manifest = {}
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n != "manifest.json"]
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
            for n in names:
                data = z.read(n)
                out.writestr(n, data)
                if n != "signature":        # signature 不参与 manifest 计算
                    manifest[n] = hashlib.sha1(data).hexdigest()
            out.writestr("manifest.json",
                         json.dumps(manifest, ensure_ascii=False).encode("utf-8"))
    os.replace(tmp, path)
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for p in sys.argv[1:]:
        rebuild(p)
        print("rebuilt:", p)
