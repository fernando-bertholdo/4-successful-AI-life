#!/usr/bin/env bash
# Captura o estado real do ambiente para virar fixture de teste.
#
# A saida CRUA contem titulos e caminhos reais de trabalho e NAO deve ser
# commitada (esta no .gitignore). Rode sanitize.py logo em seguida para gerar
# as fixtures publicaveis.
#
# Uso: ./capture.sh   (com o cmux aberto e varias sessoes ativas)
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
CMUX="${CMUX_BUNDLED_CLI_PATH:-/Applications/cmux.app/Contents/Resources/bin/cmux}"

if [[ ! -x "$CMUX" ]]; then
    echo "cmux nao encontrado em $CMUX" >&2
    exit 1
fi

mkdir -p "$DIR/.raw"

CMUX_QUIET=1 "$CMUX" tree --all --id-format both > "$DIR/.raw/tree.txt"

# Uma linha por processo claude: "<pid> <command + environment>".
: > "$DIR/.raw/ps-eww.txt"
ps -A -ww -o pid=,command= | grep "/.local/bin/claude" | grep -v " daemon run" \
    | grep -v "grep " | while read -r pid _; do
    ps eww -o command= -p "$pid" | tr '\n' ' ' | sed "s|^|$pid |" >> "$DIR/.raw/ps-eww.txt"
    printf '\n' >> "$DIR/.raw/ps-eww.txt"
done

echo "cru capturado em .raw/ (nao versionado):"
echo "  tree.txt   : $(wc -l < "$DIR/.raw/tree.txt" | tr -d ' ') linhas"
echo "  ps-eww.txt : $(wc -l < "$DIR/.raw/ps-eww.txt" | tr -d ' ') processos"
echo
echo "Agora rode: python3 $DIR/sanitize.py"
