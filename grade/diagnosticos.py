"""Diagnósticos locais comprováveis; não atribuem a causa global do solver."""
from copy import copy


def diagnostico(demanda, motor, aula=None, alocacoes=()):
    habilitados = [p for p in motor.professores if demanda.disciplina_id in motor._disciplinas[p]]
    if not habilitados:
        return 'Nenhum professor habilitado para esta disciplina. Ação: cadastrar a habilitação na ficha do professor.'
    permitidos = [p for p in habilitados if motor.permitido(p, demanda.turma.unidade_id)]
    if not permitidos:
        return 'Nenhum habilitado permitido nesta unidade. Ação: revisar a unidade oficial/permitidas na ficha do professor.'
    elegiveis = [p for p in permitidos if not demanda.professor_id or p == demanda.professor_id]
    if not elegiveis:
        return 'O professor fixado na demanda legada não é elegível. Ação: revisar o vínculo legado, a habilitação e as unidades permitidas.'
    if aula is None:
        return 'Há docentes habilitados e permitidos. Ação: revisar os horários e os bloqueios dos cards; a causa global não foi isolada.'
    disponiveis = [p for p in elegiveis if motor.disponivel(p, aula.data, aula.horario_id)]
    if not disponiveis:
        return 'Todos os docentes elegíveis estão indisponíveis neste horário. Ação: revisar as restrições por data/horário do professor.'
    outros = [a for a in alocacoes if a is not aula and not (aula.pk and a.pk == aula.pk)]
    bloqueios = set()
    for p in disponiveis:
        teste = copy(aula)
        teste.professor_id = p
        if sum(a.professor_id == p and a.data == aula.data for a in outros) >= motor.professores[p].limite_aulas:
            bloqueios.add('limite diário atingido: revisar limite ou redistribuir aulas')
            continue
        motivos = [motor.motivo_conflito(teste, a) for a in outros if a.professor_id == p and a.data == aula.data]
        motivos = [m for m in motivos if m]
        if not motivos:
            return 'Há candidato sem bloqueio local identificado. Ação: tentar nova geração ou revisar a distribuição; não foi comprovada falta de professor.'
        for motivo in motivos:
            if 'Falta cadastrar o tempo' in motivo:
                bloqueios.add('trajeto ausente: consultar/cadastrar o trajeto na unidade')
            elif 'deslocamento' in motivo:
                bloqueios.add('tempo de trajeto insuficiente: revisar horários entre unidades')
            else:
                bloqueios.add('sobreposição do professor: revisar as aulas no mesmo horário')
    return ('Bloqueios dos candidatos disponíveis nesta distribuição: ' + '; '.join(sorted(bloqueios)) + '.')[:240]
