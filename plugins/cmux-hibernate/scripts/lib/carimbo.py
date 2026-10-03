"""Carimbos de tempo do snapshot.

Carimbo de maquina (`gerado_em`, nome do diretorio) e' UTC com `Z`. Snapshots
gravados ate' a 0.1.0 trazem a hora local do host, sem zona: a leitura aceita os
dois formatos e interpreta o antigo como hora local, que e' o que ele era.

Hora mostrada a gente vai no horario de Brasilia, com a zona escrita: hora sem
zona e' lida como local por quem a ve, e um carimbo UTC sem `Z` parece 3 horas
adiantado.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

try:
    from zoneinfo import ZoneInfo
    BRASILIA = ZoneInfo("America/Sao_Paulo")
except Exception:  # sem base de fusos no host; Brasilia e' UTC-3 sem horario de verao desde 2019
    BRASILIA = timezone(timedelta(hours=-3))

FORMATO_NOME = "%Y-%m-%dT%H-%M-%S"


def agora_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def nome_de_diretorio(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(FORMATO_NOME) + "Z"


def ler(carimbo: str) -> datetime:
    """Devolve datetime com zona. Sem zona = formato antigo, hora local do host."""
    texto = carimbo[:-1] + "+00:00" if carimbo.endswith("Z") else carimbo
    dt = datetime.fromisoformat(texto)
    return dt.astimezone() if dt.tzinfo is None else dt


def instante_do_nome(nome: str) -> Optional[datetime]:
    """Instante de um diretorio de snapshot, nos dois formatos; None se o nome e' alheio."""
    utc = nome.endswith("Z")
    try:
        dt = datetime.strptime(nome[:-1] if utc else nome, FORMATO_NOME)
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc) if utc else dt.astimezone()


def mais_recentes_primeiro(dirs: List[Path]) -> List[Path]:
    """Ordena pelo instante, nao pelo texto: nome em hora local e nome em UTC nao se
    comparam como string. Nome alheio vai para o fim, entre si em ordem de nome."""
    def chave(d: Path):
        dt = instante_do_nome(d.name)
        return (dt is not None, dt.timestamp() if dt else 0.0, d.name)
    return sorted(dirs, key=chave, reverse=True)


def mostrar(carimbo: str) -> str:
    return ler(carimbo).astimezone(BRASILIA).strftime("%d/%m/%Y %H:%M") + " BRT"
