# Cyber Louvre · 赛博朋克卢浮宫

**在线预览 / Live demo:** https://cyber-louvre.pages.dev

用 Blender（Python 脚本）建模的赛博朋克风格卢浮宫 3D 模型，附带基于 Three.js 的网页查看器（环绕 / 漫游模式）。
A cyberpunk-style Louvre 3D model built procedurally in Blender (Python scripts), with a Three.js web viewer (orbit / walk modes).

## 目录 / Layout

| 路径 Path | 说明 Description |
|---|---|
| `src/` | Blender 建模、贴图、导出、校验脚本 · Blender build / texture / export / verification scripts |
| `model.blend`, `model_section.blend` | Blender 源文件 · Blender source files |
| `model.glb` | 完整 glTF 导出 · Full glTF export |
| `web/preview.html` | 网页查看器（已内嵌压缩模型）· Web viewer (compressed model embedded) |
| `web/model_web.glb` | 网页用压缩模型（meshopt + WebP）· Web-optimized model |
| `tex/`, `ref/` | 贴图与参考图 · Textures and reference images |

## 重新生成网页 / Rebuild the web viewer

```bash
bash src/rebuild_web.sh   # model.blend -> model.glb -> web/model_web.glb -> web/preview.html
```

## 部署 / Deployment

推送到 `main` 后，GitHub Actions 会把 `web/` 打包到 `dist/`（`preview.html` 作为 `index.html`），并部署到 Cloudflare Pages。
Every push to `main` triggers GitHub Actions, which copies `web/` into `dist/` (`preview.html` served as `index.html`) and deploys to Cloudflare Pages.

需要的仓库 Secrets / Required repo secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.

未纳入版本库：备份目录（`src_before*`、`tex_before*`）、`*.blend1`、中间渲染图（`renders/`、`compare/`）。
Not tracked: backup dirs, `*.blend1`, intermediate renders (`renders/`, `compare/`).
