# Microsoft Flight Simulator 2024: glTF Extension (Blender 5.x & 4.x Ready)

[![Release and Extension Repository](https://github.com/GRD-Brasil/GRD_gltf2_msfs2024/actions/workflows/release.yml/badge.svg)](https://github.com/GRD-Brasil/GRD_gltf2_msfs2024/actions/workflows/release.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE.md)

Este repositório contém o addon oficial do **MSFS 2024 SDK** (`io_scene_gltf2_msfs_2024`) com correções cirúrgicas para suporte integral às versões mais recentes do **Blender (5.0+, 5.2 LTS e 4.x)**, além de suporte nativo ao **novo sistema de Repositórios Remotos de Extensões do Blender**.

---

## ⚡ Conexão Direta e Atualizações Automáticas no Blender (Recomendado)

No **Blender 4.2+, 4.5 e Blender 5.x**, você não precisa baixar arquivos `.zip` manualmente toda vez que sair uma atualização. Basta conectar este repositório uma única vez:

### URL do Repositório:
```text
https://grd-brasil.github.io/GRD_gltf2_msfs2024/
```

### Passo a Passo:
1. Abra o Blender e acesse **Edit > Preferences** (Editar > Preferências).
2. Selecione a aba **Get Extensions** (Obter Extensões).
3. No canto superior direito da janela de preferências, clique no menu suspenso e selecione **Repositories** (Repositórios).
4. Clique no botão **`+`** e escolha **Add Remote Repository** (Adicionar Repositório Remoto).
5. Cole a URL acima: `https://grd-brasil.github.io/GRD_gltf2_msfs2024/` e confirme.
6. Volte à lista de extensões, pesquise por **Microsoft Flight Simulator 2024: glTF Extension** e clique em **Install**.
7. **Pronto!** Sempre que uma nova versão for publicada no GitHub, o Blender exibirá a notificação e um botão **Update** para atualizar com 1 clique.

---

## 📦 Instalação Manual Alternativa (.ZIP)

Caso prefira a instalação manual tradicional a partir da aba de [Releases](https://github.com/GRD-Brasil/GRD_gltf2_msfs2024/releases):

* **Para Blender 4.2+ e 5.x:**
  Baixe o arquivo `io_scene_gltf2_msfs_2024-<versao>.zip`. Ele é **autocontido** (já inclui a biblioteca `_addons_utils`).
  No Blender: *Preferences > Get Extensions > menu suspenso > Install from Disk...* e escolha o `.zip`.
* **Para Blender 3.3 a 4.1 (Legado):**
  Baixe o arquivo `io_scene_gltf2_msfs_2024-legacy-<versao>.zip`. Ele contém as duas pastas para descompactar em `%APPDATA%\Blender Foundation\Blender\<versao>\scripts\addons\`.

> [!IMPORTANT]
> Mantenha o addon do MSFS 2020 (`io_scene_gltf2_msfs`) desativado para evitar conflitos de hooks de exportação glTF.

---

## 🚀 Como Gerar Releases e Atualizações Automáticas

O repositório já está 100% configurado com **GitHub Actions** para compilar os pacotes, gerar o `index.json`, publicar o release e atualizar o repositório do Blender no GitHub Pages.

### 1. Ativação Única do GitHub Pages (Configurar no GitHub)
No GitHub do repositório (`GRD-Brasil/GRD_gltf2_msfs2024`):
1. Acesse a aba **Settings** > **Pages**.
2. Em **Build and deployment**:
   * **Source:** Selecione **GitHub Actions** (ou `Deploy from a branch` selecionando a branch `gh-pages` e pasta `/ (root)`).
3. Salve as alterações.

### 2. Publicando um Novo Release
Basta criar uma nova tag Git e enviar para o GitHub:
```bash
# Exemplo para lançar a versão 6.4.10:
git tag v6.4.10
git push origin v6.4.10
```

Ou acione manualmente via interface web:
1. Vá na aba **Actions** > **Release and Extension Repository**.
2. Clique em **Run workflow**.
3. Opcionalmente digite o número da versão (ex: `6.4.10`) e confirme.

O workflow irá automaticamente:
1. Sincronizar o número de versão no `blender_manifest.toml` e no `__init__.py`.
2. Empacotar o `.zip` da Extensão (Blender 4.2+/5.x) e o `.zip` Legado.
3. Calcular os hashes SHA-256 e gerar o arquivo `index.json` compatível com o Blender.
4. Criar o **GitHub Release** com as notas de versão e arquivos para download.
5. Fazer o deploy para o **GitHub Pages**, fazendo com que todos os usuários no Blender recebam a notificação de update imediatamente!

---

## 🛠️ Patches de Compatibilidade para Blender 5.x

1. **Draco Compression Import (`io/exp/export_settings.py`):**
   O Blender 5.0 moveu o módulo Draco de `io_scene_gltf2.io.com` para `io_scene_gltf2.io.exp`. O import condicional previne falhas de inicialização do addon.
2. **Material Inlining Hook (`io/exp/gltf_exporter_patches.py`):**
   O Blender 5.0 substitui instâncias de `bpy.types.Material` pelo wrapper interno `InlineShaderNodes`, que quebrava os hooks de materiais da Asobo com `'InlineShaderNodes' object has no attribute 'get'`. O inlining é desativado temporariamente enquanto o addon está registrado.
3. **Geometry Nodes Modifiers RNA API (`blender/utils/msfs_geometry_node_utils.py`):**
   O Blender 5.0 descontinuou o armazenamento de sockets de Geometry Nodes via ID properties (`modifier["Socket_1"]`). O acesso agora utiliza a nova API RNA de propriedades (`modifier.properties.inputs.<id>.value`), mantendo a integridade dos Gizmos (colisores e volumes de colisão).

---

## 📜 Licença

Distribuído sob a licença **Apache-2.0**. Consulte o arquivo [LICENSE.md](LICENSE.md) para obter mais informações.
