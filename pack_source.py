"""
pack_source.py  —  将 exe 中打包的项目源文件单独归档为 zip
运行方式：python pack_source.py
"""
import zipfile
from pathlib import Path

root = Path(__file__).parent
output = root / "dist" / "AIGI-Holmes-source-bundle.zip"
output.parent.mkdir(exist_ok=True)

# 对应 AIGI_Holmes.spec 中 extra_datas + Analysis 入口的所有项目文件
items = [
    "desktop_launcher.py",       # 入口脚本
    "pyi_rthook_cwd.py",         # PyInstaller 运行时钩子
    "backend",                   # 后端 Python 包
    "CLIP/clip",                 # CLIP 模块源码
    "finetuned_fake_real_resnet50.pth",  # AI 模型权重
    "templates",                 # Web 模板
    "static",                    # 静态资源
    "asset",                     # 图标 / 品牌资源
    ".env.example",              # 默认环境配置
    "models/clip",               # CLIP ViT-B/32 权重
]

with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
    for item in items:
        p = root / item
        if p.is_file():
            zf.write(p, item)
            print(f"  + {item}")
        elif p.is_dir():
            file_count = 0
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    arcname = f.relative_to(root).as_posix()
                    zf.write(f, arcname)
                    file_count += 1
            print(f"  + {item}/  ({file_count} 个文件)")
        else:
            print(f"  ! {item}  不存在，已跳过")

size_mb = output.stat().st_size / 1024 / 1024
print(f"\n完成: {output}")
print(f"大小: {size_mb:.1f} MB")
