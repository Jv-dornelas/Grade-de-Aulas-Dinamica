from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('grade', '0002_alocacaograde_atualizado_em_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(
            model_name='professor', name='usuario',
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='professor', to=settings.AUTH_USER_MODEL,
                help_text='Conta usada pelo professor para consultar sua grade no celular.',
            ),
        ),
    ]
