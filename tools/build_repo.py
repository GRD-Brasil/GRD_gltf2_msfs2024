#!/usr/bin/env python3
"""
build_repo.py - Build packages and generate static Blender Extension Repository.

This script:
1. Reads and validates `blender_manifest.toml`.
2. Packages the Blender 4.2+ Extension ZIP (flat root structure with bundled _addons_utils).
3. Packages the legacy Blender <4.2 ZIP (side-by-side folders).
4. Generates the official `index.json` (version "v1") for Blender remote repositories.
5. Generates a modern `index.html` page for GitHub Pages hosting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

# Python 3.11+ built-in tomllib with fallback
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


ROOT_DIR = Path(__file__).resolve().parent.parent
ADDON_DIR = ROOT_DIR / "io_scene_gltf2_msfs_2024"
UTILS_DIR = ROOT_DIR / "_addons_utils"
MANIFEST_PATH = ADDON_DIR / "blender_manifest.toml"


def parse_manifest_simple(text: str) -> dict:
    """Simple TOML parser fallback for manifest fields if tomllib isn't available."""
    data = {"permissions": {}, "license": [], "tags": []}
    current_section = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip()
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            # Simple string parsing
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("['") or val.startswith('["'):
                # List of strings
                items = re.findall(r'["\']([^"\']+)["\']', val)
                val = items
            if current_section:
                if current_section not in data:
                    data[current_section] = {}
                data[current_section][key] = val
            else:
                data[key] = val
    return data


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Manifest not found at {MANIFEST_PATH}")
    content = MANIFEST_PATH.read_text(encoding="utf-8")
    if tomllib is not None:
        return tomllib.loads(content)
    return parse_manifest_simple(content)


def sync_version(new_version: str):
    """Sync version in blender_manifest.toml and io_scene_gltf2_msfs_2024/__init__.py"""
    # Clean version string (e.g. 'v6.4.9' -> '6.4.9')
    ver_clean = new_version.lstrip("v").strip()
    parts = ver_clean.split(".")
    while len(parts) < 3:
        parts.append("0")
    major, minor, patch = parts[:3]

    print(f"[*] Syncing version across files: {ver_clean} ({major}.{minor}.{patch})")

    # 1. blender_manifest.toml
    manifest_text = MANIFEST_PATH.read_text(encoding="utf-8")
    updated_manifest = re.sub(
        r'version\s*=\s*"[^"]+"',
        f'version = "{ver_clean}"',
        manifest_text,
        count=1,
    )
    MANIFEST_PATH.write_text(updated_manifest, encoding="utf-8")

    # 2. __init__.py bl_info
    init_path = ADDON_DIR / "__init__.py"
    init_text = init_path.read_text(encoding="utf-8")
    updated_init = re.sub(
        r'"version":\s*\([0-9,\s]+\)',
        f'"version": ({major}, {minor}, {patch})',
        init_text,
        count=1,
    )
    init_path.write_text(updated_init, encoding="utf-8")


def should_exclude(file_path: Path) -> bool:
    """Check if a file or directory should be excluded from package archives."""
    parts = file_path.parts
    for p in parts:
        if p.startswith(".") or p == "__pycache__":
            return True
        if p.endswith((".pyc", ".pyo", ".gitattributes", ".gitignore")):
            return True
    return False


def build_extension_zip(output_path: Path, manifest: dict):
    """
    Build the Blender 4.2+ / 5.x extension package.
    In Blender 4.2+, blender_manifest.toml MUST be at the root of the ZIP.
    _addons_utils is bundled inside the root so the extension is completely self-contained.
    """
    print(f"[*] Building Blender Extension package: {output_path.name}")

    if output_path.exists():
        output_path.unlink()

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        # 1. Add all files from io_scene_gltf2_msfs_2024
        for root, dirs, files in os.walk(ADDON_DIR):
            root_path = Path(root)
            for f in files:
                file_path = root_path / f
                if should_exclude(file_path):
                    continue
                arcname = file_path.relative_to(ADDON_DIR).as_posix()
                zf.write(file_path, arcname)

        # 2. Bundle _addons_utils inside the extension root
        if UTILS_DIR.is_dir():
            for root, dirs, files in os.walk(UTILS_DIR):
                root_path = Path(root)
                for f in files:
                    file_path = root_path / f
                    if should_exclude(file_path):
                        continue
                    rel = file_path.relative_to(UTILS_DIR).as_posix()
                    arcname = f"_addons_utils/{rel}"
                    zf.write(file_path, arcname)


def build_legacy_zip(output_path: Path):
    """
    Build the legacy Blender 3.3-4.1 zip containing both folders side-by-side.
    """
    print(f"[*] Building Legacy Addon package: {output_path.name}")

    if output_path.exists():
        output_path.unlink()

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        # Add io_scene_gltf2_msfs_2024
        for root, dirs, files in os.walk(ADDON_DIR):
            root_path = Path(root)
            for f in files:
                file_path = root_path / f
                if should_exclude(file_path):
                    continue
                rel = file_path.relative_to(ROOT_DIR).as_posix()
                zf.write(file_path, rel)

        # Add _addons_utils
        if UTILS_DIR.is_dir():
            for root, dirs, files in os.walk(UTILS_DIR):
                root_path = Path(root)
                for f in files:
                    file_path = root_path / f
                    if should_exclude(file_path):
                        continue
                    rel = file_path.relative_to(ROOT_DIR).as_posix()
                    zf.write(file_path, rel)


def generate_index_json(output_dir: Path, ext_zip: Path, manifest: dict) -> Path:
    """Generate the official index.json required by Blender Extensions Repository."""
    zip_bytes = ext_zip.read_bytes()
    zip_size = len(zip_bytes)
    zip_hash = f"sha256:{hashlib.sha256(zip_bytes).hexdigest()}"

    ext_entry = {
        "schema_version": manifest.get("schema_version", "1.0.0"),
        "id": manifest.get("id", "io_scene_gltf2_msfs_2024"),
        "name": manifest.get("name", "Microsoft Flight Simulator 2024: glTF Extension"),
        "version": manifest.get("version", "6.4.9"),
        "tagline": manifest.get("tagline", "MSFS 2024 glTF Extension"),
        "maintainer": manifest.get("maintainer", "GRD-Brasil"),
        "type": manifest.get("type", "add-on"),
        "blender_version_min": manifest.get("blender_version_min", "4.2.0"),
        "license": manifest.get("license", ["SPDX:Apache-2.0"]),
        "website": manifest.get("website", "https://github.com/GRD-Brasil/GRD_gltf2_msfs2024"),
        "tags": manifest.get("tags", ["Import-Export"]),
        "archive_url": f"./{ext_zip.name}",
        "archive_size": zip_size,
        "archive_hash": zip_hash,
    }

    if "permissions" in manifest:
        ext_entry["permissions"] = manifest["permissions"]

    index_data = {
        "version": "v1",
        "blocklist": [],
        "data": [ext_entry],
    }

    index_path = output_dir / "index.json"
    index_path.write_text(json.dumps(index_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[*] Generated Blender Repository index: {index_path.name}")
    return index_path


def generate_index_html(output_dir: Path, ext_zip_name: str, legacy_zip_name: str, manifest: dict):
    """Generate a modern HTML landing page for GitHub Pages with instructions for Blender."""
    ver = manifest.get("version", "6.4.9")
    name = manifest.get("name", "MSFS 2024 glTF Extension")
    website = manifest.get("website", "https://github.com/GRD-Brasil/GRD_gltf2_msfs2024")
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} - Repositório de Extensões do Blender</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0d1117;
            --card-bg: rgba(22, 27, 34, 0.85);
            --border: #30363d;
            --text: #e6edf3;
            --text-muted: #8b949e;
            --primary: #2f81f7;
            --primary-hover: #58a6ff;
            --accent: #238636;
            --accent-hover: #2ea043;
            --code-bg: #161b22;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        body {{
            background: radial-gradient(circle at 50% 0%, #1a2233 0%, #0d1117 70%);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 800px;
            width: 100%;
        }}
        header {{
            text-align: center;
            margin-bottom: 35px;
        }}
        .badge {{
            display: inline-block;
            background: rgba(47, 129, 247, 0.15);
            color: var(--primary-hover);
            border: 1px solid rgba(47, 129, 247, 0.3);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        h1 {{
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1.25;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #ffffff 0%, #8b949e 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        p.subtitle {{
            color: var(--text-muted);
            font-size: 1.05rem;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 24px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            backdrop-filter: blur(12px);
        }}
        h2 {{
            font-size: 1.3rem;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .repo-url-box {{
            background: var(--code-bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 14px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 16px;
        }}
        .repo-url {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 0.95rem;
            color: #58a6ff;
            word-break: break-all;
        }}
        button.copy-btn {{
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
            white-space: nowrap;
        }}
        button.copy-btn:hover {{
            background: var(--primary-hover);
        }}
        ol.steps {{
            padding-left: 20px;
            color: var(--text);
            line-height: 1.8;
            font-size: 0.98rem;
        }}
        ol.steps li {{
            margin-bottom: 8px;
        }}
        .code-tag {{
            background: rgba(110, 118, 129, 0.4);
            padding: 2px 6px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-family: monospace;
        }}
        .downloads {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
            margin-top: 10px;
        }}
        @media (max-width: 600px) {{
            .downloads {{
                grid-template-columns: 1fr;
            }}
        }}
        .btn {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 16px;
            border-radius: 12px;
            text-decoration: none;
            font-weight: 600;
            transition: transform 0.15s, background 0.2s;
            border: 1px solid var(--border);
            text-align: center;
        }}
        .btn:hover {{
            transform: translateY(-2px);
        }}
        .btn-primary {{
            background: var(--accent);
            color: white;
            border-color: rgba(255,255,255,0.1);
        }}
        .btn-primary:hover {{
            background: var(--accent-hover);
        }}
        .btn-secondary {{
            background: #21262d;
            color: var(--text);
        }}
        .btn-secondary:hover {{
            background: #30363d;
        }}
        .btn-subtext {{
            font-size: 0.75rem;
            font-weight: 400;
            opacity: 0.8;
            margin-top: 4px;
        }}
        footer {{
            margin-top: auto;
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-muted);
            padding-top: 20px;
        }}
        footer a {{
            color: var(--primary-hover);
            text-decoration: none;
        }}
        footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <span class="badge">Blender 4.2+ &amp; 5.x Ready • v{ver}</span>
            <h1>{name}</h1>
            <p class="subtitle">Repositório Remoto Oficial para Instalação e Atualizações Automáticas no Blender</p>
        </header>

        <div class="card">
            <h2>🚀 Como Instalar com Conexão Automática no Blender</h2>
            <p style="color: var(--text-muted); margin-bottom: 14px; font-size: 0.95rem;">
                No Blender 4.2+, 4.5 e 5.x você pode conectar este repositório para baixar com 1 clique e receber avisos automáticos de novas versões:
            </p>
            
            <div class="repo-url-box">
                <span id="repoUrl" class="repo-url">https://grd-brasil.github.io/GRD_gltf2_msfs2024/</span>
                <button class="copy-btn" onclick="copyRepoUrl()">Copiar URL</button>
            </div>

            <ol class="steps">
                <li>Abra o Blender e vá em <span class="code-tag">Edit &gt; Preferences</span>.</li>
                <li>Clique na aba <span class="code-tag">Get Extensions</span>.</li>
                <li>Clique no menu suspenso no canto superior direito (ou ícone de engrenagem/seta) e selecione <span class="code-tag">Repositories</span>.</li>
                <li>Clique no botão <span class="code-tag">+</span> e escolha <span class="code-tag">Add Remote Repository</span>.</li>
                <li>Cole a URL copiada acima e confirme.</li>
                <li>Agora a extensão aparecerá na lista de extensões do Blender. Basta clicar em <strong>Install</strong>!</li>
                <li>Sempre que uma nova versão for publicada no GitHub, o Blender exibirá o botão <strong>Update</strong> automaticamente.</li>
            </ol>
        </div>

        <div class="card">
            <h2>💾 Download Manual (.ZIP)</h2>
            <p style="color: var(--text-muted); margin-bottom: 14px; font-size: 0.95rem;">
                Se preferir instalar manualmente a partir do arquivo compactado:
            </p>
            <div class="downloads">
                <a href="./{ext_zip_name}" class="btn btn-primary">
                    <span>Baixar Extensão (Blender 4.2+ / 5.x)</span>
                    <span class="btn-subtext">Arquivo .zip autocontido para Blender moderno</span>
                </a>
                <a href="./{legacy_zip_name}" class="btn btn-secondary">
                    <span>Baixar Legado (Blender 3.3 - 4.1)</span>
                    <span class="btn-subtext">Contém as duas pastas (io_scene + _addons_utils)</span>
                </a>
            </div>
        </div>

        <footer>
            <p>Mantido pela equipe <a href="{website}" target="_blank">GRD-Brasil</a> • Licença Apache-2.0</p>
        </footer>
    </div>

    <script>
        function copyRepoUrl() {{
            const urlText = document.getElementById('repoUrl').innerText;
            navigator.clipboard.writeText(urlText).then(() => {{
                const btn = document.querySelector('.copy-btn');
                const orig = btn.innerText;
                btn.innerText = 'Copiado! ✓';
                btn.style.background = '#238636';
                setTimeout(() => {{
                    btn.innerText = orig;
                    btn.style.background = '';
                }}, 2000);
            }});
        }}
    </script>
</body>
</html>
"""
    html_path = output_dir / "index.html"
    html_path.write_text(html_content, encoding="utf-8")
    print(f"[*] Generated Landing Page: {html_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Build MSFS 2024 glTF Blender Extension Repository")
    parser.add_argument("--output-dir", default=str(ROOT_DIR / "dist"), help="Output directory for build artifacts")
    parser.add_argument("--version", help="Override extension version (e.g. 6.4.9 or v6.4.9)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Version handling
    ver_override = args.version or os.getenv("GITHUB_REF_NAME")
    if ver_override and not ver_override.startswith("refs/"):
        sync_version(ver_override)

    manifest = load_manifest()
    ver = manifest.get("version", "6.4.9")
    ext_id = manifest.get("id", "io_scene_gltf2_msfs_2024")

    print(f"[*] Building {ext_id} v{ver}...")

    ext_zip_name = f"{ext_id}-{ver}.zip"
    legacy_zip_name = f"{ext_id}-legacy-{ver}.zip"

    ext_zip_path = output_dir / ext_zip_name
    legacy_zip_path = output_dir / legacy_zip_name

    # 1. Extension ZIP (Blender 4.2+)
    build_extension_zip(ext_zip_path, manifest)

    # 2. Legacy ZIP (Blender 3.x - 4.1)
    build_legacy_zip(legacy_zip_path)

    # 3. index.json
    generate_index_json(output_dir, ext_zip_path, manifest)

    # 4. index.html
    generate_index_html(output_dir, ext_zip_name, legacy_zip_name, manifest)

    print("\n[OK] Build completed successfully in:", output_dir)
    print(f"    - {ext_zip_name}")
    print(f"    - {legacy_zip_name}")
    print("    - index.json")
    print("    - index.html")


if __name__ == "__main__":
    main()
