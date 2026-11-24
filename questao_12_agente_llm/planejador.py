# -*- coding: utf-8 -*-
"""
Planejador e verificador clássicos usados como ferramentas pelo agente.

O LLM não monta o horário sozinho: ele interpreta o pedido e chama estas
funções, que garantem as restrições e calculam a utilidade de forma explícita.

Utilidade de uma tarefa concluída = peso da prioridade x fator do prazo
  prioridade: alta = 10, media = 6, baixa = 2
  prazo:      hoje = 1,5; amanha = 1,2; outro = 1,0
Tarefa divisível concluída em parte vale a fração concluída (blocos de pelo menos 15 min).
"""

from itertools import permutations

PESO = {"alta": 10, "media": 6, "baixa": 2}
FATOR_PRAZO = {"hoje": 1.5, "amanha": 1.2}
BLOCO_MIN = 15


def hm(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def txt(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def utilidade(tarefa, minutos_feitos=None):
    feitos = tarefa["duracao_min"] if minutos_feitos is None else minutos_feitos
    frac = min(1.0, feitos / tarefa["duracao_min"])
    return PESO.get(tarefa["prioridade"], 2) * FATOR_PRAZO.get(tarefa["prazo"], 1.0) * frac


def _normalizar(tarefas):
    out = []
    for t in tarefas:
        t = dict(t)
        t.setdefault("prioridade", "media")
        t["prioridade"] = t["prioridade"].lower().replace("é", "e")
        t.setdefault("prazo", "outro")
        t["prazo"] = t["prazo"].lower().replace("ã", "a")
        t.setdefault("divisivel", False)
        t["duracao_min"] = int(t["duracao_min"])
        out.append(t)
    return out


def _livres(inicio, fim, ocupados):
    livres, cur = [], inicio
    for a, b in sorted(ocupados):
        if a > cur:
            livres.append([cur, a])
        cur = max(cur, b)
    if cur < fim:
        livres.append([cur, fim])
    return livres


def _empacotar(ordem, livres_iniciais, permitir_divisao):
    """Encaixa as tarefas na ordem dada, no primeiro horário livre possível."""
    livres = [list(x) for x in livres_iniciais]
    blocos, feitos = [], {}
    for t in ordem:
        if permitir_divisao and t["divisivel"]:
            falta = t["duracao_min"]
            for iv in livres:
                if falta <= 0:
                    break
                disp = iv[1] - iv[0]
                usa = min(disp, falta)
                if usa >= BLOCO_MIN or (usa == falta and usa > 0):
                    blocos.append((iv[0], iv[0] + usa, t["id"]))
                    iv[0] += usa
                    falta -= usa
            if falta < t["duracao_min"]:
                feitos[t["id"]] = t["duracao_min"] - falta
        else:
            for iv in livres:
                if iv[1] - iv[0] >= t["duracao_min"]:
                    blocos.append((iv[0], iv[0] + t["duracao_min"], t["id"]))
                    iv[0] += t["duracao_min"]
                    feitos[t["id"]] = t["duracao_min"]
                    break
    return blocos, feitos


def _melhor(flex, livres, permitir_divisao, por_id, obrigatoria=None):
    melhor = None
    for ordem in permutations(flex):
        blocos, feitos = _empacotar(ordem, livres, permitir_divisao)
        if obrigatoria and obrigatoria not in feitos:
            continue
        u = sum(utilidade(por_id[i], m) for i, m in feitos.items())
        # desempate: terminar cedo as tarefas mais importantes
        custo_tempo = sum(PESO[por_id[i]["prioridade"]] * b for a, b, i in blocos)
        chave = (round(u, 6), -custo_tempo)
        if melhor is None or chave > melhor[0]:
            melhor = (chave, blocos, feitos)
    return melhor


def planejar(tarefas, inicio="14:00", fim="18:00", permitir_divisao=False):
    tarefas = _normalizar(tarefas)
    por_id = {t["id"]: t for t in tarefas}
    ini, fi = hm(inicio), hm(fim)
    fixas = [t for t in tarefas if t.get("inicio_fixo")]
    flex = [t for t in tarefas if not t.get("inicio_fixo")]
    if len(flex) > 7:
        raise ValueError("No máximo 7 tarefas flexíveis por planejamento.")

    blocos_fixos, problemas = [], []
    for t in fixas:
        a = hm(t["inicio_fixo"])
        b = a + t["duracao_min"]
        if a < ini or b > fi:
            problemas.append(f"{t['id']} ({t['nome']}) está fora da janela {inicio}-{fim}")
        blocos_fixos.append((a, b, t["id"]))
    livres = _livres(ini, fi, [(a, b) for a, b, _ in blocos_fixos])

    chave, blocos, feitos = _melhor(flex, livres, permitir_divisao, por_id)
    for a, b, i in blocos_fixos:
        feitos[i] = b - a
    todos = sorted(blocos_fixos + blocos)

    justificativas = {}
    u_total = sum(utilidade(por_id[i], m) for i, m in feitos.items())
    for t in tarefas:
        i = t["id"]
        u_max = utilidade(t)
        if t in fixas:
            justificativas[i] = (f"compromisso fixo às {t['inicio_fixo']}; mantido no horário "
                                 f"(utilidade {u_max:g})")
        elif i in feitos and feitos[i] == t["duracao_min"]:
            justificativas[i] = (f"incluída: prioridade {t['prioridade']}, prazo {t['prazo']}, "
                                 f"utilidade {u_max:g}")
        elif i in feitos:
            justificativas[i] = (f"incluída em parte ({feitos[i]} de {t['duracao_min']} min): "
                                 f"o tempo livre não comporta a tarefa inteira; utilidade "
                                 f"{utilidade(t, feitos[i]):g} de {u_max:g}")
        else:
            alt = _melhor(flex, livres, permitir_divisao, por_id, obrigatoria=i)
            if alt is None:
                motivo = (f"não cabe em nenhum intervalo livre contínuo "
                          f"({t['duracao_min']} min)")
            else:
                u_alt = alt[0][0] + sum(
                    utilidade(por_id[i], b - a)
                        for a, b, i in blocos_fixos
                )
                mudancas = []
                for x, tx in por_id.items():
                    if x == i or tx.get("inicio_fixo"):
                        continue
                    antes, depois = feitos.get(x, 0), alt[2].get(x, 0)
                    if depois < antes:
                        mudancas.append(f"{x} sairia" if depois == 0
                                        else f"{x} cairia de {antes} para {depois} min")
                motivo = (f"incluí-la daria utilidade total {u_alt:g} em vez de {u_total:g}"
                          + (f" ({'; '.join(mudancas)})" if mudancas else ""))
            prazo = ("o prazo é hoje: precisa de atenção" if t["prazo"] == "hoje"
                     else f"o prazo ({t['prazo']}) permite fazer depois")
            justificativas[i] = f"não incluída: {motivo}; {prazo}"

    plano = [{"inicio": txt(a), "fim": txt(b), "tarefa": i, "nome": por_id[i]["nome"]}
             for a, b, i in todos]
    livres_finais = _livres(ini, fi, [(a, b) for a, b, _ in todos])
    return {
        "plano": plano,
        "utilidade_total": round(u_total, 2),
        "utilidade_maxima_possivel": round(sum(utilidade(t) for t in tarefas), 2),
        "nao_realizadas": [t["id"] for t in tarefas if t["id"] not in feitos],
        "parciais": {i: m for i, m in feitos.items() if m < por_id[i]["duracao_min"]},
        "tempo_livre": [f"{txt(a)}-{txt(b)}" for a, b in livres_finais],
        "justificativas": justificativas,
        "problemas": problemas,
        "criterio": "utilidade = peso da prioridade (alta 10, media 6, baixa 2) x fator do "
                    "prazo (hoje 1,5; amanha 1,2; outro 1,0)",
        "divisao_permitida": permitir_divisao,
    }


def verificar(plano, tarefas, inicio="14:00", fim="18:00"):
    """Confere um plano (de qualquer origem) contra as restrições do problema."""
    tarefas = _normalizar(tarefas)
    por_id = {t["id"]: t for t in tarefas}
    ini, fi = hm(inicio), hm(fim)
    violacoes, avisos = [], []
    blocos = sorted((hm(b["inicio"]), hm(b["fim"]), b["tarefa"]) for b in plano)
    for a, b, i in blocos:
        if i not in por_id:
            violacoes.append(f"{i} não é uma tarefa conhecida")
            continue
        if b <= a:
            violacoes.append(f"{i}: horário de fim antes do início")
        if a < ini or b > fi:
            violacoes.append(f"{i}: {txt(a)}-{txt(b)} fora da janela {inicio}-{fim}")
    for (a1, b1, i1), (a2, b2, i2) in zip(blocos, blocos[1:]):
        if a2 < b1:
            violacoes.append(f"sobreposição entre {i1} ({txt(a1)}-{txt(b1)}) e "
                             f"{i2} ({txt(a2)}-{txt(b2)})")
    for t in tarefas:
        partes = [(a, b) for a, b, i in blocos if i == t["id"]]
        total = sum(b - a for a, b in partes)
        if t.get("inicio_fixo"):
            if partes != [(hm(t["inicio_fixo"]), hm(t["inicio_fixo"]) + t["duracao_min"])]:
                violacoes.append(f"{t['id']}: compromisso fixo não está em "
                                 f"{t['inicio_fixo']} com {t['duracao_min']} min")
        if len(partes) > 1 and not t["divisivel"]:
            violacoes.append(f"{t['id']}: foi dividida, mas não é divisível")
        if total > t["duracao_min"]:
            violacoes.append(f"{t['id']}: {total} min agendados para {t['duracao_min']} min")
        if 0 < total < t["duracao_min"] and not t["divisivel"]:
            violacoes.append(f"{t['id']}: iniciada e não concluída ({total} de "
                             f"{t['duracao_min']} min)")
        if total == 0 and t["prazo"] == "hoje":
            avisos.append(f"{t['id']} vence hoje e não foi agendada")
    return {"valido": not violacoes, "violacoes": violacoes, "avisos": avisos}
