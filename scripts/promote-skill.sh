#!/usr/bin/env bash
# promote-skill — bootstrap a skill from tech-product-template into this marketplace.
#
# Cria:
#   - plugins/<name>/upstream/                  (copia inicial da skill)
#   - plugins/<name>/.claude-plugin/plugin.json (wrapper)
#   - plugins/<name>/README.md                  (atribuição + versionamento)
#   - plugins/<name>/CHANGELOG.md               (entrada inicial)
#   - .github/workflows/sync-<name>.yml         (trigger que chama o reusable workflow)
#
# Não toca em marketplace.json — imprime entrada sugerida para você colar.
# Não comita nem pusha — você revisa antes.
#
# Uso:
#   scripts/promote-skill.sh <skill-name> [--from <path-to-template-root>]
#
# Exemplo:
#   scripts/promote-skill.sh generate-session-prompt
#   scripts/promote-skill.sh organize-commits --from ~/Documents/tech_projects/tech-product-template

set -euo pipefail

# ───── Argumentos ───────────────────────────────────────────────────────
SKILL_NAME="${1:-}"
TEMPLATE_ROOT_DEFAULT="$HOME/Documents/tech_projects/tech-product-template"
TEMPLATE_ROOT="$TEMPLATE_ROOT_DEFAULT"

if [ -z "$SKILL_NAME" ] || [[ "$SKILL_NAME" == --* ]]; then
  echo "Uso: $0 <skill-name> [--from <path-to-template-root>]" >&2
  exit 2
fi
shift
while [ $# -gt 0 ]; do
  case "$1" in
    --from)
      TEMPLATE_ROOT="$2"
      shift 2
      ;;
    *)
      echo "Argumento desconhecido: $1" >&2
      exit 2
      ;;
  esac
done

# ───── Caminhos derivados ───────────────────────────────────────────────
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SKILL_SRC="$TEMPLATE_ROOT/.claude/skills/$SKILL_NAME"
PLUGIN_DIR="$REPO_ROOT/plugins/$SKILL_NAME"
WORKFLOW_FILE="$REPO_ROOT/.github/workflows/sync-$SKILL_NAME.yml"

# ───── Validações ───────────────────────────────────────────────────────
if [ ! -d "$TEMPLATE_ROOT" ]; then
  echo "❌ Template root não encontrado: $TEMPLATE_ROOT" >&2
  echo "   Use --from para apontar outro caminho." >&2
  exit 1
fi
if [ ! -d "$SKILL_SRC" ]; then
  echo "❌ Skill não encontrada: $SKILL_SRC" >&2
  echo "   Skills disponíveis no template:" >&2
  ls -1 "$TEMPLATE_ROOT/.claude/skills/" 2>/dev/null | sed 's/^/     /' >&2
  exit 1
fi
if [ ! -f "$SKILL_SRC/SKILL.md" ]; then
  echo "❌ $SKILL_SRC não tem SKILL.md (não é uma skill válida)." >&2
  exit 1
fi
if [ -d "$PLUGIN_DIR" ]; then
  echo "❌ Plugin já existe: $PLUGIN_DIR" >&2
  echo "   Para re-sync, deixe o GitHub Action rodar (ou use 'gh workflow run')." >&2
  exit 1
fi

# ───── Extrair metadata da SKILL.md upstream ────────────────────────────
UPSTREAM_VERSION=$(awk '/^---/{f=!f; next} f && /^version:/{print $2; exit}' "$SKILL_SRC/SKILL.md")
UPSTREAM_VERSION="${UPSTREAM_VERSION:-0.1.0}"

UPSTREAM_DESC=$(awk '/^---/{f=!f; next} f && /^description:/{sub(/^description:[ ]*/, ""); print; exit}' "$SKILL_SRC/SKILL.md")
UPSTREAM_DESC="${UPSTREAM_DESC:-Skill promovida do tech-product-template.}"

# SHA atual do template (se for git repo)
UPSTREAM_SHA="(unknown)"
if (cd "$TEMPLATE_ROOT" && git rev-parse HEAD >/dev/null 2>&1); then
  UPSTREAM_SHA=$(cd "$TEMPLATE_ROOT" && git rev-parse --short HEAD)
fi

WRAPPER_VERSION="1.0.0+upstream-${UPSTREAM_VERSION}"
TODAY=$(date +%Y-%m-%d)

echo "→ Skill: $SKILL_NAME"
echo "  Source:           $SKILL_SRC"
echo "  Destino plugin:   $PLUGIN_DIR"
echo "  Workflow:         $WORKFLOW_FILE"
echo "  Versão upstream:  $UPSTREAM_VERSION (SHA $UPSTREAM_SHA)"
echo "  Versão wrapper:   $WRAPPER_VERSION"
echo

# ───── Copiar conteúdo da skill ─────────────────────────────────────────
mkdir -p "$PLUGIN_DIR/upstream" "$PLUGIN_DIR/.claude-plugin"
rsync -a --exclude='.git' "$SKILL_SRC/" "$PLUGIN_DIR/upstream/"
echo "✓ Conteúdo copiado para $PLUGIN_DIR/upstream/"

# ───── plugin.json ──────────────────────────────────────────────────────
jq -n \
  --arg name "$SKILL_NAME" \
  --arg version "$WRAPPER_VERSION" \
  --arg desc "$UPSTREAM_DESC Vendored from fernando-bertholdo/tech-product-template." \
  '{
    name: $name,
    version: $version,
    description: $desc,
    author: { name: "Fernando Bertholdo" },
    license: "MIT",
    skills: ["./upstream/"]
  }' > "$PLUGIN_DIR/.claude-plugin/plugin.json"
echo "✓ plugin.json criado ($WRAPPER_VERSION)"

# ───── README.md do wrapper ─────────────────────────────────────────────
cat > "$PLUGIN_DIR/README.md" <<EOF
# $SKILL_NAME (vendored)

Wrapper de plugin Claude Code que vendoriza a skill \`$SKILL_NAME\` do repositório
[\`fernando-bertholdo/tech-product-template\`](https://github.com/fernando-bertholdo/tech-product-template)
e a distribui via este marketplace.

## Origem

- **Upstream:** \`tech-product-template/.claude/skills/$SKILL_NAME/\`
- **Snapshot inicial:** upstream \`v$UPSTREAM_VERSION\` (SHA \`$UPSTREAM_SHA\`)
- **Licença upstream:** MIT (preservada em \`upstream/\` se aplicável)

O conteúdo da skill vive em \`upstream/\` e é puxado via sparse-checkout pelo
workflow \`.github/workflows/sync-$SKILL_NAME.yml\`. Não edite arquivos em
\`upstream/\` por capricho — qualquer alteração ali é considerada um **patch
local** e deve seguir as regras abaixo.

## Versionamento

Formato: \`MAJOR.MINOR.PATCH+upstream-X.Y.Z\` (semver puro do wrapper +
build metadata identificando o snapshot do upstream vendorizado).

Veja \`/CLAUDE.md\` na raiz do marketplace para a tabela completa de bumps.

## Patches locais

Edite arquivos em \`upstream/\` diretamente, sempre delimitando o bloco com
sentinelas:

\`\`\`markdown
<!-- LOCAL-PATCH:start id=identificador-curto -->
... seu conteúdo ...
<!-- LOCAL-PATCH:end id=identificador-curto -->
\`\`\`

Documente cada patch no \`CHANGELOG.md\` deste diretório.

## Sync com upstream

**Automático:** workflow \`.github/workflows/sync-$SKILL_NAME.yml\` roda
toda segunda-feira 09:00 UTC e abre PR se houver mudanças.

**Manual:**

\`\`\`bash
gh workflow run sync-$SKILL_NAME.yml
\`\`\`
EOF
echo "✓ README.md criado"

# ───── CHANGELOG.md do wrapper ──────────────────────────────────────────
cat > "$PLUGIN_DIR/CHANGELOG.md" <<EOF
# Changelog — $SKILL_NAME (wrapper)

Este changelog rastreia o **wrapper** deste plugin (nosso código + nossos
patches). O changelog do skill upstream vive em \`upstream/\` (se existir).

Formato: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) +
versionamento \`MAJOR.MINOR.PATCH+upstream-X.Y.Z\`.

## [$WRAPPER_VERSION] — $TODAY

### Added
- Vendor inicial de \`tech-product-template/.claude/skills/$SKILL_NAME/\`
  (upstream SHA \`$UPSTREAM_SHA\`, versão \`$UPSTREAM_VERSION\`).
- \`plugin.json\` declarando o skill em \`./upstream/\`.
- Workflow \`.github/workflows/sync-$SKILL_NAME.yml\` para sync automático
  semanal (delega ao reusable \`_sync-skill-from-template.yml\`).

### Notes
- Sem patches locais nesta versão — o conteúdo do skill é idêntico ao upstream.
EOF
echo "✓ CHANGELOG.md criado"

# ───── Trigger workflow ─────────────────────────────────────────────────
mkdir -p "$REPO_ROOT/.github/workflows"
cat > "$WORKFLOW_FILE" <<EOF
name: Sync $SKILL_NAME

# Trigger fininho — delega toda a lógica ao reusable workflow.
# Para outras skills, copie este arquivo, troque o skill_name e o cron.

on:
  schedule:
    - cron: '0 9 * * 1'      # toda segunda 09:00 UTC
  workflow_dispatch: {}      # botão "Run workflow" manual

jobs:
  sync:
    uses: ./.github/workflows/_sync-skill-from-template.yml
    with:
      skill_name: $SKILL_NAME
    secrets:
      UPSTREAM_TOKEN: \${{ secrets.UPSTREAM_TOKEN }}
EOF
echo "✓ Workflow trigger criado: $WORKFLOW_FILE"

# ───── Próximos passos ──────────────────────────────────────────────────
cat <<EOF

────────────────────────────────────────────────────────────
Bootstrap pronto. Próximos passos manuais:

1. Adicione esta entrada ao .claude-plugin/marketplace.json
   (e bumpe o "version" do marketplace):

    {
      "name": "$SKILL_NAME",
      "source": "./plugins/$SKILL_NAME",
      "description": $(jq -Rn --arg s "$UPSTREAM_DESC" '$s'),
      "version": "$WRAPPER_VERSION",
      "license": "MIT",
      "category": "productivity",
      "keywords": ["TODO"],
      "author": { "name": "Fernando Bertholdo" }
    }

2. Atualize o CHANGELOG.md raiz com a entrada da nova versão do marketplace.

3. Confirme que o secret UPSTREAM_TOKEN está configurado no repo:
     gh secret list
   Se não estiver, siga docs/promotion-runbook.md.

4. Revisar tudo, commitar, abrir PR:
     git checkout -b feat/$SKILL_NAME
     git add plugins/$SKILL_NAME/ .github/workflows/sync-$SKILL_NAME.yml \\
             .claude-plugin/marketplace.json CHANGELOG.md
     git commit -m "feat(marketplace): promote $SKILL_NAME from tech-product-template"
     git push -u origin feat/$SKILL_NAME
     gh pr create --fill

5. Após o merge, teste o workflow manualmente:
     gh workflow run sync-$SKILL_NAME.yml
     gh run watch
EOF
