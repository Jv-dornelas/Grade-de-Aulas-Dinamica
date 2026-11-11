"""Cenário opt-in para visualizar a automação integrada, isolado na cópia local."""
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from grade.gerador import gerar_semana
from grade.jornada import obter_horarios_padrao
from grade.horarios_curriculares import salvar_materias
from grade.models import (AlocacaoGrade, Curso, Disciplina, Disponibilidade,
                          MatrizCurricular, Professor, Turma, Unidade)


NOME_CURSO = '[DEMO VISUAL] Preparatório 1'
COMPONENTES = [
    ('Matemática', 4, 'EXATAS', 0),
    ('Português e interpretação', 3, 'HUMANAS', 1),
    ('Redação', 2, 'HUMANAS', 1),
    ('Biologia', 3, 'BIOLOGICAS', 2),
    ('Física', 3, 'EXATAS', 0),
    ('Química', 3, 'EXATAS', 0),
    ('História', 2, 'HUMANAS', 3),
    ('Geografia', 2, 'HUMANAS', 3),
    ('Filosofia e Sociologia', 1, 'HUMANAS', 3),
    ('Inglês', 1, 'HUMANAS', 1),
]


class Command(BaseCommand):
    help = 'Adiciona 2 turmas fictícias com curso de 24 aulas e 2 aulas fixas; valida o restante sem gravar a proposta.'

    def add_arguments(self, parser):
        parser.add_argument('--semana', required=True)
        parser.add_argument('--dia-contraturno', required=True, type=int, choices=range(5),
                            help='0=segunda a 4=sexta. Escolha demonstrativa explícita, não padrão global.')

    @transaction.atomic
    def handle(self, *args, **options):
        banco = settings.DATABASES['default']
        if banco['ENGINE'] != 'django.db.backends.sqlite3' or Path(banco['NAME']).name != 'db.automacao.sqlite3':
            raise CommandError('Demonstração permitida somente em db.automacao.sqlite3. Nada foi alterado.')
        try:
            inicio = date.fromisoformat(options['semana'])
            if not date(1900, 1, 8) <= inicio <= date(2100, 12, 24):
                raise ValueError
            inicio -= timedelta(days=inicio.weekday())
        except (ValueError, TypeError):
            raise CommandError('Informe uma data válida entre 1900 e 2100.')
        if Curso.objects.filter(nome=NOME_CURSO).exists() or Curso.objects.filter(
                nome='Preparatório 1', observacoes__startswith='Cenário fictício e editável').exists():
            self.stdout.write('O cenário visual já existe. Nenhum cadastro foi sobrescrito ou duplicado.')
            return

        horarios = obter_horarios_padrao()
        curso = Curso.objects.create(nome=NOME_CURSO, observacoes=(
            'Cenário fictício e editável para visualizar a automação. 24 aulas de 50 minutos = 20 horas semanais; '
            '20 no turno principal e 4 no contraturno escolhido explicitamente. Não é padrão escolar. '
            'Português e interpretação e Filosofia e Sociologia são componentes compostos demonstrativos. '
            'Escolhido Inglês para a única aula de idioma; pode ser substituído por Espanhol com habilitação compatível. '
            'Todas as disponibilidades deste cenário são fictícias.'))
        disciplinas = []
        for nome, quantidade, area, grupo in COMPONENTES:
            disciplina = Disciplina.objects.create(nome=f'[DEMO VISUAL] {nome}', area=area)
            MatrizCurricular.objects.create(curso=curso, disciplina=disciplina, quantidade_semana=quantidade)
            disciplinas.append((disciplina, grupo))

        turmas_criadas = []
        for indice, (polo, nomes) in enumerate((
            ('Horizonte', ('Ana', 'Bruno', 'Carla', 'Diego')),
            ('Jardim', ('Elisa', 'Fábio', 'Gabriela', 'Hugo')),
        )):
            unidade = Unidade.objects.create(nome=f'[DEMO VISUAL] {polo}', responsavel='Coordenação fictícia')
            turma = Turma.objects.create(nome=f'[DEMO VISUAL] Preparatório {indice + 1}', curso=curso,
                materias_fixas=False,
                unidade=unidade, dias_semana=[0, 1, 2, 3, 4], turno_principal='manha',
                dia_contraturno=options['dia_contraturno'])
            turmas_criadas.append(turma)
            professores = []
            for grupo, nome in enumerate(nomes):
                professor = Professor.objects.create(nome=f'[DEMO VISUAL] {nome}', unidade_oficial=unidade,
                    limite_aulas=4, observacao='Professor fictício; disponibilidade criada apenas para esta demonstração.')
                professor.disciplinas.set([d for d, g in disciplinas if g == grupo])
                for d in range(5):
                    dia = inicio + timedelta(days=d)
                    Disponibilidade.objects.create(professor=professor, data=dia,
                        disponivel_manha=True, disponivel_tarde=(d == options['dia_contraturno']))
                professores.append(professor)
            demanda = turma.demandas.get(disciplina=disciplinas[0][0])
            fixa = AlocacaoGrade(data=inicio, horario=horarios[0], unidade=unidade,
                professor=professores[0], turma=turma, disciplina=disciplinas[0][0], demanda=demanda)
            fixa.full_clean()
            fixa.save()

        # Completa só novas datas dos dois professores identificados do cenário antigo.
        # Não altera recusas prévias, disponibilidades existentes ou pessoas reais.
        for professor in Professor.objects.filter(nome__in=['[DEMO] Ana', '[DEMO] Bruno']):
            if not professor.disciplinas.exists() or professor.disciplinas.exclude(nome__startswith='[DEMO]').exists():
                continue
            for d in range(5):
                Disponibilidade.objects.get_or_create(professor=professor, data=inicio + timedelta(days=d),
                    defaults={'disponivel_manha': True, 'disponivel_tarde': True})

        resultado = gerar_semana(inicio)
        if resultado['status'] not in ('optimal', 'feasible') or resultado.get('resumo', {}).get('pendentes', 1):
            raise CommandError('Cenário não completou a validação; transação revertida: ' +
                               ' '.join(resultado.get('pendencias', [])))
        for turma in turmas_criadas:
            itens = [{'dia_semana': date.fromisoformat(p['data']).weekday(), 'horario_id': p['horario_id'],
                      'demanda_id': p['demanda_id']} for p in resultado['propostas'] if p['turma_id'] == turma.pk]
            itens += [{'dia_semana': a.data.weekday(), 'horario_id': a.horario_id, 'demanda_id': a.demanda_id}
                      for a in AlocacaoGrade.objects.filter(turma=turma)]
            salvar_materias(turma, itens)
        self.stdout.write(self.style.SUCCESS(
            f'Cenário pronto em {inicio:%d/%m/%Y}: 1 curso, 2 turmas, 8 professores fictícios e 2 aulas fixas. '
            f'Gerador validado: {len(resultado["propostas"])} novas propostas, sem pendências. '
            f'As propostas NÃO foram gravadas. Abra /?data={inicio.isoformat()}&por=curso e clique Gerar grade.'))
