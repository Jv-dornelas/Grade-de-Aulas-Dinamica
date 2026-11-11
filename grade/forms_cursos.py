from django import forms
from .models import Turma


class TurmaForm(forms.ModelForm):
    dias_semana = forms.TypedMultipleChoiceField(
        label='Dias de aula', coerce=int,
        choices=list(enumerate(('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'))),
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['horarios'].required = False
        self.fields['curso'].required = not self.instance.pk or bool(self.instance.curso_id)
        self.fields['turno_principal'].required = not self.instance.pk or bool(self.instance.curso_id)

    def clean(self):
        dados = super().clean()
        curso = dados.get('curso')
        if curso and curso.aulas_semanais == 24 and (
                set(dados.get('dias_semana', [])) != {0, 1, 2, 3, 4}
                or not dados.get('turno_principal') or dados.get('dia_contraturno') is None):
            raise forms.ValidationError('Para a matriz de 24 aulas, configure segunda a sexta, turno principal e um dia de contraturno (20 + 4 aulas).')
        if not dados.get('turno_principal') and not dados.get('horarios'):
            self.add_error('horarios', 'Selecione horários para o calendário legado ou configure o turno principal.')
        return dados

    class Meta:
        model = Turma
        fields = '__all__'
        labels = {'materias_fixas': 'Manter matérias em horários fixos (opcional)'}
